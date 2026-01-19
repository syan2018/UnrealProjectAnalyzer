"""
C++ Analyzer - Core analysis logic using tree-sitter.

Focused on analyzing C++ source code for Unreal projects to enable
reference chain tracing across Blueprint ↔ C++ boundaries.

Core capabilities:
- Class structure analysis (methods, properties, inheritance)
- Inheritance hierarchy discovery
- Code search and reference finding
- UE pattern detection (UPROPERTY, UFUNCTION, etc.)
- Blueprint exposure analysis

Supports four-layer search scope:
- project: Project Source + Project Plugins (default)
- engine: Engine Source + Engine Plugins
- plugin: All Plugins (project + engine)
- all: Everything
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser, QueryCursor
from tree_sitter import Query as TSQuery

from ..config import SearchScope, get_config
from .patterns import detect_ue_pattern, is_ue_macro_call
from .queries import QUERY_PATTERNS

# Type alias for scope parameter (includes new "plugin" scope)
ScopeType = SearchScope | Literal["project", "engine", "plugin", "all"] | None


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ParameterInfo:
    """Information about a function parameter."""

    name: str
    type: str
    default_value: str | None = None


@dataclass
class MethodInfo:
    """Information about a class method."""

    name: str
    return_type: str
    parameters: list[ParameterInfo] = field(default_factory=list)
    is_virtual: bool = False
    is_override: bool = False
    is_const: bool = False
    is_static: bool = False
    visibility: Literal["public", "protected", "private"] = "public"
    comments: list[str] = field(default_factory=list)
    line: int = 0


@dataclass
class PropertyInfo:
    """Information about a class property."""

    name: str
    type: str
    visibility: Literal["public", "protected", "private"] = "public"
    is_static: bool = False
    is_uproperty: bool = False  # Whether marked with UPROPERTY
    uproperty_specifiers: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    line: int = 0


@dataclass
class ClassInfo:
    """Information about a C++ class."""

    name: str
    file: str
    line: int
    superclasses: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    methods: list[MethodInfo] = field(default_factory=list)
    properties: list[PropertyInfo] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    is_uclass: bool = False
    uclass_specifiers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "file": self.file,
            "line": self.line,
            "superclasses": self.superclasses,
            "interfaces": self.interfaces,
            "is_uclass": self.is_uclass,
            "uclass_specifiers": self.uclass_specifiers,
            "methods": [
                {
                    "name": m.name,
                    "return_type": m.return_type,
                    "parameters": [
                        {"name": p.name, "type": p.type, "default_value": p.default_value}
                        for p in m.parameters
                    ],
                    "is_virtual": m.is_virtual,
                    "is_override": m.is_override,
                    "is_const": m.is_const,
                    "is_static": m.is_static,
                    "visibility": m.visibility,
                    "line": m.line,
                }
                for m in self.methods
            ],
            "properties": [
                {
                    "name": p.name,
                    "type": p.type,
                    "visibility": p.visibility,
                    "is_static": p.is_static,
                    "is_uproperty": p.is_uproperty,
                    "uproperty_specifiers": p.uproperty_specifiers,
                    "line": p.line,
                }
                for p in self.properties
            ],
            "comments": self.comments,
        }


@dataclass
class CodeReference:
    """A reference to code location."""

    file: str
    line: int
    column: int
    context: str


@dataclass
class ClassHierarchy:
    """Class inheritance hierarchy."""

    class_name: str
    superclasses: list["ClassHierarchy"] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "class": self.class_name,
            "superclasses": [s.to_dict() for s in self.superclasses],
            "interfaces": self.interfaces,
        }


# ============================================================================
# Main Analyzer Class
# ============================================================================


class CppAnalyzer:
    """
    C++ source code analyzer using tree-sitter.

    Focused on reference chain tracing capabilities:
    - Class structure analysis
    - Inheritance hierarchy discovery
    - Code reference finding
    - UE pattern detection (Blueprint exposure)

    Supports scope-based searching:
    - project: Project Source + Project Plugins (default)
    - engine: Engine Source + Engine Plugins
    - plugin: All Plugins (project + engine)
    - all: Everything
    """

    def __init__(self):
        """Initialize the analyzer."""
        self._language = Language(tscpp.language())
        self._parser = Parser(self._language)

        # Caches
        self._class_cache: dict[str, ClassInfo] = {}
        self._ast_cache: dict[str, Any] = {}
        self._query_cache: dict[str, TSQuery] = {}

        # Cache management
        self._max_cache_size = 1000
        self._cache_queue: list[str] = []

        # Path configuration (legacy, use config instead)
        self._unreal_path: str | None = None
        self._custom_path: str | None = None
        self._initialized: bool = False

        # Pre-compile common queries
        self._init_queries()

    def _init_queries(self) -> None:
        """Initialize commonly used queries."""
        for name, pattern in QUERY_PATTERNS.items():
            try:
                query = TSQuery(self._language, pattern)
                self._query_cache[name] = query
            except Exception as e:
                print(f"Warning: Failed to compile query '{name}': {e}")

    def _manage_cache(self, cache: dict, key: str, value: Any) -> None:
        """Manage cache size using FIFO eviction."""
        if len(cache) >= self._max_cache_size:
            if self._cache_queue:
                oldest = self._cache_queue.pop(0)
                cache.pop(oldest, None)

        cache[key] = value
        self._cache_queue.append(key)

    # ========================================================================
    # Initialization
    # ========================================================================

    def is_initialized(self) -> bool:
        """Check if the analyzer is initialized with a source path."""
        return self._initialized

    async def initialize(self, engine_path: str) -> None:
        """
        Initialize with Unreal Engine source path.

        Args:
            engine_path: Path to Unreal Engine installation
        """
        path = Path(engine_path)
        if not path.exists():
            raise ValueError(f"Invalid path: Directory does not exist - {engine_path}")

        self._unreal_path = str(path.resolve())
        self._initialized = True

        # Add to config as engine source
        config = get_config()
        config.add_source_path(engine_path, is_engine=True)

    async def initialize_custom_codebase(self, custom_path: str) -> None:
        """
        Initialize with a custom C++ codebase path.

        Args:
            custom_path: Path to the C++ source directory
        """
        path = Path(custom_path)
        if not path.exists():
            raise ValueError(f"Invalid path: Directory does not exist - {custom_path}")

        self._custom_path = str(path.resolve())
        self._initialized = True

        # Add to config as project source
        config = get_config()
        config.add_source_path(custom_path, is_engine=False)

    def _get_search_paths(self, scope: ScopeType = None, source_path: str = "") -> list[str]:
        """Get search paths based on scope.

        Args:
            scope: Search scope (project/engine/all). None uses config default.
            source_path: Optional specific path to search (overrides scope).

        Returns:
            List of paths to search.
        """
        if source_path:
            return [source_path]

        config = get_config()
        paths = config.get_source_paths(scope)

        # Fallback to legacy paths if no scoped paths configured
        if not paths:
            if self._custom_path:
                paths.append(self._custom_path)
            if self._unreal_path:
                paths.append(self._unreal_path)

        return paths

    # ========================================================================
    # File Parsing
    # ========================================================================

    async def _parse_file(self, file_path: str) -> Any:
        """Parse a C++ file and return the AST."""
        if file_path in self._ast_cache:
            return self._ast_cache[file_path]

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8", errors="ignore")
        tree = self._parser.parse(bytes(content, "utf-8"))

        self._manage_cache(self._ast_cache, file_path, tree)

        # Also extract and cache classes from this file
        await self._extract_classes_from_tree(tree, file_path, content)

        return tree

    async def _extract_classes_from_tree(
        self, tree: Any, file_path: str, content: str = ""
    ) -> None:
        """Extract and cache all classes from an AST."""
        query = self._query_cache.get("CLASS")
        if not query:
            return

        # py-tree-sitter >= 0.25: Query execution is done via QueryCursor
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)

        # Read content if not provided (for UPROPERTY detection)
        if not content:
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""

        for _, captured in matches:
            # captured: dict[str, list[Node]]
            name_nodes = captured.get("class_name") or []
            class_nodes = captured.get("class") or []
            body_nodes = captured.get("class_body") or []
            if not name_nodes or not class_nodes:
                continue

            # Skip forward declarations (no class body)
            if not body_nodes:
                continue

            class_name = name_nodes[0].text.decode(errors="ignore")
            class_node = class_nodes[0]

            class_info = self._extract_class_info(class_node, file_path, class_name, content)
            if class_info:
                self._class_cache[class_name] = class_info

    # ========================================================================
    # Class Analysis
    # ========================================================================

    def _extract_class_info(
        self, node: Any, file_path: str, class_name: str, content: str = ""
    ) -> ClassInfo | None:
        """Extract detailed class information from AST node."""
        class_info = ClassInfo(
            name=class_name,
            file=file_path,
            line=node.start_point[0] + 1,
        )

        # Check for UCLASS macro
        uclass_match = self._find_uclass_for_node(node, content)
        if uclass_match:
            class_info.is_uclass = True
            class_info.uclass_specifiers = uclass_match.get("specifiers", [])

        # Extract base classes / interfaces (multiple inheritance)
        base_types = self._extract_base_types(node)
        # Improved interface detection: check for 'I' prefix and common interface patterns
        class_info.superclasses = []
        class_info.interfaces = []
        for base in base_types:
            if self._is_interface_name(base):
                class_info.interfaces.append(base)
            else:
                class_info.superclasses.append(base)

        # Find the class body (field_declaration_list)
        body_node = None
        for child in node.children:
            if child.type == "field_declaration_list":
                body_node = child
                break

        if body_node:
            # Build a map of UPROPERTY/UFUNCTION declarations by line
            ue_macros_by_line = self._build_ue_macro_map(content) if content else {}

            # Extract methods and properties
            current_visibility = "private"  # Default for classes

            for child in body_node.children:
                # Check for access specifier
                if child.type == "access_specifier":
                    specifier_text = child.text.decode().strip().rstrip(":")
                    if specifier_text in ("public", "protected", "private"):
                        current_visibility = specifier_text

                # Skip UE macro calls (UPROPERTY, UFUNCTION, etc.) - they're not methods
                if child.type in ("function_definition", "declaration"):
                    child_text = child.text.decode() if child.text else ""
                    if not is_ue_macro_call(child_text):
                        method_info = self._extract_method_info(child, current_visibility)
                        if method_info:
                            class_info.methods.append(method_info)

                # Extract field declarations
                elif child.type == "field_declaration":
                    prop_info = self._extract_property_info(
                        child, current_visibility, ue_macros_by_line
                    )
                    if prop_info:
                        class_info.properties.append(prop_info)

        # Extract preceding comments
        class_info.comments = self._extract_comments(node)

        return class_info

    def _is_interface_name(self, name: str) -> bool:
        """Check if a class name is likely an interface.

        UE interfaces typically:
        - Start with 'I' followed by uppercase letter
        - End with 'Interface'
        """
        if not name:
            return False
        # Starts with I followed by uppercase (INavAgentInterface, IAbilitySystemInterface)
        if len(name) >= 2 and name[0] == "I" and name[1].isupper():
            return True
        # Ends with Interface
        if name.endswith("Interface"):
            return True
        return False

    def _find_uclass_for_node(self, class_node: Any, content: str) -> dict | None:
        """Find UCLASS macro that precedes this class node."""
        if not content:
            return None

        line_num = class_node.start_point[0]
        lines = content.split("\n")

        # Look backwards from class definition for UCLASS
        for i in range(line_num - 1, max(0, line_num - 10), -1):
            if i >= len(lines):
                continue
            line = lines[i]
            if "UCLASS" in line:
                # Extract specifiers
                match = re.search(r"UCLASS\s*\(([^)]*)\)", line)
                if match:
                    from .patterns import parse_specifiers

                    specifiers = parse_specifiers(match.group(1))
                    return {"specifiers": specifiers}
                return {"specifiers": []}

        return None

    def _build_ue_macro_map(self, content: str) -> dict[int, dict]:
        """Build a map of UE macros (UPROPERTY, UFUNCTION) by line number."""
        macro_map = {}
        lines = content.split("\n")

        for i, line in enumerate(lines):
            for macro in ["UPROPERTY", "UFUNCTION"]:
                if macro in line:
                    match = re.search(rf"{macro}\s*\(([^)]*)\)", line)
                    if match:
                        from .patterns import parse_specifiers

                        specifiers = parse_specifiers(match.group(1))
                        macro_map[i + 1] = {"macro": macro, "specifiers": specifiers}
                        macro_map[i + 2] = {
                            "macro": macro,
                            "specifiers": specifiers,
                        }  # Next line too

        return macro_map

    def _extract_base_types(self, class_node: Any) -> list[str]:
        """
        Extract base types from a class node.

        In tree-sitter-cpp, `base_class_clause` for a class like:
          class A : public B, public IInterface { ... }
        is represented as alternating `access_specifier` and `type_identifier` nodes.
        """
        bases: list[str] = []

        base_clause = None
        for child in class_node.children:
            if child.type == "base_class_clause":
                base_clause = child
                break
        if not base_clause:
            return bases

        for child in base_clause.children:
            if child.type in ("type_identifier", "qualified_identifier", "scoped_identifier"):
                text = child.text.decode(errors="ignore").strip()
                if not text:
                    continue
                # Handle qualified names like "public INavAgentInterface"
                base_name = text.split("::")[-1]
                if base_name and base_name not in ("public", "protected", "private"):
                    bases.append(base_name)

        return bases

    def _iter_descendants(self, node: Any) -> list[Any]:
        """
        Iterate all descendants of a node (depth-first).

        Note: py-tree-sitter Node does not expose a `.descendants` helper in 0.25.x,
        so we implement our own traversal using `.children`.
        """
        stack = list(getattr(node, "children", []) or [])
        while stack:
            cur = stack.pop()
            yield cur
            children = getattr(cur, "children", None)
            if children:
                stack.extend(children)

    def _extract_method_info(self, node: Any, visibility: str) -> MethodInfo | None:
        """Extract method information from a function node."""
        # Find the function declarator
        declarator = None
        for child in self._iter_descendants(node):
            if child.type == "function_declarator":
                declarator = child
                break

        if not declarator:
            return None

        method_info = MethodInfo(
            name="",
            return_type="",
            visibility=visibility,
            line=node.start_point[0] + 1,
        )

        # Extract method name
        for child in declarator.children:
            if child.type == "identifier":
                method_info.name = child.text.decode()
                break
            elif child.type == "field_identifier":
                method_info.name = child.text.decode()
                break
            elif child.type == "destructor_name":
                method_info.name = child.text.decode()
                break

        if not method_info.name:
            return None

        # Filter out UE macro names that look like methods
        if method_info.name in (
            "UPROPERTY",
            "UFUNCTION",
            "UCLASS",
            "USTRUCT",
            "UENUM",
            "GENERATED_BODY",
            "GENERATED_UCLASS_BODY",
            "GENERATED_USTRUCT_BODY",
        ):
            return None

        # Extract modifiers from node text
        node_text = node.text.decode()
        if "virtual" in node_text:
            method_info.is_virtual = True
        if "override" in node_text:
            method_info.is_override = True
        if "static" in node_text:
            method_info.is_static = True
        if node_text.rstrip().endswith("const"):
            method_info.is_const = True

        # Try to extract return type
        for child in node.children:
            if child.type in ("type_identifier", "primitive_type", "qualified_identifier"):
                method_info.return_type = child.text.decode()
                break

        # Extract parameters
        for child in declarator.children:
            if child.type == "parameter_list":
                method_info.parameters = self._extract_parameters(child)
                break

        return method_info

    def _extract_parameters(self, param_list: Any) -> list[ParameterInfo]:
        """Extract parameter information from a parameter list."""
        params = []

        for child in param_list.children:
            if child.type == "parameter_declaration":
                param = self._extract_single_parameter(child)
                if param:
                    params.append(param)

        return params

    def _extract_single_parameter(self, param_node: Any) -> ParameterInfo | None:
        """Extract a single parameter's information."""
        param_type = ""
        param_name = ""
        default_value = None

        for child in param_node.children:
            if child.type in ("type_identifier", "primitive_type", "qualified_identifier"):
                param_type = child.text.decode()
            elif child.type == "identifier":
                param_name = child.text.decode()
            elif child.type == "pointer_declarator":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        param_name = subchild.text.decode()
                param_type += "*"
            elif child.type == "reference_declarator":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        param_name = subchild.text.decode()
                param_type += "&"
            elif child.type == "optional_parameter_declaration":
                default_value = child.text.decode().split("=")[-1].strip()

        if param_type or param_name:
            return ParameterInfo(
                name=param_name or "unnamed",
                type=param_type or "unknown",
                default_value=default_value,
            )
        return None

    def _extract_property_info(
        self, node: Any, visibility: str, ue_macros_by_line: dict[int, dict] | None = None
    ) -> PropertyInfo | None:
        """Extract property information from a field declaration."""
        prop_type = ""
        prop_name = ""
        is_static = False

        node_text = node.text.decode()
        if "static" in node_text:
            is_static = True

        for child in node.children:
            if child.type in (
                "type_identifier",
                "primitive_type",
                "qualified_identifier",
                "template_type",
            ):
                prop_type = child.text.decode()
            elif child.type in ("identifier", "field_identifier"):
                prop_name = child.text.decode()
            elif child.type == "pointer_declarator":
                for subchild in child.children:
                    if subchild.type in ("identifier", "field_identifier"):
                        prop_name = subchild.text.decode()
                prop_type += "*"

        if prop_name:
            # Check for UPROPERTY
            line_num = node.start_point[0] + 1
            is_uproperty = False
            uproperty_specifiers = []

            if ue_macros_by_line:
                macro_info = ue_macros_by_line.get(line_num) or ue_macros_by_line.get(line_num - 1)
                if macro_info and macro_info.get("macro") == "UPROPERTY":
                    is_uproperty = True
                    uproperty_specifiers = macro_info.get("specifiers", [])

            return PropertyInfo(
                name=prop_name,
                type=prop_type or "unknown",
                visibility=visibility,
                is_static=is_static,
                is_uproperty=is_uproperty,
                uproperty_specifiers=uproperty_specifiers,
                line=line_num,
            )
        return None

    def _extract_comments(self, node: Any) -> list[str]:
        """Extract comments preceding a node."""
        comments = []
        prev = node.prev_sibling
        while prev and prev.type == "comment":
            comment_text = prev.text.decode().strip()
            comments.insert(0, comment_text)
            prev = prev.prev_sibling
        return comments

    # ========================================================================
    # Public API - Class Analysis
    # ========================================================================

    async def analyze_class(
        self, class_name: str, source_path: str = "", scope: ScopeType = None
    ) -> dict:
        """
        Analyze a C++ class structure.

        Args:
            class_name: Name of the class to analyze
            source_path: Optional specific directory to search
            scope: Search scope (project/engine/all). Default: project only.

        Returns:
            Dictionary containing class information
        """
        # Check cache first
        if class_name in self._class_cache:
            return self._class_cache[class_name].to_dict()

        # Get search paths based on scope
        search_paths = self._get_search_paths(scope, source_path)

        if not search_paths:
            raise ValueError(
                "No C++ source paths configured. Set CPP_SOURCE_PATH environment variable."
            )

        # Search for the class
        for base_path in search_paths:
            base = Path(base_path)
            if not base.exists():
                continue
            for pattern in ["**/*.h", "**/*.cpp"]:
                for file_path in base.rglob(pattern.replace("**/", "")):
                    try:
                        await self._parse_file(str(file_path))
                        if class_name in self._class_cache:
                            return self._class_cache[class_name].to_dict()
                    except Exception:
                        continue

        raise ValueError(f"Class not found: {class_name}")

    async def find_class_hierarchy(
        self, class_name: str, include_interfaces: bool = True, scope: ScopeType = None
    ) -> dict:
        """
        Get the inheritance hierarchy of a class.

        Args:
            class_name: Name of the class
            include_interfaces: Whether to include implemented interfaces
            scope: Search scope (project/engine/all). Default: project only.

        Returns:
            Nested hierarchy dictionary
        """
        try:
            class_info = await self.analyze_class(class_name, scope=scope)
        except ValueError:
            return ClassHierarchy(class_name=class_name).to_dict()

        hierarchy = ClassHierarchy(
            class_name=class_name,
            interfaces=class_info.get("interfaces", []) if include_interfaces else [],
        )

        # Recursively build superclass hierarchies
        for superclass in class_info.get("superclasses", []):
            try:
                super_hierarchy_dict = await self.find_class_hierarchy(
                    superclass, include_interfaces, scope=scope
                )
                super_hierarchy = ClassHierarchy(
                    class_name=super_hierarchy_dict["class"],
                    superclasses=[],
                    interfaces=super_hierarchy_dict.get("interfaces", []),
                )
                # Handle nested superclasses
                for s in super_hierarchy_dict.get("superclasses", []):
                    if isinstance(s, dict):
                        super_hierarchy.superclasses.append(
                            ClassHierarchy(
                                class_name=s.get("class", ""), interfaces=s.get("interfaces", [])
                            )
                        )
                hierarchy.superclasses.append(super_hierarchy)
            except Exception:
                hierarchy.superclasses.append(ClassHierarchy(class_name=superclass))

        return hierarchy.to_dict()

    # ========================================================================
    # Public API - Code Search
    # ========================================================================

    async def search_code(
        self,
        query: str,
        file_pattern: str = "*.{h,cpp}",
        include_comments: bool = True,
        scope: ScopeType = None,
        max_results: int = 500,
        *,
        query_mode: Literal["regex", "tokens", "smart"] = "regex",
    ) -> dict:
        """
        Search through C++ source code.

        Args:
            query: Search query (supports regex)
            file_pattern: File pattern to search (default: "*.{h,cpp}")
            include_comments: Whether to include comment lines
            scope: Search scope (project/engine/all). Default: project only.
            max_results: Maximum number of results to return (default: 500)

        Returns:
            Dictionary with matches and count
        """
        search_paths = self._get_search_paths(scope)

        if not search_paths:
            return {
                "matches": [],
                "count": 0,
                "scope": str(scope or "project"),
                "searched_paths": [],
                "query_mode": query_mode,
            }

        # Normalize scope early (for safety filtering later).
        cfg = get_config()
        norm_scope: SearchScope
        if scope is None:
            norm_scope = cfg.default_scope
        elif isinstance(scope, SearchScope):
            norm_scope = scope
        else:
            try:
                norm_scope = SearchScope(str(scope))
            except Exception:
                norm_scope = SearchScope.PROJECT

        results = []
        lowered_query = query.strip()

        def _looks_like_regex(q: str) -> bool:
            # Heuristic: treat as regex if it contains common regex meta chars.
            regex_meta = set(r"\.^$*+?{}[]|()")
            return any(ch in regex_meta for ch in q)

        # Resolve smart mode.
        if query_mode == "smart":
            if not lowered_query:
                query_mode_resolved: Literal["regex", "tokens"] = "tokens"
            elif _looks_like_regex(lowered_query):
                query_mode_resolved = "regex"
            elif any(ch.isspace() for ch in lowered_query):
                query_mode_resolved = "tokens"
            else:
                # Single token: treat as substring token search (more grep-like than regex).
                query_mode_resolved = "tokens"
        else:
            query_mode_resolved = "tokens" if query_mode == "tokens" else "regex"

        regex: re.Pattern[str] | None = None
        tokens: list[str] = []

        if query_mode_resolved == "regex":
            try:
                regex = re.compile(query, re.IGNORECASE)
            except re.error as e:
                return {
                    "matches": [],
                    "count": 0,
                    "error": f"Invalid regex: {e}",
                    "scope": str(scope or "project"),
                    "searched_paths": search_paths,
                    "query_mode": query_mode,
                }
        else:
            # Token mode: split by whitespace, drop empties.
            tokens = [t for t in re.split(r"\s+", lowered_query) if t]
            if not tokens:
                return {
                    "matches": [],
                    "count": 0,
                    "scope": str(scope or "project"),
                    "searched_paths": search_paths,
                    "query_mode": query_mode,
                }

        # Parse file patterns
        patterns = []
        if "{" in file_pattern:
            base, ext_part = file_pattern.split("{")
            extensions = ext_part.rstrip("}").split(",")
            patterns = [f"{base}{ext}" for ext in extensions]
        else:
            patterns = [file_pattern]

        for base_path in search_paths:
            base = Path(base_path)
            if not base.exists():
                continue
            for pattern in patterns:
                glob_pattern = pattern.replace("*", "")
                for file_path in base.rglob(f"*{glob_pattern}"):
                    if len(results) >= max_results:
                        break
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        lines = content.split("\n")

                        for i, line in enumerate(lines):
                            if len(results) >= max_results:
                                break
                            if not include_comments:
                                stripped = line.strip()
                                if stripped.startswith("//") or stripped.startswith("/*"):
                                    continue

                            if query_mode_resolved == "regex":
                                assert regex is not None
                                if not regex.search(line):
                                    continue
                                context = "\n".join(lines[max(0, i - 2) : i + 3])
                                results.append(
                                    {
                                        "file": str(file_path),
                                        "line": i + 1,
                                        "column": 1,
                                        "context": context,
                                        "score": 1,
                                    }
                                )
                            else:
                                lower_line = line.lower()
                                matched = [t for t in tokens if t.lower() in lower_line]
                                if not matched:
                                    continue
                                # Column: best effort - first matched token.
                                first = matched[0]
                                col = lower_line.find(first.lower())
                                context = "\n".join(lines[max(0, i - 2) : i + 3])
                                results.append(
                                    {
                                        "file": str(file_path),
                                        "line": i + 1,
                                        "column": (col + 1) if col >= 0 else 1,
                                        "context": context,
                                        "matched_terms": matched,
                                        "score": len(matched),
                                    }
                                )
                    except Exception:
                        continue

        # In token mode, prefer higher-score matches first.
        if query_mode_resolved == "tokens":
            results.sort(key=lambda m: int(m.get("score", 0)), reverse=True)

        # --------------------------------------------------------------------
        # SAFETY: Enforce scope filtering on returned matches.
        #
        # Even if configuration is wrong (e.g. engine path accidentally included in
        # project paths), this ensures `scope='project'` never returns engine files
        # outside the configured project roots (and vice versa).
        # --------------------------------------------------------------------
        def _is_under_any_root(file_path: str, roots: list[str]) -> bool:
            try:
                p = Path(file_path).resolve()
            except Exception:
                return False
            for r in roots:
                try:
                    root = Path(r).resolve()
                except Exception:
                    continue
                # `is_relative_to` is 3.9+, and we are on 3.12 in uv typically.
                try:
                    if p.is_relative_to(root):
                        return True
                except Exception:
                    # Fallback for platforms where is_relative_to might fail
                    if str(p).lower().startswith(str(root).lower().rstrip("\\/") + "\\"):
                        return True
            return False

        if norm_scope == SearchScope.PROJECT:
            proj_roots = cfg.get_project_paths()
            results = [m for m in results if _is_under_any_root(str(m.get("file", "")), proj_roots)]
        elif norm_scope == SearchScope.ENGINE:
            eng_roots = cfg.get_engine_paths()
            results = [m for m in results if _is_under_any_root(str(m.get("file", "")), eng_roots)]
        elif norm_scope == SearchScope.PLUGIN:
            plugin_roots = cfg.get_plugin_paths()
            results = [m for m in results if _is_under_any_root(str(m.get("file", "")), plugin_roots)]
        # SearchScope.ALL: keep as-is.

        return {
            "matches": results,
            "count": len(results),
            "scope": str(scope or "project"),
            "searched_paths": search_paths,
            "truncated": len(results) >= max_results,
            "query_mode": query_mode,
            "query_mode_resolved": query_mode_resolved,
        }

    async def find_references(
        self,
        identifier: str,
        ref_type: Literal["class", "function", "variable"] | None = None,
        scope: ScopeType = None,
    ) -> dict:
        """
        Find all references to an identifier.

        Args:
            identifier: Name of the class, function, or variable
            ref_type: Optional type filter
            scope: Search scope (project/engine/all). Default: project only.

        Returns:
            Dictionary with references and count
        """
        return await self.search_code(rf"\b{re.escape(identifier)}\b", scope=scope)

    # ========================================================================
    # Public API - Pattern Detection
    # ========================================================================

    async def detect_patterns(self, file_path: str) -> dict:
        """
        Detect Unreal Engine patterns in a file.

        Args:
            file_path: Path to the C++ file

        Returns:
            Dictionary with detected patterns
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8", errors="ignore")
        patterns = detect_ue_pattern(content, file_path)

        return {"patterns": patterns, "file": file_path}

    async def analyze_file(
        self,
        file_path: str,
        *,
        max_preview_chars: int = 50000,  # 增加到 50KB，足够大多数文件
        start_line: int | None = None,  # 可选：从指定行开始
        end_line: int | None = None,    # 可选：到指定行结束
    ) -> dict:
        """
        Analyze a single C++ file path (header/source).

        This is a lightweight file-oriented API used by unified.get_details when the user provides
        a file path (e.g., D:\\...\\LyraHealthComponent.h).

        Args:
            file_path: Path to the C++ file
            max_preview_chars: Maximum characters to include in preview (default: 50000)
            start_line: Optional starting line number (1-based)
            end_line: Optional ending line number (1-based, inclusive)

        Returns:
            - file: absolute file path
            - exists: bool
            - size_bytes: int | None
            - preview: str (truncated or line-filtered)
            - is_truncated: bool
            - total_chars: int
            - preview_chars: int
            - includes: list[str]
            - classes: list[dict] (name, line)
            - functions: list[dict] (name, line)
            - ue_patterns: list[dict] (UPROPERTY/UFUNCTION/UCLASS...)
        """
        path = Path(file_path)
        if not path.exists():
            return {"file": str(path), "exists": False, "error": "file_not_found"}

        try:
            size_bytes = path.stat().st_size
        except Exception:
            size_bytes = None

        content = path.read_text(encoding="utf-8", errors="ignore")
        
        # Apply line filtering if requested
        if start_line is not None or end_line is not None:
            lines = content.splitlines(keepends=True)
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            content = "".join(lines[start_idx:end_idx])

        # Parse AST (cached)
        tree = await self._parse_file(str(path))

        includes: list[str] = []
        classes: list[dict] = []
        functions: list[dict] = []

        # Includes
        include_q = self._query_cache.get("INCLUDE")
        if include_q is not None:
            cursor = QueryCursor(include_q)
            for _, captured in cursor.matches(tree.root_node):
                nodes = captured.get("include_path") or []
                if not nodes:
                    continue
                includes.append(nodes[0].text.decode(errors="ignore").strip())

        # Classes (name + line)
        class_q = self._query_cache.get("CLASS")
        if class_q is not None:
            cursor = QueryCursor(class_q)
            for _, captured in cursor.matches(tree.root_node):
                name_nodes = captured.get("class_name") or []
                class_nodes = captured.get("class") or []
                body_nodes = captured.get("class_body") or []
                if not name_nodes or not class_nodes or not body_nodes:
                    continue
                classes.append(
                    {
                        "name": name_nodes[0].text.decode(errors="ignore"),
                        "line": class_nodes[0].start_point[0] + 1,
                    }
                )

        # Functions (definition only)
        func_q = self._query_cache.get("FUNCTION")
        if func_q is not None:
            cursor = QueryCursor(func_q)
            for _, captured in cursor.matches(tree.root_node):
                name_nodes = captured.get("func_name") or []
                func_nodes = captured.get("function") or []
                if not name_nodes or not func_nodes:
                    continue
                functions.append(
                    {
                        "name": name_nodes[0].text.decode(errors="ignore"),
                        "line": func_nodes[0].start_point[0] + 1,
                    }
                )

        # UE patterns (regex-based)
        ue_patterns = detect_ue_pattern(content, str(path))

        preview = content[: max(0, int(max_preview_chars))]
        is_truncated = len(content) > max_preview_chars
        if is_truncated:
            remaining_bytes = len(content) - max_preview_chars
            preview += f"\n... (truncated, {remaining_bytes} more bytes)"

        return {
            "file": str(path.resolve()),
            "exists": True,
            "size_bytes": size_bytes,
            "preview": preview,
            "is_truncated": is_truncated,
            "total_chars": len(content),
            "preview_chars": len(preview),
            "includes": includes,
            "classes": classes,
            "functions": functions,
            "ue_patterns": ue_patterns,
        }

    async def get_blueprint_exposure(self, file_path: str) -> dict:
        """
        Get all Blueprint-exposed API from a file.

        Args:
            file_path: Path to the C++ header file

        Returns:
            Dictionary containing Blueprint-exposed items
        """
        patterns_result = await self.detect_patterns(file_path)
        patterns = patterns_result.get("patterns", [])

        exposure = {
            "file": file_path,
            "blueprint_callable_functions": [],
            "blueprint_pure_functions": [],
            "blueprint_events": [],
            "blueprint_readable_properties": [],
            "blueprint_writable_properties": [],
            "blueprintable_classes": [],
        }

        for pattern in patterns:
            specifiers = pattern.get("specifiers", [])
            name = pattern.get("name", "")
            pattern_type = pattern.get("pattern_type", "")

            if pattern_type == "UFUNCTION":
                if "BlueprintCallable" in specifiers:
                    exposure["blueprint_callable_functions"].append(name)
                if "BlueprintPure" in specifiers:
                    exposure["blueprint_pure_functions"].append(name)
                if (
                    "BlueprintImplementableEvent" in specifiers
                    or "BlueprintNativeEvent" in specifiers
                ):
                    exposure["blueprint_events"].append(name)

            elif pattern_type == "UPROPERTY":
                if "BlueprintReadOnly" in specifiers or "BlueprintReadWrite" in specifiers:
                    exposure["blueprint_readable_properties"].append(name)
                if "BlueprintReadWrite" in specifiers:
                    exposure["blueprint_writable_properties"].append(name)

            elif pattern_type == "UCLASS":
                if "Blueprintable" in specifiers:
                    exposure["blueprintable_classes"].append(name)

        return exposure


# ============================================================================
# Global Instance
# ============================================================================

_analyzer: CppAnalyzer | None = None


def get_analyzer() -> CppAnalyzer:
    """Get the global analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = CppAnalyzer()
    return _analyzer


def set_analyzer(analyzer: CppAnalyzer) -> None:
    """Set the global analyzer instance (useful for testing)."""
    global _analyzer
    _analyzer = analyzer
