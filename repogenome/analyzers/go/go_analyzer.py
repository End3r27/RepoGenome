"""
Go file analyzer.

Extracts structure from Go files including packages, functions, types, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class GoAnalyzer:
    """Analyzer for Go files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Go file and extract its structure.

        Args:
            file_path: Path to Go file

        Returns:
            Dictionary with extracted information
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return {
                "imports": [],
                "functions": [],
                "classes": [],  # Types in Go
                "entry_points": [],
                "errors": ["Could not read file"],
            }

        package = self._extract_package(content)
        imports = self._extract_imports(content)
        types = self._extract_types(content)
        functions = self._extract_functions(content)
        entry_points = self._extract_entry_points(functions)

        return {
            "package": package,
            "imports": imports,
            "functions": functions,
            "classes": types,  # Using "classes" for consistency with other analyzers
            "entry_points": entry_points,
        }

    def _extract_package(self, content: str) -> str:
        """Extract package declaration."""
        match = re.search(r"^package\s+(\w+)", content, re.MULTILINE)
        if match:
            return match.group(1)
        return ""

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        # Single import: import "package"
        single_pattern = r'^import\s+"([^"]+)"'
        for match in re.finditer(single_pattern, content, re.MULTILINE):
            imports.append({"module": match.group(1)})

        # Multiple imports: import ( "pkg1" "pkg2" )
        multi_pattern = r'^import\s*\(\s*((?:"[^"]+"\s*)+)\s*\)'
        for match in re.finditer(multi_pattern, content, re.MULTILINE):
            packages = re.findall(r'"([^"]+)"', match.group(1))
            for pkg in packages:
                imports.append({"module": pkg})

        # Alias imports: import alias "package"
        alias_pattern = r'^import\s+(\w+)\s+"([^"]+)"'
        for match in re.finditer(alias_pattern, content, re.MULTILINE):
            imports.append({"module": match.group(2), "alias": match.group(1)})

        return imports

    def _extract_types(self, content: str) -> List[Dict[str, Any]]:
        """Extract type definitions (struct, interface, type aliases)."""
        types = []
        
        # Struct definitions: type Name struct { ... }
        struct_pattern = r"type\s+(\w+)\s+struct\s*\{"
        for match in re.finditer(struct_pattern, content):
            types.append({"name": match.group(1), "type": "struct"})

        # Interface definitions: type Name interface { ... }
        interface_pattern = r"type\s+(\w+)\s+interface\s*\{"
        for match in re.finditer(interface_pattern, content):
            types.append({"name": match.group(1), "type": "interface"})

        # Type aliases: type Name = Type or type Name Type
        type_pattern = r"type\s+(\w+)\s+(?:=|[\w\[\]*]+)"
        for match in re.finditer(type_pattern, content):
            name = match.group(1)
            # Skip if already added as struct or interface
            if not any(t["name"] == name for t in types):
                types.append({"name": name, "type": "alias"})

        return types

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function and method definitions."""
        functions = []
        
        # Regular functions: func FunctionName(...) ...
        func_pattern = r"^func\s+(\w+)\s*\([^)]*\)\s*(?:\([^)]*\))?"
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            func_name = match.group(1)
            functions.append({
                "name": func_name,
                "is_method": False,
            })

        # Methods: func (receiver) MethodName(...) ...
        method_pattern = r"^func\s+\([^)]+\)\s+(\w+)\s*\([^)]*\)"
        for match in re.finditer(method_pattern, content, re.MULTILINE):
            method_name = match.group(1)
            functions.append({
                "name": method_name,
                "is_method": True,
            })

        return functions

    def _extract_entry_points(self, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract main functions (entry points)."""
        entry_points = []
        for func in functions:
            if func["name"] == "main":
                entry_points.append(func["name"])
        return entry_points


def analyze_go_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Go file.

    Args:
        file_path: Path to Go file

    Returns:
        Dictionary with extracted information
    """
    analyzer = GoAnalyzer()
    return analyzer.analyze_file(file_path)

