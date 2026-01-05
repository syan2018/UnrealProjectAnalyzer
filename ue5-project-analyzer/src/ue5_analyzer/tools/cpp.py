"""
C++ source code analysis tools.

These tools use tree-sitter to analyze C++ source files directly,
without requiring communication with the UE5 Editor.
"""

from ..cpp_analyzer import get_analyzer


async def analyze_cpp_class(class_name: str, source_path: str = "") -> dict:
    """Analyze a C++ class structure.
    
    Args:
        class_name: Name of the C++ class (e.g., "ACharacter", "UActorComponent")
        source_path: Optional specific source directory to search
    
    Returns:
        Dictionary containing:
        - name: Class name
        - file: Source file path
        - line: Line number of definition
        - superclasses: List of parent classes
        - methods: List of methods with signatures
        - properties: List of properties
        - comments: Documentation comments
    """
    analyzer = get_analyzer()
    return await analyzer.analyze_class(class_name, source_path)


async def get_cpp_class_hierarchy(class_name: str) -> dict:
    """Get the inheritance hierarchy of a C++ class.
    
    Args:
        class_name: Name of the C++ class
    
    Returns:
        Dictionary containing:
        - class: Root class name
        - superclasses: Recursive hierarchy of parent classes
        - interfaces: Implemented interfaces
    """
    analyzer = get_analyzer()
    return await analyzer.find_class_hierarchy(class_name)


async def search_cpp_code(query: str, file_pattern: str = "*.h") -> dict:
    """Search through C++ source code.
    
    Args:
        query: Search query (supports regex)
        file_pattern: File pattern to search (default: "*.h")
    
    Returns:
        Dictionary containing:
        - matches: List of matches with file, line, and context
        - count: Number of matches
    """
    analyzer = get_analyzer()
    return await analyzer.search_code(query, file_pattern)


async def find_cpp_references(identifier: str, ref_type: str = "") -> dict:
    """Find all references to a C++ identifier.
    
    Args:
        identifier: Name of the class, function, or variable
        ref_type: Optional type filter ("class", "function", "variable")
    
    Returns:
        Dictionary containing:
        - references: List of references with file, line, and context
        - count: Number of references
    """
    analyzer = get_analyzer()
    return await analyzer.find_references(identifier, ref_type)


async def detect_ue_patterns(file_path: str) -> dict:
    """Detect Unreal Engine patterns in a C++ file.
    
    Detects:
    - UPROPERTY declarations and specifiers
    - UFUNCTION declarations and specifiers
    - UCLASS/USTRUCT/UENUM declarations
    - Component setup patterns
    - Event binding patterns
    
    Args:
        file_path: Path to the C++ header file
    
    Returns:
        Dictionary containing:
        - patterns: List of detected patterns with details
        - suggestions: Improvement suggestions
    """
    analyzer = get_analyzer()
    return await analyzer.detect_patterns(file_path)


async def get_cpp_blueprint_exposure(file_path: str) -> dict:
    """Get all Blueprint-exposed API from a C++ file.
    
    Args:
        file_path: Path to the C++ header file
    
    Returns:
        Dictionary containing:
        - classes: List of classes with:
            - blueprint_callable_functions
            - blueprint_pure_functions
            - blueprint_events
            - blueprint_readable_properties
            - blueprint_writable_properties
    """
    analyzer = get_analyzer()
    return await analyzer.get_blueprint_exposure(file_path)
