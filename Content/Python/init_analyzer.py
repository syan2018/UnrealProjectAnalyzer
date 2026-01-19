"""
UnrealCopilot MCP Server initialization script.

This script initializes the MCP server inside Unreal Engine's Python environment.
It sets up the bridge between C++ and Python, and starts the analyzer server.
"""

import sys
import os
from pathlib import Path
import site

_python_dir = Path(__file__).parent
_venv_site_packages_dir = _python_dir / ".venv" / "Lib" / "site-packages"

# Add uv-managed venv site-packages first (higher priority for dependencies).
if _venv_site_packages_dir.exists():
    try:
        # Important: process .pth files too (e.g. pywin32 on Windows)
        site.addsitedir(str(_venv_site_packages_dir))
    except Exception:
        if str(_venv_site_packages_dir) not in sys.path:
            sys.path.insert(0, str(_venv_site_packages_dir))

# Add Content/Python for the UnrealCopilot package
if str(_python_dir) not in sys.path:
    sys.path.insert(0, str(_python_dir))

import unreal
import asyncio
import uuid
import threading
from typing import Optional


# -----------------------------------------------------------------------------
# Module state (avoid relying on __main__ across ExecPythonCommand calls)
# -----------------------------------------------------------------------------
_analyzer_mcp = None
_analyzer_context_id: Optional[str] = None
_analyzer_server_thread = None
_analyzer_server_shutdown_event = None  # threading.Event for graceful shutdown
_analyzer_uvicorn_server = None  # uvicorn.Server instance for HTTP/SSE
_analyzer_uvicorn_loop = None  # asyncio loop used by uvicorn server thread
_tools_registered = False
_stderr_redirected = False
_original_stderr = None
_dependency_dialog_shown = False


# ---------------------------------------------------------------------------
# Thread-safe Python -> C++ notification queue
#
# UE Python API access must happen on the main game thread.
# Our MCP server runs on a background Python thread, so we enqueue notifications
# and drain them on the main thread via Slate post-tick.
# ---------------------------------------------------------------------------
_cpp_notify_lock = threading.Lock()
_cpp_notify_queue: list[tuple[str, tuple]] = []
_cpp_notify_tick_handle = None


def _get_transport_enum(transport: str):
    """
    Best-effort mapping from transport string to UE enum.
    We keep it defensive because UE Python enum exposure can vary by version.
    """
    t = (transport or "").strip().lower()
    enum_cls = getattr(unreal, "EUnrealAnalyzerMcpTransport", None) or getattr(
        unreal, "UnrealAnalyzerMcpTransport", None
    )
    if enum_cls is None:
        return None

    if t == "stdio":
        return getattr(enum_cls, "Stdio", None)
    if t == "sse":
        return getattr(enum_cls, "Sse", None)
    # default: http
    return getattr(enum_cls, "Http", None)


def _notify_cpp(method_name: str, *args) -> None:
    """
    Notify C++ subsystem about MCP server state.

    Important:
    - Must run on game thread to safely touch UE objects.
    - This replaces unreliable port-probing in Tick().
    """
    # IMPORTANT: Never touch Unreal API here (this can be called from a background thread).
    try:
        with _cpp_notify_lock:
            _cpp_notify_queue.append((method_name, args))
    except Exception:
        return


def _ensure_cpp_notify_pump_registered_once() -> None:
    """Register a Slate tick callback to drain notification queue on the main thread."""
    global _cpp_notify_tick_handle
    if _cpp_notify_tick_handle is not None:
        return

    try:
        register_post = getattr(unreal, "register_slate_post_tick_callback", None)
        register_pre = getattr(unreal, "register_slate_pre_tick_callback", None)

        def _pump(delta_seconds=0.0):
            # Drain queue first (keep lock hold minimal)
            try:
                with _cpp_notify_lock:
                    items = list(_cpp_notify_queue)
                    _cpp_notify_queue.clear()
            except Exception:
                return

            if not items:
                return

            subsystem_cls = getattr(unreal, "McpServerSubsystem", None)
            if subsystem_cls is None:
                # Subsystem not ready yet; retry next tick.
                with _cpp_notify_lock:
                    _cpp_notify_queue[:0] = items
                return

            try:
                subsystem = unreal.get_editor_subsystem(subsystem_cls)
            except Exception:
                subsystem = None

            if not subsystem:
                with _cpp_notify_lock:
                    _cpp_notify_queue[:0] = items
                return

            for method_name, args in items:
                try:
                    fn = getattr(subsystem, method_name, None)
                    if callable(fn):
                        fn(*args)
                except Exception as e:
                    unreal.log_warning(f"[UnrealCopilot] Failed to notify C++: {method_name}: {e}")

        if callable(register_post):
            _cpp_notify_tick_handle = register_post(_pump)
        elif callable(register_pre):
            _cpp_notify_tick_handle = register_pre(_pump)
        else:
            unreal.log_warning(
                "[UnrealCopilot] No Slate tick callback API found; C++ state notifications are disabled."
            )
            _cpp_notify_tick_handle = "disabled"
    except Exception as e:
        try:
            unreal.log_warning(f"[UnrealCopilot] Failed to register C++ notify pump: {e}")
        except Exception:
            pass
        _cpp_notify_tick_handle = "disabled"


