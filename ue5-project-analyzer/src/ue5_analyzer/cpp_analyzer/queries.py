"""
Tree-sitter query patterns for C++ analysis.
"""

# Common query patterns for C++ parsing
QUERY_PATTERNS = {
    # Match class definitions
    "CLASS": """
        (class_specifier
            name: (type_identifier) @class_name
            body: (field_declaration_list)? @class_body) @class
    """,
    
    # Match function definitions
    "FUNCTION": """
        (function_definition
            declarator: (function_declarator
                declarator: (identifier) @func_name
                parameters: (parameter_list) @params)) @function
    """,
    
    # Match type identifiers
    "TYPE_IDENTIFIER": """
        (type_identifier) @type_id
    """,
    
    # Match identifiers
    "IDENTIFIER": """
        (identifier) @id
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
}
