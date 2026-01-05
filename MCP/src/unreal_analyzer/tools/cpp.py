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

Configuration is done via environment variables:
- CPP_SOURCE_PATH: Path to C++ source directory (required)
- UNREAL_ENGINE_PATH: Optional path to Unreal installation for engine source analysis
"""

from typing import Literal

from ..cpp_analyzer import get_analyzer


# ============================================================================
# Class Analysis Tools
# ============================================================================

async def analyze_cpp_class(class_name: str, source_path: str = "") -> dict:
    """
    Analyze a C++ class structure.
    
    Extracts detailed information about a class including its methods,
    properties, inheritance, and documentation. Essential for understanding
    how C++ classes expose functionality to Blueprints.
    
    Args:
        class_name: Name of the C++ class (e.g., "ACharacter", "UActorComponent")
        source_path: Optional specific source directory to search
    
    Returns:
        Dictionary containing:
        - name: Class name
        - file: Source file path
        - line: Line number of definition
        - superclasses: List of parent classes
        - interfaces: List of implemented interfaces
        - methods: List of methods with signatures, parameters, visibility
        - properties: List of properties with types and visibility
        - comments: Documentation comments
    
    Example:
        >>> await analyze_cpp_class("ACharacter")
        {
            "name": "ACharacter",
            "file": ".../Character.h",
            "superclasses": ["APawn"],
            "methods": [...],
            ...
        }
    """
    analyzer = get_analyzer()
    return await analyzer.analyze_class(class_name, source_path)


async def get_cpp_class_hierarchy(class_name: str, include_interfaces: bool = True) -> dict:
    """
    Get the inheritance hierarchy of a C++ class.
    
    Recursively traces the class inheritance chain. Critical for understanding
    Blueprint class hierarchies that extend C++ base classes.
    
    Args:
        class_name: Name of the C++ class
        include_interfaces: Whether to include implemented interfaces
    
    Returns:
        Dictionary containing:
        - class: Root class name
        - superclasses: Recursive hierarchy of parent classes
        - interfaces: Implemented interfaces (if include_interfaces=True)
    
    Example:
        >>> await get_cpp_class_hierarchy("ACharacter")
        {
            "class": "ACharacter",
            "superclasses": [
                {
                    "class": "APawn",
                    "superclasses": [
                        {"class": "AActor", "superclasses": [...]}
                    ]
                }
            ],
            "interfaces": ["INavAgentInterface"]
        }
    """
    analyzer = get_analyzer()
    return await analyzer.find_class_hierarchy(class_name, include_interfaces)


# ============================================================================
# Code Search Tools
# ============================================================================

async def search_cpp_code(
    query: str,
    file_pattern: str = "*.{h,cpp}",
    include_comments: bool = True
) -> dict:
    """
    Search through C++ source code.
    
    Performs regex-based search to find code patterns, function calls,
    or any text in source files. Useful for tracing where specific
    classes or functions are used.
    
    Args:
        query: Search query (supports regex patterns)
        file_pattern: File pattern to search (default: "*.{h,cpp}")
        include_comments: Whether to include matches in comments
    
    Returns:
        Dictionary containing:
        - matches: List of matches with file, line, column, and context
        - count: Total number of matches
    
    Example:
        >>> await search_cpp_code("TryActivateAbility")
        {
            "matches": [
                {
                    "file": ".../AbilitySystemComponent.cpp",
                    "line": 234,
                    "context": "void UAbilitySystemComponent::TryActivateAbility(...)"
                }
            ],
            "count": 15
        }
    """
    analyzer = get_analyzer()
    return await analyzer.search_code(query, file_pattern, include_comments)


async def find_cpp_references(
    identifier: str,
    ref_type: Literal['class', 'function', 'variable'] | None = None
) -> dict:
    """
    Find all references to a C++ identifier.
    
    Searches for all occurrences of a class, function, or variable name.
    Essential for tracing how C++ code is used across the codebase.
    
    Args:
        identifier: Name of the class, function, or variable
        ref_type: Optional type filter to narrow search results
    
    Returns:
        Dictionary containing:
        - matches: List of references with file, line, and context
        - count: Number of references found
    
    Example:
        >>> await find_cpp_references("UAbilitySystemComponent", "class")
        {
            "matches": [
                {"file": ".../Character.h", "line": 55, "context": "..."},
                {"file": ".../Ability.cpp", "line": 12, "context": "..."}
            ],
            "count": 47
        }
    """
    analyzer = get_analyzer()
    return await analyzer.find_references(identifier, ref_type)


# ============================================================================
# UE Pattern Detection Tools
# ============================================================================

async def detect_ue_patterns(file_path: str) -> dict:
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


async def get_cpp_blueprint_exposure(file_path: str) -> dict:
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
