"""
Configuration management for UE5 Project Analyzer.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Server configuration."""
    
    # UE5 Plugin HTTP API
    ue_plugin_host: str = field(default_factory=lambda: os.getenv("UE_PLUGIN_HOST", "localhost"))
    ue_plugin_port: int = field(default_factory=lambda: int(os.getenv("UE_PLUGIN_PORT", "8080")))
    
    # C++ Source paths (for tree-sitter analysis)
    cpp_source_paths: list[str] = field(default_factory=list)
    
    # Cache settings
    cache_enabled: bool = True
    cache_max_size: int = 1000
    
    @property
    def ue_plugin_url(self) -> str:
        """Get the full URL for UE5 plugin API."""
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