def _show_dependency_error_dialog_once() -> None:
    """
    Show a user-facing dialog when Python dependencies are not ready.

    This is intentionally simple and actionable: tell the user to run uv sync manually
    and restart the editor. Shown at most once per editor session.
    """
    global _dependency_dialog_shown
    if _dependency_dialog_shown:
        return

    _dependency_dialog_shown = True

    try:
        import uv_sync

        missing = getattr(uv_sync, "LAST_MISSING", None) or []
        last_error = getattr(uv_sync, "LAST_ERROR", None)
    except Exception:
        missing = []
        last_error = None

    missing_text = ", ".join(missing) if missing else "(unknown)"
    details = f"缺失依赖: {missing_text}"
    if last_error:
        details += f"\n\n最近一次错误:\n{last_error}"

    message = (
        "UnrealCopilot 需要 Python 依赖才能启动 MCP。\n\n"
        f"{details}\n\n"
        "建议（首次安装/更新后）：\n"
        "1) 关闭 Unreal Editor\n"
        "2) 在插件目录执行:\n"
        "   cd <PluginRoot>/Content/Python\n"
        "   uv sync\n"
        "3) 重新打开 Unreal Editor 后再点击 Start\n\n"
        "更多细节请查看 Output Log 中的 LogPython。"
    )

    try:
        unreal.EditorDialog.show_message(
            "UnrealCopilot - 依赖未就绪",
            message,
            unreal.AppMsgType.OK,
        )
    except Exception:
        # If dialog API isn't available, at least log it.
        unreal.log_warning(message)


class _UnrealLogStream:
    """
    A minimal file-like stream that forwards writes to Unreal log.

    Unreal's Python plugin treats stderr as LogPython: Error (even for INFO).
    We redirect FastMCP/Uvicorn stderr to Unreal log to avoid misleading red errors.
    """

    encoding = "utf-8"

    def write(self, s: str) -> int:
        if not s:
            return 0
        # Avoid logging huge chunks as one line
        for line in str(s).splitlines():
            line = line.rstrip()
            if line:
                unreal.log(line)
        return len(s)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False


def _redirect_stderr_to_unreal_once() -> None:
    global _stderr_redirected, _original_stderr
    if _stderr_redirected:
        return
    try:
        _original_stderr = sys.stderr
        sys.stderr = _UnrealLogStream()
        _stderr_redirected = True
    except Exception:
        # Best-effort; if we can't redirect, keep default behavior.
        pass


def _store_legacy_globals(mcp, context_id: str) -> None:
    """Backward-compatible: also store into __main__ (best-effort)."""
    try:
        import __main__

        __main__._analyzer_mcp = mcp
        __main__._analyzer_context_id = context_id
    except Exception:
        # UE may execute python in a non-standard global module; ignore.
        pass


