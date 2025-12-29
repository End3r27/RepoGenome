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

        # Supported file extensions
        python_extensions = {".py"}
        typescript_extensions = {".ts", ".tsx", ".js", ".jsx"}

        # Find all code files
        code_files = []
        for ext in python_extensions | typescript_extensions:
            code_files.extend(
                [
                    f
                    for f in repo_path.rglob(f"*{ext}")
                    if not any(
                        part in str(f)
                        for part in [
                            ".git",
                            "__pycache__",
                            "node_modules",
                            ".venv",
                            "venv",
                            "dist",
                            "build",
                        ]
                    )
                ]
            )

        # Analyze each file
        for file_path in code_files:
            rel_path = str(file_path.relative_to(repo_path))
            language = self._detect_language(file_path)

            # Add file node
            file_node_id = rel_path
            nodes[file_node_id] = Node(
                type=NodeType.FILE,
                file=rel_path,
                language=language,
                visibility="public",
            )

            # Analyze file contents
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

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext = file_path.suffix.lower()
        if ext == ".py":
            return "Python"
        elif ext in [".ts", ".tsx"]:
            return "TypeScript"
        elif ext in [".js", ".jsx"]:
            return "JavaScript"
        return "Unknown"

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

