"""
Configuration management for Unreal Project Analyzer.

All configuration is done via environment variables:

C++ Analysis:
- CPP_SOURCE_PATH: Path to project's C++ source directory (required for C++ analysis)
- UNREAL_ENGINE_PATH: Path to Unreal installation (optional, for engine source)

Unreal Plugin Communication:
- UE_PLUGIN_HOST: Host for Unreal Plugin HTTP API (default: localhost)
- UE_PLUGIN_PORT: Port for Unreal Plugin HTTP API (default: 8080)

Cache Settings:
- ANALYZER_CACHE_ENABLED: Enable caching (default: true)
- ANALYZER_CACHE_MAX_SIZE: Maximum cache entries (default: 1000)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _parse_bool(value: str | None, default: bool = True) -> bool:
    """Parse boolean from environment variable."""
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


@dataclass
class Config:
    """Server configuration loaded from environment variables."""
    
    # Unreal Plugin HTTP API
    ue_plugin_host: str = field(
        default_factory=lambda: os.getenv("UE_PLUGIN_HOST", "localhost")
    )
    ue_plugin_port: int = field(
        default_factory=lambda: int(os.getenv("UE_PLUGIN_PORT", "8080"))
    )
    
    # C++ Source paths (for tree-sitter analysis)
    cpp_source_paths: list[str] = field(default_factory=list)
    
    # Cache settings
    cache_enabled: bool = field(
        default_factory=lambda: _parse_bool(os.getenv("ANALYZER_CACHE_ENABLED"), True)
    )
    cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("ANALYZER_CACHE_MAX_SIZE", "1000"))
    )
    
    def __post_init__(self):
        """Initialize paths from environment after dataclass init."""
        # Add CPP_SOURCE_PATH if set
        cpp_source = os.getenv("CPP_SOURCE_PATH")
        if cpp_source:
            self.add_source_path(cpp_source)
        
        # Add UNREAL_ENGINE_PATH if set
        unreal_path = os.getenv("UNREAL_ENGINE_PATH")
        if unreal_path:
            self.add_source_path(unreal_path)
    
    @property
    def ue_plugin_url(self) -> str:
        """Get the full URL for Unreal plugin API."""
        return f"http://{self.ue_plugin_host}:{self.ue_plugin_port}"
    
    def add_source_path(self, path: str | Path) -> None:
        """Add a C++ source path for analysis."""
        path_str = str(Path(path).resolve())
        if path_str not in self.cpp_source_paths:
            self.cpp_source_paths.append(path_str)


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
