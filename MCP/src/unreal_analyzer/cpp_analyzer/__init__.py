"""
C++ Source Code Analyzer.

Uses tree-sitter to parse and analyze C++ source files.
Focused on reference chain tracing across Blueprint ↔ C++ boundaries.

Key Components:
- CppAnalyzer: Main analyzer class
- get_analyzer(): Get the global analyzer instance
- detect_ue_pattern(): Detect UPROPERTY/UFUNCTION/UCLASS patterns
"""

from .analyzer import (
    CppAnalyzer,
    get_analyzer,
    set_analyzer,
    ClassInfo,
    MethodInfo,
    PropertyInfo,
    ParameterInfo,
    CodeReference,
    ClassHierarchy,
)
from .patterns import (
    UE_PATTERNS,
    BLUEPRINT_SPECIFIERS,
    REPLICATION_SPECIFIERS,
    detect_ue_pattern,
    parse_specifiers,
)
from .queries import (
    QUERY_PATTERNS,
    get_query_pattern,
)

__all__ = [
    # Analyzer
    "CppAnalyzer",
    "get_analyzer",
    "set_analyzer",
    # Data classes
    "ClassInfo",
    "MethodInfo",
    "PropertyInfo",
    "ParameterInfo",
    "CodeReference",
    "ClassHierarchy",
    # Patterns
    "UE_PATTERNS",
    "BLUEPRINT_SPECIFIERS",
    "REPLICATION_SPECIFIERS",
    "detect_ue_pattern",
    "parse_specifiers",
    # Queries
    "QUERY_PATTERNS",
    "get_query_pattern",
]
