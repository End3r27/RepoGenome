"""
RepoSpider subsystem - Structural graph analysis.

Extracts files, symbols, dependencies, and builds the structural graph
of the repository.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from repogenome.analyzers.call_graph import CallGraphBuilder
from repogenome.analyzers.dependency_resolver import DependencyResolver
from repogenome.analyzers.python.ast_analyzer import analyze_python_file
from repogenome.analyzers.typescript.ts_analyzer import analyze_typescript_file
from repogenome.analyzers.java.java_analyzer import analyze_java_file
from repogenome.analyzers.go.go_analyzer import analyze_go_file
from repogenome.analyzers.cpp.cpp_analyzer import analyze_cpp_file
from repogenome.analyzers.rust.rust_analyzer import analyze_rust_file
from repogenome.analyzers.csharp.csharp_analyzer import analyze_csharp_file
from repogenome.analyzers.ruby.ruby_analyzer import analyze_ruby_file
from repogenome.analyzers.php.php_analyzer import analyze_php_file
from repogenome.analyzers.markdown.md_analyzer import analyze_markdown_file
from repogenome.analyzers.json.json_analyzer import analyze_json_file
from repogenome.analyzers.yaml.yaml_analyzer import analyze_yaml_file
from repogenome.analyzers.html.html_analyzer import analyze_html_file
from repogenome.analyzers.css.css_analyzer import analyze_css_file
from repogenome.analyzers.shell.shell_analyzer import analyze_shell_file
from repogenome.analyzers.sql.sql_analyzer import analyze_sql_file
from repogenome.core.schema import Edge, EdgeType, Node, NodeType
from repogenome.subsystems.base import Subsystem


class RepoSpider(Subsystem):
    """Extract structural graph (files, symbols, dependencies)."""

    def __init__(self):
        """Initialize RepoSpider."""
        super().__init__("repospider")
        self.required_analyzers = ["python", "typescript"]
        self.dependency_resolver = DependencyResolver()

    def analyze(
        self, repo_path: Path, existing_genome: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze repository structure.

        Args:
            repo_path: Path to repository root
            existing_genome: Optional existing genome

        Returns:
            Dictionary with nodes and edges
        """
        nodes: Dict[str, Node] = {}
        edges: List[Edge] = []
        entry_points: List[str] = []

        # Code file extensions (for detailed analysis)
        python_extensions = {".py"}
        typescript_extensions = {".ts", ".tsx", ".js", ".jsx"}
        java_extensions = {".java"}
        go_extensions = {".go"}
        cpp_extensions = {".cpp", ".cc", ".cxx", ".hpp", ".h", ".hxx"}
        rust_extensions = {".rs"}
        csharp_extensions = {".cs"}
        ruby_extensions = {".rb"}
        php_extensions = {".php", ".phtml"}

        # Ignored directories
        ignored_parts = [
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            ".eggs",
            "*.egg-info",
        ]

        # Find all files in the repository
        all_files = []
        for f in repo_path.rglob("*"):
            if f.is_file():
                # Check if file is in ignored directory
                if any(part in str(f) for part in ignored_parts):
                    continue
                all_files.append(f)

        # Analyze each file
        for file_path in all_files:
            rel_path = str(file_path.relative_to(repo_path))
            language = self._detect_language(file_path)

            # Skip binary files and very large files
            if not self._is_text_file(file_path):
                # Create basic file node for binary files
                file_node_id = rel_path
                nodes[file_node_id] = Node(
                    type=NodeType.FILE,
                    file=rel_path,
                    language=language or "Binary",
                    visibility="public",
                )
                continue

            # Add file node
            file_node_id = rel_path
            nodes[file_node_id] = Node(
                type=NodeType.FILE,
                file=rel_path,
                language=language,
                visibility="public",
            )

            # Analyze file contents based on type
            try:
                if file_path.suffix in python_extensions:
                    file_data = analyze_python_file(file_path)
                    entry_points.extend(
                        [ep for ep in file_data.get("entry_points", [])]
                    )

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility=self._detect_visibility(func["name"]),
                            summary=self._extract_docstring(func),
                        )

                        # Add defines edge from file to function
                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add class nodes
                    for cls in file_data.get("classes", []):
                        cls_node_id = self._make_node_id(rel_path, cls["name"])
                        nodes[cls_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility=self._detect_visibility(cls["name"]),
                        )

                        # Add defines edge
                        edges.append(
                            Edge(from_=file_node_id, to=cls_node_id, type=EdgeType.DEFINES)
                        )

                    # Add import edges
                    for imp in file_data.get("imports", []):
                        target_module = imp.get("module", "")
                        if target_module:
                            # Try to resolve import to a file using enhanced resolver
                            target_file = self.dependency_resolver.resolve_python_import(
                                repo_path, rel_path, target_module
                            )
                            if target_file:
                                edges.append(
                                    Edge(
                                        from_=file_node_id,
                                        to=target_file,
                                        type=EdgeType.IMPORTS,
                                    )
                                )

                    # Build call graph for this file
                    call_graph_builder = CallGraphBuilder()
                    file_functions = file_data.get("functions", [])
                    file_call_graph = call_graph_builder.analyze_file(
                        file_path, file_functions, repo_path
                    )

                    # Add call edges (file_call_graph maps function names to called function names)
                    for caller_name, callee_names in file_call_graph.items():
                        caller_id = self._make_node_id(rel_path, caller_name)
                        if caller_id in nodes:
                            for callee_name in callee_names:
                                callee_id = self._make_node_id(rel_path, callee_name)
                                if callee_id in nodes:
                                    edges.append(
                                        Edge(from_=caller_id, to=callee_id, type=EdgeType.CALLS)
                                    )

                elif file_path.suffix in typescript_extensions:
                    file_data = analyze_typescript_file(file_path)

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility="public" if func.get("is_export") else "private",
                        )

                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add class nodes
                    for cls in file_data.get("classes", []):
                        cls_node_id = self._make_node_id(rel_path, cls["name"])
                        nodes[cls_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility="public" if cls.get("is_export") else "private",
                        )

                        edges.append(
                            Edge(from_=file_node_id, to=cls_node_id, type=EdgeType.DEFINES)
                        )

                    # Add import edges
                    for imp in file_data.get("imports", []):
                        target_module = imp.get("module", "")
                        if target_module:
                            target_file = self.dependency_resolver.resolve_typescript_import(
                                repo_path, rel_path, target_module
                            )
                            if target_file:
                                edges.append(
                                    Edge(
                                        from_=file_node_id,
                                        to=target_file,
                                        type=EdgeType.IMPORTS,
                                    )
                                )

                elif file_path.suffix in java_extensions:
                    file_data = analyze_java_file(file_path)
                    entry_points.extend(file_data.get("entry_points", []))

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility=func.get("visibility", "public"),
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add class nodes
                    for cls in file_data.get("classes", []):
                        cls_node_id = self._make_node_id(rel_path, cls["name"])
                        nodes[cls_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility=cls.get("visibility", "public"),
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=cls_node_id, type=EdgeType.DEFINES)
                        )

                elif file_path.suffix in go_extensions:
                    file_data = analyze_go_file(file_path)
                    entry_points.extend(file_data.get("entry_points", []))

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility="public",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add type nodes (structs, interfaces)
                    for typ in file_data.get("classes", []):
                        type_node_id = self._make_node_id(rel_path, typ["name"])
                        nodes[type_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility="public",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=type_node_id, type=EdgeType.DEFINES)
                        )

                elif file_path.suffix in cpp_extensions:
                    file_data = analyze_cpp_file(file_path)
                    entry_points.extend(file_data.get("entry_points", []))

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility="public",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add class nodes
                    for cls in file_data.get("classes", []):
                        cls_node_id = self._make_node_id(rel_path, cls["name"])
                        nodes[cls_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility="public",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=cls_node_id, type=EdgeType.DEFINES)
                        )

                elif file_path.suffix in rust_extensions:
                    file_data = analyze_rust_file(file_path)
                    entry_points.extend(file_data.get("entry_points", []))

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility="public" if func.get("is_pub") else "private",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add type nodes (structs, enums, traits)
                    for typ in file_data.get("classes", []):
                        type_node_id = self._make_node_id(rel_path, typ["name"])
                        nodes[type_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility="public",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=type_node_id, type=EdgeType.DEFINES)
                        )

                elif file_path.suffix in csharp_extensions:
                    file_data = analyze_csharp_file(file_path)
                    entry_points.extend(file_data.get("entry_points", []))

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility=func.get("visibility", "public"),
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add class nodes
                    for cls in file_data.get("classes", []):
                        cls_node_id = self._make_node_id(rel_path, cls["name"])
                        nodes[cls_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility=cls.get("visibility", "public"),
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=cls_node_id, type=EdgeType.DEFINES)
                        )

                elif file_path.suffix in ruby_extensions:
                    file_data = analyze_ruby_file(file_path)

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility="public",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add class nodes
                    for cls in file_data.get("classes", []):
                        cls_node_id = self._make_node_id(rel_path, cls["name"])
                        nodes[cls_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility="public",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=cls_node_id, type=EdgeType.DEFINES)
                        )

                elif file_path.suffix in php_extensions:
                    file_data = analyze_php_file(file_path)

                    # Add function nodes
                    for func in file_data.get("functions", []):
                        func_node_id = self._make_node_id(rel_path, func["name"])
                        nodes[func_node_id] = Node(
                            type=NodeType.FUNCTION,
                            file=rel_path,
                            language=language,
                            visibility=func.get("visibility", "public"),
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                        )

                    # Add class nodes
                    for cls in file_data.get("classes", []):
                        cls_node_id = self._make_node_id(rel_path, cls["name"])
                        nodes[cls_node_id] = Node(
                            type=NodeType.CLASS,
                            file=rel_path,
                            language=language,
                            visibility="public",
                        )
                        edges.append(
                            Edge(from_=file_node_id, to=cls_node_id, type=EdgeType.DEFINES)
                        )

                else:
                    # Analyze other file types with their specific analyzers
                    if file_path.suffix in {".md", ".markdown"}:
                        file_data = analyze_markdown_file(file_path)
                        # Create nodes for headings
                        for heading in file_data.get("headings", []):
                            heading_id = f"{file_node_id}#{heading['level']}-{heading['text'][:50]}"
                            nodes[heading_id] = Node(
                                type=NodeType.CONCEPT,
                                file=rel_path,
                                language=language,
                                summary=heading["text"][:200],
                            )
                            edges.append(
                                Edge(from_=file_node_id, to=heading_id, type=EdgeType.DEFINES)
                            )
                        # Create edges for internal links
                        for link in file_data.get("links", []):
                            if link.get("is_internal"):
                                # Link to another file node (if exists)
                                target_path = link["url"]
                                if target_path in nodes:
                                    edges.append(
                                        Edge(from_=file_node_id, to=target_path, type=EdgeType.REFERENCES)
                                    )

                    elif file_path.suffix == ".json":
                        file_data = analyze_json_file(file_path)
                        # Create nodes for top-level keys in objects
                        if file_data.get("type") == "object":
                            for key in file_data.get("keys", []):
                                key_id = f"{file_node_id}.{key}"
                                nodes[key_id] = Node(
                                    type=NodeType.CONCEPT,
                                    file=rel_path,
                                    language=language,
                                )
                                edges.append(
                                    Edge(from_=file_node_id, to=key_id, type=EdgeType.DEFINES)
                                )

                    elif file_path.suffix in {".yaml", ".yml"}:
                        file_data = analyze_yaml_file(file_path)
                        # Create nodes for top-level keys
                        if file_data.get("type") == "object":
                            for key in file_data.get("keys", []):
                                key_id = f"{file_node_id}.{key}"
                                nodes[key_id] = Node(
                                    type=NodeType.CONCEPT,
                                    file=rel_path,
                                    language=language,
                                )
                                edges.append(
                                    Edge(from_=file_node_id, to=key_id, type=EdgeType.DEFINES)
                                )

                    elif file_path.suffix in {".html", ".htm"}:
                        file_data = analyze_html_file(file_path)
                        # Create edges for links
                        for link in file_data.get("links", []):
                            if link.get("is_internal"):
                                target_path = link["url"]
                                if target_path in nodes:
                                    edges.append(
                                        Edge(from_=file_node_id, to=target_path, type=EdgeType.REFERENCES)
                                    )
                        # Create edges for stylesheets
                        for stylesheet in file_data.get("stylesheets", []):
                            href = stylesheet.get("href", "")
                            if href in nodes:
                                edges.append(
                                    Edge(from_=file_node_id, to=href, type=EdgeType.REFERENCES)
                                )

                    elif file_path.suffix in {".css", ".scss", ".sass", ".less"}:
                        file_data = analyze_css_file(file_path)
                        # Create nodes for key selectors
                        for selector_info in file_data.get("selectors", [])[:50]:  # Limit to first 50
                            selector = selector_info.get("selector", "")
                            if selector and len(selector) < 100:  # Skip very long selectors
                                selector_id = f"{file_node_id}.{selector[:50]}"
                                nodes[selector_id] = Node(
                                    type=NodeType.CONCEPT,
                                    file=rel_path,
                                    language=language,
                                )
                                edges.append(
                                    Edge(from_=file_node_id, to=selector_id, type=EdgeType.DEFINES)
                                )

                    elif file_path.suffix in {".sh", ".bash", ".zsh", ".ps1"}:
                        file_data = analyze_shell_file(file_path)
                        # Create nodes for functions (similar to Python/TypeScript)
                        for func in file_data.get("functions", []):
                            func_name = func.get("name", "")
                            func_node_id = self._make_node_id(rel_path, func_name)
                            nodes[func_node_id] = Node(
                                type=NodeType.FUNCTION,
                                file=rel_path,
                                language=language,
                                visibility="public",
                            )
                            edges.append(
                                Edge(from_=file_node_id, to=func_node_id, type=EdgeType.DEFINES)
                            )

                    elif file_path.suffix == ".sql":
                        file_data = analyze_sql_file(file_path)
                        # Create nodes for tables
                        for table in file_data.get("tables", []):
                            table_id = f"{file_node_id}.{table}"
                            nodes[table_id] = Node(
                                type=NodeType.CONCEPT,
                                file=rel_path,
                                language=language,
                            )
                            edges.append(
                                Edge(from_=file_node_id, to=table_id, type=EdgeType.DEFINES)
                            )
                        # Create nodes for views
                        for view in file_data.get("views", []):
                            view_name = view.get("name", "")
                            view_id = f"{file_node_id}.{view_name}"
                            nodes[view_id] = Node(
                                type=NodeType.CONCEPT,
                                file=rel_path,
                                language=language,
                            )
                            edges.append(
                                Edge(from_=file_node_id, to=view_id, type=EdgeType.DEFINES)
                            )
            except Exception as e:
                # Continue on error - log but don't fail
                from repogenome.core.errors import handle_analysis_error
                error_info = handle_analysis_error(e, str(file_path))
                # Could log errors here if needed
                continue

        # Calculate fan-in/fan-out for criticality
        fan_in: Dict[str, int] = {}
        fan_out: Dict[str, int] = {}
        for edge in edges:
            fan_out[edge.from_] = fan_out.get(edge.from_, 0) + 1
            fan_in[edge.to] = fan_in.get(edge.to, 0) + 1

        # Update node criticality based on fan-in
        for node_id, node in nodes.items():
            node_fan_in = fan_in.get(node_id, 0)
            if node_fan_in > 0:
                # Normalize to 0-1 range (log scale)
                import math

                node.criticality = min(1.0, math.log(node_fan_in + 1) / math.log(11))

        return {
            "nodes": {k: v.model_dump() for k, v in nodes.items()},
            "edges": [e.model_dump(by_alias=True) for e in edges],
            "entry_points": entry_points,
        }

    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language or file type from file extension."""
        ext = file_path.suffix.lower()
        
        # Programming languages
        language_map = {
            ".py": "Python",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
            ".sh": "Shell",
            ".bash": "Bash",
            ".zsh": "Zsh",
            ".ps1": "PowerShell",
            ".sql": "SQL",
            ".r": "R",
            ".m": "MATLAB",
            ".jl": "Julia",
            ".clj": "Clojure",
            ".hs": "Haskell",
            ".ml": "OCaml",
            ".ex": "Elixir",
            ".exs": "Elixir",
            # Documentation
            ".md": "Markdown",
            ".markdown": "Markdown",
            ".rst": "reStructuredText",
            ".txt": "Text",
            # Configuration
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".xml": "XML",
            ".ini": "INI",
            ".cfg": "Config",
            ".conf": "Config",
            # Web
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".sass": "SASS",
            ".less": "LESS",
        }
        
        return language_map.get(ext)

    def _is_text_file(self, file_path: Path, max_size: int = 10 * 1024 * 1024) -> bool:
        """
        Check if a file is a text file.
        
        Args:
            file_path: Path to file
            max_size: Maximum file size to check (default: 10MB)
            
        Returns:
            True if file appears to be text-based
        """
        try:
            # Check file size
            if file_path.stat().st_size > max_size:
                return False
            
            # Check if file has known binary extensions
            binary_extensions = {
                ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
                ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
                ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".obj",
                ".pyc", ".pyo", ".class", ".jar", ".war", ".ear",
                ".woff", ".woff2", ".ttf", ".eot", ".otf",
                ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv",
                ".db", ".sqlite", ".sqlite3",
            }
            if file_path.suffix.lower() in binary_extensions:
                return False
            
            # Try to read as text
            try:
                with open(file_path, "rb") as f:
                    chunk = f.read(8192)  # Read first 8KB
                    # Check for null bytes (indicating binary)
                    if b"\x00" in chunk:
                        return False
                    # Try to decode as UTF-8
                    chunk.decode("utf-8", errors="strict")
                return True
            except (UnicodeDecodeError, UnicodeError):
                # Try other encodings
                try:
                    with open(file_path, "r", encoding="latin-1", errors="strict") as f:
                        f.read(8192)
                    return True
                except Exception:
                    return False
        except Exception:
            return False

    def _make_node_id(self, file_path: str, name: str) -> str:
        """Create a unique node ID."""
        # Remove extension for cleaner IDs
        file_base = file_path.replace(".py", "").replace(".ts", "").replace(
            ".js", ""
        )
        return f"{file_base}.{name}"

    def _detect_visibility(self, name: str) -> str:
        """
        Detect visibility from naming convention.

        Args:
            name: Symbol name

        Returns:
            'public' or 'private'
        """
        if name.startswith("_"):
            return "private"
        return "public"

    def _extract_docstring(self, func: Dict[str, Any]) -> Optional[str]:
        """Extract docstring summary (placeholder - would need AST access)."""
        # This would extract from AST in full implementation
        return None

    def _resolve_import(
        self, repo_path: Path, from_file: str, import_module: str
    ) -> Optional[str]:
        """
        Resolve import to a file path.

        Args:
            repo_path: Repository root
            from_file: File containing the import
            import_module: Module being imported

        Returns:
            Relative file path or None
        """
        from_file_path = repo_path / from_file
        from_dir = from_file_path.parent

        # Try different resolution strategies
        # 1. Relative import
        if import_module.startswith("."):
            parts = import_module.split(".")
            depth = len([p for p in parts if p == ""])
            module_parts = [p for p in parts if p]
            target_dir = from_dir
            for _ in range(depth - 1):
                target_dir = target_dir.parent

            # Try different extensions
            for ext in [".py", ".ts", ".tsx", ".js"]:
                test_path = target_dir / f"{'/'.join(module_parts)}{ext}"
                if test_path.exists() and test_path.is_file():
                    return str(test_path.relative_to(repo_path))

                # Try __init__.py style
                test_path = target_dir / "/".join(module_parts) / f"__init__{ext}"
                if test_path.exists():
                    return str(test_path.relative_to(repo_path))

        # 2. Absolute import (from repo root)
        else:
            # Try different extensions
            for ext in [".py", ".ts", ".tsx", ".js"]:
                parts = import_module.split(".")
                # Try as file
                test_path = repo_path / f"{'/'.join(parts)}{ext}"
                if test_path.exists() and test_path.is_file():
                    return str(test_path.relative_to(repo_path))

                # Try as package
                test_path = repo_path / "/".join(parts) / f"__init__{ext}"
                if test_path.exists():
                    return str(test_path.relative_to(repo_path))

        return None