def setup_analyzer_bridge(force: bool = False):
    """
    Set up the bridge between C++ and Python for the analyzer.
    This creates a context object that C++ can use to communicate with Python.
    """
    global _analyzer_mcp, _analyzer_context_id, _tools_registered

    if _analyzer_mcp is not None and _analyzer_context_id is not None and not force:
        return {
            "context_id": _analyzer_context_id,
            "status": "initialized",
            "mcp_name": getattr(_analyzer_mcp, "name", "UnrealCopilot"),
        }

    try:
        # Ensure dependencies are installed (and sys.path updated by uv_sync)
        try:
            import uv_sync

            if not uv_sync.ensure_dependencies():
                unreal.log_error("[UnrealCopilot] Dependencies are missing; cannot initialize bridge.")
                unreal.log_error("[UnrealCopilot] Run: uv sync (in Content/Python)")
                _show_dependency_error_dialog_once()
                return None
        except Exception as e:
            unreal.log_warning(f"[UnrealCopilot] Dependency check failed: {e}")

        # Check if we can import the analyzer
        from unreal_copilot.server import initialize_from_environment, mcp, register_tools

        unreal.log("[UnrealCopilot] MCP server module loaded successfully")

        # Register tools once (important when running via import in UE)
        if not _tools_registered:
            try:
                register_tools()
                _tools_registered = True
            except Exception as e:
                unreal.log_error(f"[UnrealCopilot] Failed to register MCP tools: {e}")
                import traceback

                unreal.log_error(traceback.format_exc())
                return None

        # Initialize analyzer config from current environment (optional but helpful)
        try:
            initialize_from_environment()
        except Exception:
            # Not fatal; tools that rely on paths will warn later.
            pass

        # Create a bridge context
        context_id = str(uuid.uuid4())

        # Store the MCP instance for later access
        _analyzer_mcp = mcp
        _analyzer_context_id = context_id
        _store_legacy_globals(mcp, context_id)

        unreal.log(f"[UnrealCopilot] Bridge initialized with ID: {context_id}")

        return {
            "context_id": context_id,
            "status": "initialized",
            "mcp_name": mcp.name if hasattr(mcp, 'name') else "UnrealCopilot",
        }

    except ImportError as e:
        unreal.log_error(f"[UnrealCopilot] Failed to import MCP server: {e}")
        unreal.log_error(f"[UnrealCopilot] Make sure dependencies are installed")
        unreal.log_error(f"[UnrealCopilot] Run: uv sync (in Content/Python)")
        _show_dependency_error_dialog_once()
        return None
    except Exception as e:
        unreal.log_error(f"[UnrealCopilot] Error initializing analyzer: {e}")
        import traceback
        unreal.log_error(traceback.format_exc())
        return None


def get_mcp_instance():
    """Get the global MCP instance."""
    global _analyzer_mcp
    if _analyzer_mcp is not None:
        return _analyzer_mcp
    # Fallback for legacy storage
    try:
        import __main__

        return getattr(__main__, "_analyzer_mcp", None)
    except Exception:
        return None


