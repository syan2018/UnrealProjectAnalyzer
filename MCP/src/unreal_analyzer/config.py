"""
Configuration management for Unreal Project Analyzer.

Supports three-layer search model:
- project: Game/project C++ source code and blueprints (default)
- engine: Unreal Engine source code
- all: Both project and engine

Configuration via environment variables:

C++ Analysis:
- CPP_SOURCE_PATH: Path to project's C++ source directory (required for C++ analysis)
- UNREAL_ENGINE_PATH: Path to Unreal installation (optional, for engine source)

Unreal Plugin Communication:
- UE_PLUGIN_HOST: Host for Unreal Plugin HTTP API (default: localhost)
- UE_PLUGIN_PORT: Port for Unreal Plugin HTTP API (default: 8080)

Cache Settings:
- ANALYZER_CACHE_ENABLED: Enable caching (default: true)
- ANALYZER_CACHE_MAX_SIZE: Maximum cache entries (default: 1000)

Search Defaults:
- DEFAULT_SEARCH_SCOPE: Default search scope (project/engine/all, default: project)
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal


class SearchScope(str, Enum):
    """Search scope for code analysis."""

    PROJECT = "project"  # Project source only (default)
    ENGINE = "engine"  # Engine source only
    ALL = "all"  # Both project and engine


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


def _auto_detect_project_source_paths() -> list[str]:
    """
    Best-effort auto detection of <Project>/Source when running from a plugin directory.

    This solves a common UX pitfall when users manually run the MCP server from:
      <Project>/Plugins/UnrealProjectAnalyzer
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
    is_engine: bool = False
    label: str = ""

    def __post_init__(self):
        if not self.label:
            self.label = "engine" if self.is_engine else "project"


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
        # Add CPP_SOURCE_PATH as project source
        cpp_source = os.getenv("CPP_SOURCE_PATH")
        if cpp_source:
            self.add_source_path(cpp_source, is_engine=False)
        else:
            # Auto-detect project Source if not provided (opt-out via env var).
            auto_detect = _parse_bool(os.getenv("ANALYZER_AUTO_DETECT_PROJECT_SOURCE"), True)
            if auto_detect:
                for p in _auto_detect_project_source_paths():
                    self.add_source_path(p, is_engine=False, label="auto_project")

        # Add UNREAL_ENGINE_PATH as engine source
        unreal_path = os.getenv("UNREAL_ENGINE_PATH")
        if unreal_path:
            self.add_source_path(unreal_path, is_engine=True)

    @property
    def ue_plugin_url(self) -> str:
        """Get the full URL for Unreal plugin API."""
        return f"http://{self.ue_plugin_host}:{self.ue_plugin_port}"

    def add_source_path(self, path: str | Path, is_engine: bool = False, label: str = "") -> None:
        """Add a C++ source path for analysis with scope metadata.

        Args:
            path: Path to the source directory
            is_engine: Whether this is an engine path (affects search scope)
            label: Optional label for this source (e.g., "lyra", "engine")
        """
        path_str = str(Path(path).resolve())

        # Check for duplicates
        for cfg in self._source_configs:
            if cfg.path == path_str:
                return

        self._source_configs.append(
            SourceConfig(
                path=path_str,
                is_engine=is_engine,
                label=label or ("engine" if is_engine else "project"),
            )
        )

        # Legacy compatibility
        if path_str not in self.cpp_source_paths:
            self.cpp_source_paths.append(path_str)

    def get_source_paths(
        self, scope: SearchScope | Literal["project", "engine", "all"] | None = None
    ) -> list[str]:
        """Get source paths filtered by scope.

        Args:
            scope: Search scope (project, engine, all). If None, uses default_scope.

        Returns:
            List of source paths matching the scope.
        """
        if scope is None:
            scope = self.default_scope
        elif isinstance(scope, str):
            scope = SearchScope(scope)

        if scope == SearchScope.ALL:
            return [cfg.path for cfg in self._source_configs]
        elif scope == SearchScope.ENGINE:
            return [cfg.path for cfg in self._source_configs if cfg.is_engine]
        else:  # PROJECT
            return [cfg.path for cfg in self._source_configs if not cfg.is_engine]

    def get_project_paths(self) -> list[str]:
        """Get project-only source paths (convenience method)."""
        return self.get_source_paths(SearchScope.PROJECT)

    def get_engine_paths(self) -> list[str]:
        """Get engine-only source paths (convenience method)."""
        return self.get_source_paths(SearchScope.ENGINE)

    def has_engine_source(self) -> bool:
        """Check if engine source paths are configured."""
        return any(cfg.is_engine for cfg in self._source_configs)

    def has_project_source(self) -> bool:
        """Check if project source paths are configured."""
        return any(not cfg.is_engine for cfg in self._source_configs)


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
