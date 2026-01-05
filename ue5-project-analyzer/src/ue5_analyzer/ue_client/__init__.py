"""
UE5 Plugin HTTP Client.

Provides communication with the UE5ProjectAnalyzer plugin running in the Editor.
"""

from .http_client import UEPluginClient, get_client

__all__ = ["UEPluginClient", "get_client"]
