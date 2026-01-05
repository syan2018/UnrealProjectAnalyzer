"""
Unreal Plugin HTTP Client.

Provides communication with the UnrealProjectAnalyzer plugin running in the Editor.
"""

from .http_client import UEPluginClient, get_client

__all__ = ["UEPluginClient", "get_client"]