def start_analyzer_server(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp",
    cpp_source_path: Optional[str] = None,
    unreal_engine_path: Optional[str] = None,
):
    """
    Start the MCP analyzer server.

    Args:
        transport: Transport protocol ("stdio", "http", "sse")
        host: Host for HTTP/SSE transport
        port: Port for HTTP/SSE transport
        path: Path for HTTP transport
        cpp_source_path: Project C++ source path
        unreal_engine_path: Unreal Engine source path
    """
    try:
        # Prevent FastMCP/Uvicorn from emitting INFO logs as LogPython: Error
        _redirect_stderr_to_unreal_once()

        mcp = get_mcp_instance()
        if not mcp:
            unreal.log_warning("[UnrealCopilot] MCP instance not found. Initializing bridge lazily...")
            result = setup_analyzer_bridge()
            if not result:
                unreal.log_error("[UnrealCopilot] Failed to initialize bridge; cannot start server.")
                _notify_cpp("notify_mcp_server_start_failed", "Failed to initialize Python bridge")
                _notify_cpp("notify_mcp_server_stopped")
                return False
            mcp = get_mcp_instance()
            if not mcp:
                unreal.log_error("[UnrealCopilot] MCP instance still missing after initialization.")
                _notify_cpp("notify_mcp_server_start_failed", "MCP instance missing after initialization")
                _notify_cpp("notify_mcp_server_stopped")
                return False

        unreal.log(f"[UnrealCopilot] Starting MCP server with transport: {transport}")

        # Set environment variables for paths
        if cpp_source_path:
            os.environ["CPP_SOURCE_PATH"] = cpp_source_path
            unreal.log(f"[UnrealCopilot] Set CPP_SOURCE_PATH: {cpp_source_path}")

        if unreal_engine_path:
            os.environ["UNREAL_ENGINE_PATH"] = unreal_engine_path
            unreal.log(f"[UnrealCopilot] Set UNREAL_ENGINE_PATH: {unreal_engine_path}")

        # Ensure tools are registered + analyzer initialized from env
        global _tools_registered
        try:
            from unreal_copilot.server import initialize_from_environment, register_tools

            if not _tools_registered:
                register_tools()
                _tools_registered = True
            initialize_from_environment()
        except Exception:
            pass

        # Start the server in a background thread
        import threading
        global _analyzer_server_thread, _analyzer_server_shutdown_event, _analyzer_uvicorn_server, _analyzer_uvicorn_loop
        
        if _analyzer_server_thread is not None and _analyzer_server_thread.is_alive():
            unreal.log_warning("[UnrealCopilot] MCP server thread already running")
            return True

        # Create shutdown event for graceful stop
        shutdown_event = threading.Event()
        _analyzer_server_shutdown_event = shutdown_event

        # Notify C++ that we are entering the starting state (non-blocking).
        transport_enum = _get_transport_enum(transport)
        if transport_enum is not None:
            _notify_cpp("notify_mcp_server_starting", transport_enum, host, int(port), path)

        def run_server():
            global _analyzer_uvicorn_server, _analyzer_uvicorn_loop
            try:
                # For HTTP/SSE, we try to get access to the uvicorn server for graceful shutdown
                if transport in ("http", "sse"):
                    try:
                        # Use FastMCP's http_app to ensure we can manage uvicorn lifecycle.
                        import uvicorn

                        asgi_app = mcp.http_app(transport=transport, path=path)

                        config = uvicorn.Config(
                            asgi_app,
                            host=host,
                            port=port,
                            log_level="warning",
                            lifespan="on",
                            ws="websockets-sansio",
                            timeout_graceful_shutdown=1,
                        )
                        server = uvicorn.Server(config)
                        _analyzer_uvicorn_server = server

                        # If stop was requested early, honor it before starting.
                        if shutdown_event.is_set():
                            server.should_exit = True

                        async def _serve_with_watch():
                            # Wait for uvicorn to fully start, then notify C++.
                            async def _watch_started():
                                try:
                                    while not server.started and not server.should_exit:
                                        await asyncio.sleep(0.05)
                                    if server.started and not server.should_exit:
                                        _notify_cpp("notify_mcp_server_running")
                                except Exception:
                                    return

                            asyncio.create_task(_watch_started())
                            await server.serve()

                        # Run server on a dedicated event loop (thread-safe shutdown).
                        loop = asyncio.new_event_loop()
                        _analyzer_uvicorn_loop = loop
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(_serve_with_watch())
                    except Exception as e:
                        # No fallback here: if custom ASGI/uvicorn setup fails, state reporting
                        # would be unreliable. Fail fast and let outer handler report errors.
                        unreal.log_error(f"[UnrealCopilot] Custom uvicorn setup failed: {e}")
                        raise
                elif transport == "stdio":
                    try:
                        mcp.run(show_banner=False)
                    except TypeError:
                        mcp.run()
                else:
                    unreal.log_error(f"[UnrealCopilot] Unknown transport: {transport}")
            except Exception as e:
                unreal.log_error(f"[UnrealCopilot] MCP server crashed: {e}")
                import traceback
                unreal.log_error(traceback.format_exc())
                _notify_cpp("notify_mcp_server_start_failed", str(e))
            finally:
                # Clear server reference when done
                _analyzer_uvicorn_server = None
                _analyzer_uvicorn_loop = None
                # Always notify stopped when the server thread exits.
                _notify_cpp("notify_mcp_server_stopped")

        server_thread = threading.Thread(target=run_server, daemon=True, name="MCP-Server")
        server_thread.start()

        _analyzer_server_thread = server_thread
        # Legacy storage (best-effort)
        try:
            import __main__
            __main__._analyzer_server_thread = server_thread
        except Exception:
            pass

        unreal.log(f"[UnrealCopilot] MCP server started on {transport}://{host}:{port}{path}")
        return True

    except Exception as e:
        unreal.log_error(f"[UnrealCopilot] Failed to start MCP server: {e}")
        import traceback
        unreal.log_error(traceback.format_exc())
        return False


