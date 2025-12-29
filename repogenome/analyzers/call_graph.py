"""Call graph analysis for building accurate function call relationships."""

import ast
from pathlib import Path
from typing import Any, Dict, List, Set


class CallGraphBuilder:
    """Build call graphs by analyzing function bodies."""

    def analyze_file(self, file_path: Path, functions: List[Dict[str, Any]], repo_path: Path) -> Dict[str, List[str]]:
        """
        Analyze a file to build call graph.

        Args:
            file_path: Path to Python file
            functions: List of function definitions from AST analysis
            repo_path: Repository root path

        Returns:
            Dictionary mapping function names to list of called function names
        """
        call_graph: Dict[str, List[str]] = {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            # Build function name to function info mapping
            func_map = {func["name"]: func for func in functions}

            # Visit AST to find calls
            visitor = _CallVisitor(func_map)
            visitor.visit(tree)

            # Note: file_str should be passed in or calculated relative to repo root
            # For now, we'll return calls with function names and let caller construct IDs
            for func_name, calls in visitor.call_graph.items():
                if calls:
                    call_graph[func_name] = calls

        except Exception:
            pass

        return call_graph


class _CallVisitor(ast.NodeVisitor):
    """AST visitor for finding function calls."""

    def __init__(self, func_map: Dict[str, Any]):
        """Initialize visitor."""
        self.func_map = func_map
        self.call_graph: Dict[str, List[str]] = {}
        self.current_function: str = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        old_func = self.current_function
        self.current_function = node.name
        self.call_graph[node.name] = []
        self.generic_visit(node)
        self.current_function = old_func

    def visit_Call(self, node: ast.Call):
        """Visit function call."""
        if self.current_function is None:
            return

        # Extract function name
        func_name = self._get_call_name(node.func)
        if func_name:
            if func_name in self.func_map:
                if func_name not in self.call_graph.get(self.current_function, []):
                    self.call_graph.setdefault(self.current_function, []).append(
                        func_name
                    )

        self.generic_visit(node)

    def _get_call_name(self, node: ast.AST) -> str:
        """Extract function name from call node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # Method call - could extract attribute name
            return None  # Skip method calls for now
        return None

