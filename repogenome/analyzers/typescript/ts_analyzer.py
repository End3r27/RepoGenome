"""
TypeScript/JavaScript analyzer using tree-sitter.

This module provides basic TypeScript/JavaScript code analysis.
For full tree-sitter support, the tree-sitter-typescript package is needed.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class TypeScriptAnalyzer:
    """Analyzer for TypeScript and JavaScript code."""

    def __init__(self):
        """Initialize the analyzer."""
        self.tree_sitter_available = False
        try:
            import tree_sitter
            import tree_sitter_typescript

            self.tree_sitter_available = True
            self.ts_language = tree_sitter_typescript.language_typescript()
            self.tsx_language = tree_sitter_typescript.language_tsx()
            self.parser = tree_sitter.Parser()
        except ImportError:
            # Fall back to regex-based parsing
            pass

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a TypeScript/JavaScript file.

        Args:
            file_path: Path to TypeScript/JavaScript file

        Returns:
            Dictionary with extracted information
        """
        if self.tree_sitter_available:
            return self._analyze_with_tree_sitter(file_path)
        else:
            return self._analyze_with_regex(file_path)

    def _analyze_with_tree_sitter(self, file_path: Path) -> Dict[str, Any]:
        """Analyze using tree-sitter (more accurate)."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().encode("utf-8")

            # Select language based on extension
            if file_path.suffix == ".tsx" or file_path.suffix == ".jsx":
                self.parser.set_language(self.tsx_language)
            else:
                self.parser.set_language(self.ts_language)

            tree = self.parser.parse(content)
            return self._extract_from_tree_sitter(tree, content.decode("utf-8"))

        except Exception as e:
            return {
                "imports": [],
                "functions": [],
                "classes": [],
                "entry_points": [],
                "errors": [str(e)],
            }

    def _analyze_with_regex(self, file_path: Path) -> Dict[str, Any]:
        """
        Fallback regex-based analyzer (less accurate but works without tree-sitter).

        Args:
            file_path: Path to file

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

        imports = self._extract_imports_regex(content)
        functions = self._extract_functions_regex(content)
        classes = self._extract_classes_regex(content)
        api_routes = self._extract_api_routes_regex(content)

        return {
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "entry_points": [],
            "api_routes": api_routes,
        }

    def _extract_imports_regex(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements using regex."""
        imports = []
        # Match: import ... from '...'
        pattern = r"import\s+(?:(\w+)|(?:\{([^}]+)\})|(?:\*\s+as\s+(\w+)))\s+from\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(pattern, content):
            default_import = match.group(1)
            named_imports = match.group(2)
            namespace_import = match.group(3)
            module = match.group(4)

            if default_import:
                imports.append({"module": module, "name": default_import})
            elif named_imports:
                for name in re.split(r",\s*", named_imports):
                    name = name.strip()
                    alias_match = re.match(r"(\w+)(?:\s+as\s+(\w+))?", name)
                    if alias_match:
                        imports.append(
                            {
                                "module": module,
                                "name": alias_match.group(1),
                                "alias": alias_match.group(2),
                            }
                        )
            elif namespace_import:
                imports.append(
                    {"module": module, "name": namespace_import, "is_namespace": True}
                )

        return imports

    def _extract_functions_regex(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions using regex."""
        functions = []
        # Match function declarations, arrow functions, method definitions
        patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            r"(?:export\s+)?(?:async\s+)?const\s+(\w+)\s*[:=]\s*(?:async\s+)?\([^)]*\)\s*=>",
            r"(?:export\s+)?(\w+)\s*:\s*(?:async\s+)?\([^)]*\)\s*=>",
            r"(?:public\s+|private\s+|protected\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                if func_name and func_name not in [f["name"] for f in functions]:
                    functions.append(
                        {
                            "name": func_name,
                            "is_async": "async" in match.group(0),
                            "is_export": "export" in match.group(0),
                        }
                    )

        return functions

    def _extract_classes_regex(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions using regex."""
        classes = []
        pattern = r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for match in re.finditer(pattern, content):
            classes.append(
                {
                    "name": match.group(1),
                    "extends": match.group(2),
                    "is_export": "export" in match.group(0),
                }
            )
        return classes

    def _extract_api_routes_regex(self, content: str) -> List[Dict[str, Any]]:
        """Extract API routes (Express, Next.js, etc.)."""
        routes = []
        # Express routes: app.get('/path', handler) or router.post('/path', handler)
        pattern = r"(?:app|router)\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]"
        for match in re.finditer(pattern, content):
            routes.append(
                {
                    "method": match.group(1).upper(),
                    "path": match.group(2),
                }
            )
        return routes

    def _extract_from_tree_sitter(
        self, tree, content: str
    ) -> Dict[str, Any]:
        """Extract information from tree-sitter AST."""
        # This would traverse the tree-sitter tree
        # For now, fall back to regex if tree-sitter fails
        return self._analyze_with_regex(Path(""))


def analyze_typescript_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a TypeScript/JavaScript file.

    Args:
        file_path: Path to file

    Returns:
        Dictionary with extracted information
    """
    analyzer = TypeScriptAnalyzer()
    return analyzer.analyze_file(file_path)

