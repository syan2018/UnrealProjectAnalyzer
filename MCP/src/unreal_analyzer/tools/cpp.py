"""
C++ source code analysis tools.

These tools use tree-sitter to analyze C++ source files directly,
without requiring communication with the Unreal Editor.

Core capabilities for reference chain tracing:
- Class structure analysis
- Inheritance hierarchy discovery
- Code search and reference finding
- UE pattern detection (UPROPERTY/UFUNCTION exposure)
- Blueprint exposure analysis

Supports three-layer search scope:
- project: Project C++ source only (default, faster)
- engine: Unreal Engine source only
- all: Both project and engine (slower but comprehensive)

Configuration is done via environment variables:
- CPP_SOURCE_PATH: Path to C++ source directory (required)
- UNREAL_ENGINE_PATH: Optional path to Unreal installation for engine source analysis
"""

from typing import Annotated, Literal

from ..cpp_analyzer import get_analyzer

# Type alias for scope parameter
ScopeType = Literal["project", "engine", "all"]


# ============================================================================
# Class Analysis Tools
# ============================================================================


async def analyze_cpp_class(
    class_name: str, source_path: str = "", scope: ScopeType = "project"
) -> dict:
    """
    Analyze a C++ class structure (tree-sitter).

    Args:
        class_name: C++ class name (e.g. `ACharacter`, `ULyraHealthComponent`).
        source_path: Optional explicit directory to search first.
        scope: Search scope: `project` (default) | `engine` | `all`.

    Returns:
        A dict with:
        - name: str
        - file: str
        - line: int
        - superclasses: list[str]
        - interfaces: list[str]
        - methods: list[dict]
        - properties: list[dict]
        - comments: list[str]
    """
    analyzer = get_analyzer()
    return await analyzer.analyze_class(class_name, source_path, scope=scope)


async def get_cpp_class_hierarchy(
    class_name: str, include_interfaces: bool = True, scope: ScopeType = "project"
) -> dict:
    """
    Get the inheritance hierarchy of a C++ class (tree-sitter).

    Args:
        class_name: C++ class name.
        include_interfaces: Include implemented interfaces in the result.
        scope: Search scope: `project` (default) | `engine` | `all`.

    Returns:
        A dict:
        - class: str
        - superclasses: list[dict] (recursive)
        - interfaces: list[str]
    """
    analyzer = get_analyzer()
    return await analyzer.find_class_hierarchy(class_name, include_interfaces, scope=scope)


# ============================================================================
# Code Search Tools
# ============================================================================


async def search_cpp_code(
    query: str,
    file_pattern: str = "*.{h,cpp}",
    include_comments: bool = True,
    scope: ScopeType = "project",
    max_results: int = 500,
) -> dict:
    """
    Search C++ source code (regex) (tree-sitter).

    Args:
        query: Regex query.
        file_pattern: File glob pattern (default: `*.{h,cpp}`).
        include_comments: Include matches in comment lines.
        scope: Search scope: `project` (default) | `engine` | `all`.
        max_results: Limit returned matches.

    Returns:
        A dict:
        - matches: list[dict]
        - count: int
        - scope: str
        - truncated: bool
    """
    analyzer = get_analyzer()
    return await analyzer.search_code(
        query, file_pattern, include_comments, scope=scope, max_results=max_results
    )


async def find_cpp_references(
    identifier: str,
    ref_type: Literal["class", "function", "variable"] | None = None,
    scope: ScopeType = "project",
) -> dict:
    """
    Find references to a C++ identifier (best-effort) (tree-sitter/regex).

    Args:
        identifier: Identifier name.
        ref_type: Optional filter (currently best-effort; may be ignored).
        scope: Search scope: `project` (default) | `engine` | `all`.

    Returns:
        A dict:
        - matches: list[dict]
        - count: int
        - scope: str
    """
    analyzer = get_analyzer()
    return await analyzer.find_references(identifier, ref_type, scope=scope)


# ============================================================================
# UE Pattern Detection Tools
# ============================================================================


async def detect_ue_patterns(
    file_path: Annotated[str, "C++ file path (.h/.cpp) to scan for UPROPERTY/UFUNCTION/UCLASS"],
) -> dict:
    """
    Detect Unreal Engine patterns in a C++ file.

    Analyzes a file for UE-specific macros that determine Blueprint exposure.
    Critical for understanding the C++ → Blueprint boundary.

    Detects:
    - UPROPERTY: Properties exposed to Blueprints
    - UFUNCTION: Functions callable from Blueprints
    - UCLASS/USTRUCT/UENUM: Type declarations
    - Replication specifiers

    Args:
        file_path: Path to the C++ header or source file

    Returns:
        Dictionary containing:
        - file: Path to the analyzed file
        - patterns: List of detected patterns, each with:
            - pattern_type: UPROPERTY, UFUNCTION, UCLASS, etc.
            - name: Name of the property/function/class
            - specifiers: List of specifiers used
            - line: Line number
            - context: Surrounding code
            - is_blueprint_exposed: Whether exposed to Blueprints
            - is_replicated: Whether marked for replication

    Example:
        >>> await detect_ue_patterns("Source/MyGame/MyActor.h")
        {
            "patterns": [
                {
                    "pattern_type": "UPROPERTY",
                    "name": "Health",
                    "specifiers": ["BlueprintReadWrite", "Replicated"],
                    "is_blueprint_exposed": true,
                    "is_replicated": true
                },
                {
                    "pattern_type": "UFUNCTION",
                    "name": "TakeDamage",
                    "specifiers": ["BlueprintCallable"],
                    "is_blueprint_exposed": true
                }
            ]
        }
    """
    analyzer = get_analyzer()
    return await analyzer.detect_patterns(file_path)


async def get_cpp_blueprint_exposure(
    file_path: Annotated[str, "C++ header file path (.h) to summarize Blueprint-exposed API"],
) -> dict:
    """
    Get all Blueprint-exposed API from a C++ file.

    Extracts a summary of everything in a C++ header that is accessible
    from Blueprints. This is the key tool for understanding the
    C++ → Blueprint interface boundary.

    Args:
        file_path: Path to the C++ header file

    Returns:
        Dictionary containing:
        - file: Path to the analyzed file
        - blueprint_callable_functions: Functions with BlueprintCallable
        - blueprint_pure_functions: Functions with BlueprintPure
        - blueprint_events: Functions with BlueprintImplementableEvent/NativeEvent
        - blueprint_readable_properties: Properties readable in Blueprints
        - blueprint_writable_properties: Properties writable in Blueprints
        - blueprintable_classes: Classes that can be Blueprint parents

    Example:
        >>> await get_cpp_blueprint_exposure("Source/MyGame/MyActor.h")
        {
            "file": "Source/MyGame/MyActor.h",
            "blueprint_callable_functions": ["TakeDamage", "Heal", "GetHealth"],
            "blueprint_pure_functions": ["GetHealthPercent"],
            "blueprint_events": ["OnDeath"],
            "blueprint_readable_properties": ["Health", "MaxHealth"],
            "blueprint_writable_properties": ["Health"],
            "blueprintable_classes": ["AMyActor"]
        }
    """
    analyzer = get_analyzer()
    return await analyzer.get_blueprint_exposure(file_path)
