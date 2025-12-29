"""
C++ file analyzer.

Extracts structure from C++ files including classes, functions, includes, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class CPPAnalyzer:
    """Analyzer for C++ files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a C++ file and extract its structure.

        Args:
            file_path: Path to C++ file

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
                "classes": [],
                "entry_points": [],
                "errors": ["Could not read file"],
            }

        # Remove comments
        content = self._remove_comments(content)

        imports = self._extract_includes(content)
        classes = self._extract_classes(content)
        functions = self._extract_functions(content)
        entry_points = self._extract_entry_points(functions)

        return {
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "entry_points": entry_points,
        }

    def _remove_comments(self, content: str) -> str:
        """Remove C++ comments."""
        # Remove single-line comments
        content = re.sub(r"//.*", "", content)
        # Remove multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        return content

    def _extract_includes(self, content: str) -> List[Dict[str, Any]]:
        """Extract #include statements."""
        imports = []
        # Match #include <header> or #include "header"
        pattern = r'#include\s+([<"])([^>"]+)([>"])'
        for match in re.finditer(pattern, content):
            header = match.group(2)
            is_system = match.group(1) == "<"
            imports.append({"module": header, "is_system": is_system})
        return imports

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class, struct, and namespace definitions."""
        classes = []
        
        # Class definitions: class Name { or class Name : Base { ...
        class_pattern = r"(?:class|struct|union)\s+(\w+)(?:\s*:\s*(?:public|private|protected)?\s*[\w:,<>]+)?\s*\{"
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            full_match = match.group(0)
            class_type = "class" if "class" in full_match else "struct" if "struct" in full_match else "union"
            classes.append({
                "name": class_name,
                "type": class_type,
            })

        return classes

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        
        # Function pattern: [return_type] function_name(parameters) [const] { or ;
        # This is simplified - C++ function syntax is complex with templates
        pattern = r"(?:[\w:<>*&]+\s+)?(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:\{|;|=)"
        
        for match in re.finditer(pattern, content):
            func_name = match.group(1)
            full_match = match.group(0)
            
            # Skip common keywords that might match
            keywords = {"if", "while", "for", "switch", "catch", "return", "new", "delete", "sizeof", "static_cast", "dynamic_cast", "const_cast", "reinterpret_cast"}
            if func_name in keywords:
                continue
            
            # Detect if const method
            is_const = "const" in full_match
            
            functions.append({
                "name": func_name,
                "is_const": is_const,
            })
        
        return functions

    def _extract_entry_points(self, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract main functions (entry points)."""
        entry_points = []
        for func in functions:
            if func["name"] == "main":
                entry_points.append(func["name"])
        return entry_points


def analyze_cpp_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a C++ file.

    Args:
        file_path: Path to C++ file

    Returns:
        Dictionary with extracted information
    """
    analyzer = CPPAnalyzer()
    return analyzer.analyze_file(file_path)