def stop_analyzer_server():
    """
    Stop the MCP analyzer server.
    
    For HTTP/SSE transport, attempts graceful shutdown via uvicorn.
    For stdio transport, the daemon thread will terminate with the process.
    """
    try:
        global _analyzer_server_thread, _analyzer_server_shutdown_event, _analyzer_uvicorn_server, _analyzer_uvicorn_loop
        
        if _analyzer_server_thread is None or not _analyzer_server_thread.is_alive():
            unreal.log("[UnrealCopilot] MCP server is not running")
            _notify_cpp("notify_mcp_server_stopped")
            return False
        
        unreal.log("[UnrealCopilot] Stopping MCP server...")
        
        # Signal shutdown event
        if _analyzer_server_shutdown_event is not None:
            _analyzer_server_shutdown_event.set()
        
        # Try to gracefully shutdown uvicorn server (HTTP/SSE)
        if _analyzer_uvicorn_server is not None:
            try:
                _analyzer_uvicorn_server.should_exit = True
                _analyzer_uvicorn_server.force_exit = True
                if _analyzer_uvicorn_loop is not None:
                    _analyzer_uvicorn_loop.call_soon_threadsafe(lambda: None)
                unreal.log("[UnrealCopilot] Signaled uvicorn server to exit")
            except Exception as e:
                unreal.log_warning(f"[UnrealCopilot] Failed to signal uvicorn shutdown: {e}")
        
        # Wait briefly for graceful shutdown
        if _analyzer_server_thread.is_alive():
            _analyzer_server_thread.join(timeout=5.0)
            
            if _analyzer_server_thread.is_alive():
                # As a last resort, stop the event loop to unblock the thread.
                if _analyzer_uvicorn_loop is not None:
                    try:
                        _analyzer_uvicorn_loop.call_soon_threadsafe(_analyzer_uvicorn_loop.stop)
                    except Exception as e:
                        unreal.log_warning(f"[UnrealCopilot] Failed to stop uvicorn loop: {e}")
                    _analyzer_server_thread.join(timeout=1.0)

                if _analyzer_server_thread.is_alive():
                    unreal.log_warning("[UnrealCopilot] Server thread still running after timeout (daemon thread will exit with process)")
                    # Keep references so we can retry stop / state stays "stopping" in C++.
                    return False
            else:
                unreal.log("[UnrealCopilot] Server thread stopped gracefully")
        
        # Clean up references (only after the thread actually stopped)
        _analyzer_server_thread = None
        _analyzer_server_shutdown_event = None
        _analyzer_uvicorn_server = None
        _analyzer_uvicorn_loop = None
        
        try:
            import __main__
            if hasattr(__main__, "_analyzer_server_thread"):
                delattr(__main__, "_analyzer_server_thread")
        except Exception:
            pass
        
        unreal.log("[UnrealCopilot] MCP server stopped")
        _notify_cpp("notify_mcp_server_stopped")
        return True
        
    except Exception as e:
        unreal.log_error(f"[UnrealCopilot] Error stopping MCP server: {e}")
        import traceback
        unreal.log_error(traceback.format_exc())
        return False


def get_server_status():
    """Get the current status of the MCP server."""
    try:
        global _analyzer_server_thread, _analyzer_context_id, _analyzer_uvicorn_server
        thread = _analyzer_server_thread
        if thread is None:
            # Fallback to legacy storage
            try:
                import __main__
                thread = getattr(__main__, "_analyzer_server_thread", None)
            except Exception:
                thread = None

        is_running = thread is not None and thread.is_alive()
        
        # Additional check: if uvicorn server exists, check its state
        uvicorn_active = False
        if _analyzer_uvicorn_server is not None:
            try:
                uvicorn_active = _analyzer_uvicorn_server.started and not _analyzer_uvicorn_server.should_exit
            except Exception:
                pass

        return {
            "running": is_running,
            "context_id": _analyzer_context_id,
            "uvicorn_active": uvicorn_active,
        }
    except Exception as e:
        unreal.log_error(f"[UnrealCopilot] Error getting server status: {e}")
        return {
            "running": False,
            "error": str(e),
        }


# Auto-initialize when imported
if __name__ != "__main__":
    # We're being imported/exec'd by UE
    unreal.log("[UnrealCopilot] Initializing analyzer bridge...")

    # Ensure dependencies are installed
    _deps_ok = False
    try:
        import uv_sync
        _deps_ok = uv_sync.ensure_dependencies()
        if not _deps_ok:
            unreal.log_warning("[UnrealCopilot] Dependencies are missing.")
            unreal.log_warning("[UnrealCopilot] Please run: uv sync")
            unreal.log_warning("[UnrealCopilot] in the Content/Python directory, then restart the editor or click Start again.")
            _show_dependency_error_dialog_once()
    except Exception as e:
        unreal.log_warning(f"[UnrealCopilot] Failed to check dependencies: {e}")

    # Only set up the bridge if dependencies are available
    if _deps_ok:
        # Register main-thread notification pump (required for Python -> C++ state updates)
        _ensure_cpp_notify_pump_registered_once()

        result = setup_analyzer_bridge()
        if result:
            unreal.log("[UnrealCopilot] Analyzer initialized successfully")
        else:
            unreal.log_error("[UnrealCopilot] Failed to initialize analyzer")
    else:
        unreal.log_error("[UnrealCopilot] Skipping bridge setup due to missing dependencies")


