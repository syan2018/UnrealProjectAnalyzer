"""
Python Bridge Server for UE5 Project Analyzer.

This script runs inside the Unreal Editor Python environment.
It provides supplementary APIs that cannot be implemented in C++.

The bridge is automatically started by the C++ plugin module.
"""

import unreal
import threading
import json

# Bridge configuration
BRIDGE_PORT = 8081  # Different from main HTTP server

# Flag to control the bridge lifecycle
_running = False


def start_bridge():
    """Start the Python bridge server."""
    global _running
    
    if _running:
        unreal.log_warning("UE5ProjectAnalyzer: Python bridge already running")
        return
    
    _running = True
    unreal.log("UE5ProjectAnalyzer: Python bridge started on port {}".format(BRIDGE_PORT))
    
    # TODO: Implement actual TCP/HTTP server if needed
    # For now, we expose functions that C++ can call directly via Python API


def stop_bridge():
    """Stop the Python bridge server."""
    global _running
    _running = False
    unreal.log("UE5ProjectAnalyzer: Python bridge stopped")


# ============================================================================
# Bridge API Functions
# These can be called from C++ via the Python scripting interface
# ============================================================================

def get_asset_registry():
    """Get the asset registry instance."""
    return unreal.AssetRegistryHelpers.get_asset_registry()


def get_asset_dependencies(asset_path: str) -> dict:
    """Get dependencies of an asset using Python API.
    
    Args:
        asset_path: The asset path (e.g., "/Game/Blueprints/BP_Player")
    
    Returns:
        Dictionary with dependencies
    """
    registry = get_asset_registry()
    
    # Get dependencies
    dependencies = registry.get_dependencies(asset_path)
    
    return {
        "asset": asset_path,
        "dependencies": [str(dep) for dep in dependencies],
        "count": len(dependencies),
    }


def get_asset_referencers(asset_path: str) -> dict:
    """Get referencers of an asset using Python API.
    
    Args:
        asset_path: The asset path
    
    Returns:
        Dictionary with referencers
    """
    registry = get_asset_registry()
    
    # Get referencers
    referencers = registry.get_referencers(asset_path)
    
    return {
        "asset": asset_path,
        "referencers": [str(ref) for ref in referencers],
        "count": len(referencers),
    }


def search_assets_by_class(class_name: str) -> dict:
    """Search for assets by class name.
    
    Args:
        class_name: The class name to search for
    
    Returns:
        Dictionary with matching assets
    """
    registry = get_asset_registry()
    
    # Get assets by class
    assets = registry.get_assets_by_class(class_name)
    
    return {
        "class": class_name,
        "assets": [
            {
                "name": str(asset.asset_name),
                "path": str(asset.package_name),
                "class": str(asset.asset_class),
            }
            for asset in assets
        ],
        "count": len(assets),
    }


def get_blueprint_for_class(class_path: str) -> dict:
    """Get the Blueprint that generated a class.
    
    Args:
        class_path: The class path
    
    Returns:
        Dictionary with Blueprint info
    """
    # Load the class
    loaded_class = unreal.load_class(None, class_path)
    
    if not loaded_class:
        return {"error": "Class not found", "class": class_path}
    
    # Check if it's a Blueprint-generated class
    blueprint = unreal.BlueprintEditorLibrary.get_blueprint_for_class(loaded_class)
    
    if blueprint:
        return {
            "class": class_path,
            "blueprint": str(blueprint.get_path_name()),
            "is_blueprint_class": True,
        }
    else:
        return {
            "class": class_path,
            "blueprint": None,
            "is_blueprint_class": False,
        }


# Auto-start if loaded
if __name__ != "__main__":
    # We're being imported/exec'd by UE
    start_bridge()
