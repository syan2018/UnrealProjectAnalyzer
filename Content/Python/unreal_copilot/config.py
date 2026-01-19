"""
Configuration management for Unreal Copilot.

Supports four-layer search model:
- project: Project Source + Project Plugins (default)
- engine: Engine Source + Engine Plugins
- plugin: All Plugins (project + engine)
- all: Everything

Configuration via environment variables:

C++ Analysis:
- CPP_SOURCE_PATH: Path to project's C++ source directory (required for C++ analysis)
- UNREAL_ENGINE_PATH: Path to Unreal installation (optional, for engine source)
- PROJECT_PLUGINS_PATH: Path to project plugins (optional, auto-detected)
- ENGINE_PLUGINS_PATH: Path to engine plugins (optional, derived from UNREAL_ENGINE_PATH)

Unreal Plugin Communication:
- UE_PLUGIN_HOST: Host for Unreal Plugin HTTP API (default: localhost)
- UE_PLUGIN_PORT: Port for Unreal Plugin HTTP API (default: 8080)

Cache Settings:
- ANALYZER_CACHE_ENABLED: Enable caching (default: true)
- ANALYZER_CACHE_MAX_SIZE: Maximum cache entries (default: 1000)

Search Defaults:
- DEFAULT_SEARCH_SCOPE: Default search scope (project/engine/plugin/all, default: project)
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal


class SourceType(str, Enum):
    """Type of source path for fine-grained scope control."""

    PROJECT_SOURCE = "project_source"    # <Project>/Source/
    PROJECT_PLUGIN = "project_plugin"    # <Project>/Plugins/*/Source/
    ENGINE_SOURCE = "engine_source"      # <Engine>/Engine/Source/
    ENGINE_PLUGIN = "engine_plugin"      # <Engine>/Engine/Plugins/*/Source/


class SearchScope(str, Enum):
    """Search scope for code analysis."""

    PROJECT = "project"  # Project Source + Project Plugins (default)
    ENGINE = "engine"    # Engine Source + Engine Plugins
    PLUGIN = "plugin"    # All Plugins (project + engine)
    ALL = "all"          # Everything


def _parse_bool(value: str | None, default: bool = True) -> bool:
    """Parse boolean from environment variable."""
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _parse_scope(value: str | None) -> SearchScope:
    """Parse search scope from environment variable."""
    if value is None:
        return SearchScope.PROJECT
    try:
        return SearchScope(value.lower())
    except ValueError:
        return SearchScope.PROJECT


def _find_project_root() -> Path | None:
    """
    Find the project root directory by looking for a .uproject file.

    Returns:
        Path to project root directory, or None if not found.
    """
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents][:8]:
        try:
            uprojects = list(parent.glob("*.uproject"))
        except Exception:
            uprojects = []
        if uprojects:
            return uprojects[0].parent
    return None


def _auto_detect_project_plugins_paths() -> list[str]:
    """
    Auto-detect all plugin Source directories under <Project>/Plugins/.

    Returns:
        List of paths to plugin Source directories.
    """
    candidates: list[str] = []

    project_root = _find_project_root()
    if not project_root:
        return candidates

    plugins_dir = project_root / "Plugins"
    if not plugins_dir.exists() or not plugins_dir.is_dir():
        return candidates

    # Find all plugin Source directories (Plugins/*/Source/)
    try:
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            source_dir = plugin_dir / "Source"
            if source_dir.exists() and source_dir.is_dir():
                candidates.append(str(source_dir.resolve()))
    except Exception:
        pass

    return candidates


def _auto_detect_engine_plugins_paths(engine_path: str) -> list[str]:
    """
    Auto-detect plugin Source directories under <Engine>/Engine/Plugins/.

    Args:
        engine_path: Path to Unreal Engine installation.

    Returns:
        List of paths to engine plugin Source directories.
    """
    candidates: list[str] = []

    engine_plugins_dir = Path(engine_path) / "Engine" / "Plugins"
    if not engine_plugins_dir.exists():
        return candidates

    # Recursively find all Source directories under Plugins
    # Engine plugins can be nested: Plugins/Runtime/*/Source/, Plugins/Editor/*/Source/, etc.
    try:
        for source_dir in engine_plugins_dir.rglob("Source"):
            if source_dir.is_dir():
                # Skip if it's a Source folder inside another Source folder
                if "Source" not in str(source_dir.parent).split("Source")[0].split("/")[-1:]:
                    candidates.append(str(source_dir.resolve()))
    except Exception:
        pass

    return candidates


def _auto_detect_project_source_paths() -> list[str]:
    """
    Best-effort auto detection of <Project>/Source when running from a plugin directory.

    This solves a common UX pitfall when users manually run the MCP server from:
      <Project>/Plugins/UnrealCopilot
    but forget to pass --cpp-source-path.
    """
    candidates: list[str] = []

    cwd = Path.cwd()
    # Walk up a few levels to find a *.uproject
    for parent in [cwd, *cwd.parents][:8]:
        try:
            uprojects = list(parent.glob("*.uproject"))
        except Exception:
            uprojects = []
        if not uprojects:
            continue

        # Prefer the first uproject found; use its directory.
        project_dir = uprojects[0].parent
        src = project_dir / "Source"
        if src.exists() and src.is_dir():
            candidates.append(str(src.resolve()))
        break

    return candidates


@dataclass
class SourceConfig:
    """Configuration for a source path with metadata."""

    path: str
    source_type: SourceType = SourceType.PROJECT_SOURCE
    label: str = ""

    # Legacy compatibility property
    @property
    def is_engine(self) -> bool:
        """Check if this is an engine path (for backward compatibility)."""
        return self.source_type in (SourceType.ENGINE_SOURCE, SourceType.ENGINE_PLUGIN)

    @property
    def is_plugin(self) -> bool:
        """Check if this is a plugin path."""
        return self.source_type in (SourceType.PROJECT_PLUGIN, SourceType.ENGINE_PLUGIN)

    def __post_init__(self):
        if not self.label:
            self.label = self.source_type.value


@dataclass
class Config:
    """Server configuration loaded from environment variables."""

    # Unreal Plugin HTTP API
    ue_plugin_host: str = field(default_factory=lambda: os.getenv("UE_PLUGIN_HOST", "localhost"))
    ue_plugin_port: int = field(default_factory=lambda: int(os.getenv("UE_PLUGIN_PORT", "8080")))

    # Source paths with scope metadata
    _source_configs: list[SourceConfig] = field(default_factory=list)

    # Legacy compatibility
    cpp_source_paths: list[str] = field(default_factory=list)

    # Cache settings
    cache_enabled: bool = field(
        default_factory=lambda: _parse_bool(os.getenv("ANALYZER_CACHE_ENABLED"), True)
    )
    cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("ANALYZER_CACHE_MAX_SIZE", "1000"))
    )

    # Default search scope
    default_scope: SearchScope = field(
        default_factory=lambda: _parse_scope(os.getenv("DEFAULT_SEARCH_SCOPE"))
    )

    def __post_init__(self):
        """Initialize paths from environment after dataclass init."""
        auto_detect = _parse_bool(os.getenv("ANALYZER_AUTO_DETECT_PROJECT_SOURCE"), True)

        # === Project Source ===
        cpp_source = os.getenv("CPP_SOURCE_PATH")
        if cpp_source:
            self.add_source_path(cpp_source, source_type=SourceType.PROJECT_SOURCE)
        elif auto_detect:
            for p in _auto_detect_project_source_paths():
                self.add_source_path(p, source_type=SourceType.PROJECT_SOURCE, label="auto_project")

        # === Project Plugins ===
        project_plugins = os.getenv("PROJECT_PLUGINS_PATH")
        if project_plugins:
            # User specified a single plugins root, scan for plugin Source dirs
            plugins_root = Path(project_plugins)
            if plugins_root.exists():
                for plugin_dir in plugins_root.iterdir():
                    if plugin_dir.is_dir():
                        source_dir = plugin_dir / "Source"
                        if source_dir.exists():
                            self.add_source_path(
                                str(source_dir), 
                                source_type=SourceType.PROJECT_PLUGIN,
                                label=plugin_dir.name
                            )
        elif auto_detect:
            for p in _auto_detect_project_plugins_paths():
                # Extract plugin name from path
                plugin_name = Path(p).parent.name
                self.add_source_path(p, source_type=SourceType.PROJECT_PLUGIN, label=plugin_name)

        # === Engine Source ===
        unreal_path = os.getenv("UNREAL_ENGINE_PATH")
        if unreal_path:
            engine_source = Path(unreal_path) / "Engine" / "Source"
            if engine_source.exists():
                self.add_source_path(str(engine_source), source_type=SourceType.ENGINE_SOURCE)
            else:
                # Fallback: user might have passed Engine/Source directly
                self.add_source_path(unreal_path, source_type=SourceType.ENGINE_SOURCE)

            # === Engine Plugins ===
            engine_plugins = os.getenv("ENGINE_PLUGINS_PATH")
            if engine_plugins:
                for p in _auto_detect_engine_plugins_paths(engine_plugins):
                    plugin_name = Path(p).parent.name
                    self.add_source_path(p, source_type=SourceType.ENGINE_PLUGIN, label=plugin_name)
            else:
                # Auto-detect engine plugins from UNREAL_ENGINE_PATH
                for p in _auto_detect_engine_plugins_paths(unreal_path):
                    plugin_name = Path(p).parent.name
                    self.add_source_path(p, source_type=SourceType.ENGINE_PLUGIN, label=plugin_name)

    @property
    def ue_plugin_url(self) -> str:
        """Get the full URL for Unreal plugin API."""
        return f"http://{self.ue_plugin_host}:{self.ue_plugin_port}"

    def add_source_path(
        self,
        path: str | Path,
        source_type: SourceType = SourceType.PROJECT_SOURCE,
        is_engine: bool = False,  # Legacy parameter, ignored if source_type is provided
        label: str = "",
    ) -> None:
        """Add a C++ source path for analysis with scope metadata.

        Args:
            path: Path to the source directory
            source_type: Type of source (project_source, project_plugin, etc.)
            is_engine: Legacy parameter for backward compatibility
            label: Optional label for this source (e.g., "lyra", "engine")
        """
        path_str = str(Path(path).resolve())

        # Check for duplicates
        for cfg in self._source_configs:
            if cfg.path == path_str:
                return

        # Handle legacy is_engine parameter
        if source_type == SourceType.PROJECT_SOURCE and is_engine:
            source_type = SourceType.ENGINE_SOURCE

        self._source_configs.append(
            SourceConfig(
                path=path_str,
                source_type=source_type,
                label=label or source_type.value,
            )
        )

        # Legacy compatibility
        if path_str not in self.cpp_source_paths:
            self.cpp_source_paths.append(path_str)

    def get_source_paths(
        self, scope: SearchScope | Literal["project", "engine", "plugin", "all"] | None = None
    ) -> list[str]:
        """Get source paths filtered by scope.

        Args:
            scope: Search scope (project, engine, plugin, all). If None, uses default_scope.

        Returns:
            List of source paths matching the scope.

        Scope semantics:
            - project: PROJECT_SOURCE + PROJECT_PLUGIN
            - engine: ENGINE_SOURCE + ENGINE_PLUGIN
            - plugin: PROJECT_PLUGIN + ENGINE_PLUGIN (all plugins only)
            - all: Everything
        """
        if scope is None:
            scope = self.default_scope
        elif isinstance(scope, str):
            try:
                scope = SearchScope(scope)
            except ValueError:
                scope = self.default_scope

        if scope == SearchScope.ALL:
            return [cfg.path for cfg in self._source_configs]
        elif scope == SearchScope.PLUGIN:
            # All plugins only (project + engine plugins)
            return [cfg.path for cfg in self._source_configs if cfg.is_plugin]
        elif scope == SearchScope.ENGINE:
            # Engine source + engine plugins
            return [
                cfg.path for cfg in self._source_configs
                if cfg.source_type in (SourceType.ENGINE_SOURCE, SourceType.ENGINE_PLUGIN)
            ]
        else:  # PROJECT (default)
            # Project source + project plugins
            return [
                cfg.path for cfg in self._source_configs
                if cfg.source_type in (SourceType.PROJECT_SOURCE, SourceType.PROJECT_PLUGIN)
            ]

    def get_project_paths(self) -> list[str]:
        """Get project paths (Source + Plugins) - convenience method."""
        return self.get_source_paths(SearchScope.PROJECT)

    def get_engine_paths(self) -> list[str]:
        """Get engine paths (Source + Plugins) - convenience method."""
        return self.get_source_paths(SearchScope.ENGINE)

    def get_plugin_paths(self) -> list[str]:
        """Get all plugin paths (project + engine) - convenience method."""
        return self.get_source_paths(SearchScope.PLUGIN)

    def get_project_source_only(self) -> list[str]:
        """Get project Source directory only (no plugins)."""
        return [
            cfg.path for cfg in self._source_configs
            if cfg.source_type == SourceType.PROJECT_SOURCE
        ]

    def get_project_plugins_only(self) -> list[str]:
        """Get project Plugins directories only."""
        return [
            cfg.path for cfg in self._source_configs
            if cfg.source_type == SourceType.PROJECT_PLUGIN
        ]

    def has_engine_source(self) -> bool:
        """Check if engine source paths are configured."""
        return any(cfg.is_engine for cfg in self._source_configs)

    def has_project_source(self) -> bool:
        """Check if project source paths are configured."""
        return any(not cfg.is_engine for cfg in self._source_configs)

    def has_plugin_source(self) -> bool:
        """Check if any plugin paths are configured."""
        return any(cfg.is_plugin for cfg in self._source_configs)

    def get_source_configs(self) -> list[SourceConfig]:
        """Get all source configurations (for debugging/inspection)."""
        return list(self._source_configs)


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration (useful for testing)."""
    global _config
    _config = None


