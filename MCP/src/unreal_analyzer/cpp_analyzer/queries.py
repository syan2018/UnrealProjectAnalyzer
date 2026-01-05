"""
Tree-sitter query patterns for C++ analysis.

These patterns efficiently extract class structures, methods,
and other code elements from parsed AST.
"""

# ============================================================================
# Common Query Patterns for C++ Parsing
# ============================================================================

QUERY_PATTERNS = {
    # Match class definitions with name and body
    "CLASS": """
        (class_specifier
            name: (type_identifier) @class_name
            body: (field_declaration_list)? @class_body) @class
    """,
    
    # Match struct definitions
    "STRUCT": """
        (struct_specifier
            name: (type_identifier) @struct_name
            body: (field_declaration_list)? @struct_body) @struct
    """,
    
    # Match function definitions
    "FUNCTION": """
        (function_definition
            declarator: (function_declarator
                declarator: (identifier) @func_name
                parameters: (parameter_list) @params)) @function
    """,
    
    # Match field declarations (class members)
    "FIELD_DECLARATION": """
        (field_declaration
            type: (_) @field_type
            declarator: (_) @field_name) @field
    """,
    
    # Match base class clauses
    "BASE_CLASS": """
        (base_class_clause
            (type_identifier) @base_class)
    """,
    
    # Match type identifiers
    "TYPE_IDENTIFIER": """
        (type_identifier) @type_id
    """,
    
    # Match identifiers
    "IDENTIFIER": """
        (identifier) @id
    """,
    
    # Match include directives
    "INCLUDE": """
        (preproc_include
            path: (_) @include_path) @include
    """,
}


def get_query_pattern(name: str) -> str | None:
    """
    Get a query pattern by name.
    
    Args:
        name: Name of the query pattern
    
    Returns:
        Query pattern string or None if not found
    """
    return QUERY_PATTERNS.get(name)
