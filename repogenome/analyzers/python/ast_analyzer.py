"""
Python AST analyzer for extracting code structure.

This module parses Python files using the ast module and extracts
classes, functions, imports, and other structural elements.
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class PythonASTAnalyzer:
    """Analyzer for Python code using AST parsing."""

    def __init__(self):
        """Initialize the analyzer."""
        self.imports: Dict[str, List[str]] = {}
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.entry_points: List[str] = []
        self.decorators: Dict[str, List[str]] = {}

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Python file and extract its structure.

        Args:
            file_path: Path to Python file

        Returns:
            Dictionary with extracted information
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return {
                "imports": [],
                "functions": [],
                "classes": [],
                "entry_points": [],
                "errors": ["Could not read file"],
            }

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            return {
                "imports": [],
                "functions": [],
                "classes": [],
                "entry_points": [],
                "errors": [f"Syntax error: {e}"],
            }

        analyzer = _PythonASTVisitor(str(file_path))
        analyzer.visit(tree)

        # Check for entry point
        entry_points = []
        if analyzer.has_main_block:
            entry_points.append(str(file_path))

        return {
            "imports": analyzer.imports,
            "functions": analyzer.functions,
            "classes": analyzer.classes,
            "entry_points": entry_points,
            "decorators": analyzer.decorators,
            "api_routes": analyzer.api_routes,
        }


class _PythonASTVisitor(ast.NodeVisitor):
    """AST visitor for extracting Python code structure."""

    def __init__(self, file_path: str):
        """Initialize visitor."""
        self.file_path = file_path
        self.imports: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.has_main_block = False
        self.decorators: Dict[str, List[str]] = {}
        self.api_routes: List[Dict[str, Any]] = []
        self.current_class: Optional[str] = None

    def visit_Import(self, node: ast.Import):
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(
                {
                    "module": alias.name,
                    "alias": alias.asname,
                    "lineno": node.lineno,
                }
            )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from-import statements."""
        module = node.module or ""
        for alias in node.names:
            self.imports.append(
                {
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "lineno": node.lineno,
                }
            )

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        decorator_names = []
        api_route = None

        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if decorator_name:
                decorator_names.append(decorator_name)
                # Check for API route decorators
                if decorator_name in ["route", "get", "post", "put", "delete", "patch"]:
                    api_route = self._extract_route(decorator, node.name)

        func_info = {
            "name": node.name,
            "lineno": node.lineno,
            "args": [arg.arg for arg in node.args.args],
            "decorators": decorator_names,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "is_method": self.current_class is not None,
            "class": self.current_class,
        }

        if api_route:
            self.api_routes.append(api_route)

        self.functions.append(func_info)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions."""
        bases = [self._get_name(base) for base in node.bases]

        class_info = {
            "name": node.name,
            "lineno": node.lineno,
            "bases": bases,
            "decorators": [
                self._get_decorator_name(d) for d in node.decorator_list
            ],
        }

        self.classes.append(class_info)

        # Visit class body with context
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_If(self, node: ast.If):
        """Visit if statements (check for __main__ block)."""
        if isinstance(node.test, ast.Compare):
            if (
                isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == "__main__"
            ):
                self.has_main_block = True
        self.generic_visit(node)

    def _get_decorator_name(self, node: ast.AST) -> Optional[str]:
        """Extract decorator name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return node.func.attr
        return None

    def _get_name(self, node: ast.AST) -> str:
        """Extract name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def _extract_route(
        self, decorator: ast.AST, func_name: str
    ) -> Dict[str, Any]:
        """Extract API route information from decorator."""
        route_info = {
            "function": func_name,
            "method": "GET",
            "path": f"/{func_name}",
        }

        if isinstance(decorator, ast.Call):
            # Extract route path from decorator arguments
            if decorator.args:
                first_arg = decorator.args[0]
                if isinstance(first_arg, ast.Constant):
                    route_info["path"] = first_arg.value
                elif isinstance(first_arg, ast.Str):  # Python < 3.8
                    route_info["path"] = first_arg.s

            # Extract HTTP method from decorator name
            decorator_name = self._get_decorator_name(decorator.func)
            if decorator_name:
                route_info["method"] = decorator_name.upper()

        return route_info


def analyze_python_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Python file.

    Args:
        file_path: Path to Python file

    Returns:
        Dictionary with extracted information
    """
    analyzer = PythonASTAnalyzer()
    return analyzer.analyze_file(file_path)

