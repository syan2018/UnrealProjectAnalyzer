"""
C++ Analyzer - Core analysis logic using tree-sitter.

Migrated from unreal-analyzer-mcp (TypeScript).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser, Query

from ..config import get_config
from .queries import QUERY_PATTERNS
from .patterns import UE_PATTERNS, detect_ue_pattern


@dataclass
class ClassInfo:
    """Information about a C++ class."""
    name: str
    file: str
    line: int
    superclasses: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    methods: list[dict] = field(default_factory=list)
    properties: list[dict] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)


@dataclass
class CodeReference:
    """A reference to code location."""
    file: str
    line: int
    column: int
    context: str


class CppAnalyzer:
    """C++ source code analyzer using tree-sitter."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self._language = Language(tscpp.language())
        self._parser = Parser(self._language)
        
        # Caches
        self._class_cache: dict[str, ClassInfo] = {}
        self._ast_cache: dict[str, Any] = {}
        self._query_cache: dict[str, Query] = {}
        
        # Cache management
        self._max_cache_size = 1000
        self._cache_queue: list[str] = []
        
        # Pre-compile common queries
        self._init_queries()
    
    def _init_queries(self) -> None:
        """Initialize commonly used queries."""
        for name, pattern in QUERY_PATTERNS.items():
            try:
                query = self._language.query(pattern)
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
    
    def _parse_file(self, file_path: str) -> Any:
        """Parse a C++ file and return the AST."""
        if file_path in self._ast_cache:
            return self._ast_cache[file_path]
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding="utf-8", errors="ignore")
        tree = self._parser.parse(bytes(content, "utf-8"))
        
        self._manage_cache(self._ast_cache, file_path, tree)
        return tree
    
    async def analyze_class(self, class_name: str, source_path: str = "") -> dict:
        """Analyze a C++ class.
        
        Args:
            class_name: Name of the class to analyze
            source_path: Optional specific directory to search
        
        Returns:
            ClassInfo as dictionary
        """
        # Check cache first
        if class_name in self._class_cache:
            return self._class_cache[class_name].__dict__
        
        # Determine search paths
        config = get_config()
        search_paths = [source_path] if source_path else config.cpp_source_paths
        
        if not search_paths:
            raise ValueError("No C++ source paths configured. Use set_cpp_source_path first.")
        
        # Search for the class
        for base_path in search_paths:
            for header_file in Path(base_path).rglob("*.h"):
                try:
                    tree = self._parse_file(str(header_file))
                    class_info = self._extract_class(tree, str(header_file), class_name)
                    if class_info:
                        self._class_cache[class_name] = class_info
                        return class_info.__dict__
                except Exception:
                    continue
        
        raise ValueError(f"Class not found: {class_name}")
    
    def _extract_class(self, tree: Any, file_path: str, target_class: str) -> ClassInfo | None:
        """Extract class information from AST."""
        query = self._query_cache.get("CLASS")
        if not query:
            return None
        
        captures = query.captures(tree.root_node)
        
        for node, capture_name in captures:
            if capture_name == "class_name" and node.text.decode() == target_class:
                # Found the class, extract info
                class_node = node.parent
                return ClassInfo(
                    name=target_class,
                    file=file_path,
                    line=node.start_point[0] + 1,
                    superclasses=self._extract_superclasses(class_node),
                    methods=self._extract_methods(class_node),
                    properties=self._extract_properties(class_node),
                )
        
        return None
    
    def _extract_superclasses(self, class_node: Any) -> list[str]:
        """Extract superclass names from a class node."""
        superclasses = []
        for child in class_node.children:
            if child.type == "base_class_clause":
                for base in child.children:
                    if base.type == "type_identifier":
                        superclasses.append(base.text.decode())
        return superclasses
    
    def _extract_methods(self, class_node: Any) -> list[dict]:
        """Extract method information from a class node."""
        methods = []
        # TODO: Implement method extraction
        return methods
    
    def _extract_properties(self, class_node: Any) -> list[dict]:
        """Extract property information from a class node."""
        properties = []
        # TODO: Implement property extraction
        return properties
    
    async def find_class_hierarchy(self, class_name: str) -> dict:
        """Find the inheritance hierarchy of a class."""
        class_info = await self.analyze_class(class_name)
        
        hierarchy = {
            "class": class_name,
            "superclasses": [],
            "interfaces": class_info.get("interfaces", []),
        }
        
        for superclass in class_info.get("superclasses", []):
            try:
                super_hierarchy = await self.find_class_hierarchy(superclass)
                hierarchy["superclasses"].append(super_hierarchy)
            except ValueError:
                # Superclass not found in source, just add the name
                hierarchy["superclasses"].append({"class": superclass, "superclasses": []})
        
        return hierarchy
    
    async def search_code(self, query: str, file_pattern: str = "*.h") -> dict:
        """Search for code matching a pattern."""
        import re
        
        config = get_config()
        results = []
        regex = re.compile(query, re.IGNORECASE)
        
        for base_path in config.cpp_source_paths:
            for file_path in Path(base_path).rglob(file_pattern):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")
                    
                    for i, line in enumerate(lines):
                        if regex.search(line):
                            context = "\n".join(lines[max(0, i-2):i+3])
                            results.append({
                                "file": str(file_path),
                                "line": i + 1,
                                "column": 1,
                                "context": context,
                            })
                except Exception:
                    continue
        
        return {"matches": results, "count": len(results)}
    
    async def find_references(self, identifier: str, ref_type: str = "") -> dict:
        """Find all references to an identifier."""
        # Use code search for now
        return await self.search_code(rf"\b{identifier}\b")
    
    async def detect_patterns(self, file_path: str) -> dict:
        """Detect Unreal Engine patterns in a file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding="utf-8", errors="ignore")
        patterns = detect_ue_pattern(content, file_path)
        
        return {"patterns": patterns, "file": file_path}
    
    async def get_blueprint_exposure(self, file_path: str) -> dict:
        """Get all Blueprint-exposed API from a file."""
        patterns = await self.detect_patterns(file_path)
        
        # Organize by exposure type
        exposure = {
            "file": file_path,
            "classes": [],
        }
        
        # TODO: Parse UPROPERTY/UFUNCTION and organize by class
        
        return exposure


# Global analyzer instance
_analyzer: CppAnalyzer | None = None


def get_analyzer() -> CppAnalyzer:
    """Get the global analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = CppAnalyzer()
    return _analyzer


def set_analyzer(analyzer: CppAnalyzer) -> None:
    """Set the global analyzer instance."""
    global _analyzer
    _analyzer = analyzer
