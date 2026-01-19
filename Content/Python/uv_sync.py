"""
Automatic dependency sync for UnrealCopilot.

Uses uv to create a local virtual environment (.venv) from pyproject.toml.

Why:
- Avoids installing into system/site Python
- Avoids relying on pip-style target installs
- Works well with UE embedded Python by adding .venv site-packages to sys.path
"""

import sys
import subprocess
from pathlib import Path
import site
import traceback

LAST_MISSING: list[str] = []
LAST_ERROR: str | None = None


def get_python_dir() -> Path:
    """Get the Content/Python directory."""
    return Path(__file__).parent.absolute()


def get_venv_site_packages() -> Path:
    """Get .venv site-packages directory (Windows layout)."""
    return get_python_dir() / ".venv" / "Lib" / "site-packages"

def ensure_site_packages_in_path() -> list[Path]:
    """Ensure candidate site-packages dirs are in sys.path for import checks."""
    added: list[Path] = []

    p = get_venv_site_packages()
    if p.exists():
        # Use site.addsitedir so .pth files are processed (important on Windows, e.g. pywin32).
        before = set(sys.path)
        try:
            site.addsitedir(str(p))
        except Exception:
            # Fallback: plain sys.path injection
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))

        after = set(sys.path)
        if str(p) in after and str(p) not in before:
            added.append(p)

    return added


def check_dependencies() -> list[str]:
    """Check if required dependencies are installed. Returns list of missing packages."""
    global LAST_MISSING, LAST_ERROR
    ensure_site_packages_in_path()

    required = [
        ("fastmcp", "fastmcp"),
        ("httpx", "httpx"),
        ("tree_sitter", "tree-sitter"),
    ]

    missing = []
    for import_name, package_name in required:
        try:
            __import__(import_name)
        except Exception as e:
            # Print the real reason: many packages fail due to missing DLL / unprocessed .pth.
            print(f"[UnrealCopilot] Import check failed for {package_name}: {type(e).__name__}: {e}")
            LAST_ERROR = f"{package_name}: {type(e).__name__}: {e}"
            # Uncomment if you need deep debugging:
            # print(traceback.format_exc())
            missing.append(package_name)

    LAST_MISSING = list(missing)
    return missing


def run_uv_sync() -> bool:
    """Run `uv sync` to create/update .venv from pyproject.toml/uv.lock."""
    global LAST_ERROR
    python_dir = get_python_dir()
    pyproject_path = python_dir / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"[UnrealCopilot] Error: pyproject.toml not found at {pyproject_path}")
        return False

    print("[UnrealCopilot] Syncing dependencies with uv (creating .venv)...")

    try:
        result = subprocess.run(
            # Keep it simple: relies on pyproject.toml `requires-python` to select 3.11.
            ["uv", "sync"],
            cwd=str(python_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            venv_site = get_venv_site_packages()
            print(f"[UnrealCopilot] uv sync OK. venv site-packages: {venv_site}")
            return True
        else:
            print(f"[UnrealCopilot] Error: {result.stderr}")
            LAST_ERROR = result.stderr.strip() or "uv sync failed"
            return False

    except subprocess.TimeoutExpired:
        print("[UnrealCopilot] Error: uv sync timed out")
        LAST_ERROR = "uv sync timed out"
        return False
    except FileNotFoundError:
        print("[UnrealCopilot] Error: 'uv' not found. Install from https://docs.astral.sh/uv/")
        LAST_ERROR = "uv not found"
        return False
    except Exception as e:
        print(f"[UnrealCopilot] Error: {e}")
        LAST_ERROR = f"{type(e).__name__}: {e}"
        return False


def ensure_dependencies() -> bool:
    """
    Ensure all required dependencies are installed.
    Returns True if dependencies are available, False otherwise.
    """
    global LAST_MISSING, LAST_ERROR
    missing = check_dependencies()

    if not missing:
        LAST_MISSING = []
        LAST_ERROR = None
        print("[UnrealCopilot] All dependencies satisfied")
        return True

    print(f"[UnrealCopilot] Missing: {', '.join(missing)}")

    if run_uv_sync():
        # Refresh import system
        import importlib
        importlib.invalidate_caches()
        ensure_site_packages_in_path()

        # Verify installation
        missing = check_dependencies()
        if not missing:
            LAST_MISSING = []
            LAST_ERROR = None
            return True

        print(f"[UnrealCopilot] Still missing: {', '.join(missing)}")
        print("[UnrealCopilot] Restart editor after installation.")
        return False

    print("[UnrealCopilot] Auto-sync failed. Run manually:")
    print("  cd Content/Python && uv sync")
    return False


if __name__ == "__main__":
    sys.exit(0 if ensure_dependencies() else 1)

