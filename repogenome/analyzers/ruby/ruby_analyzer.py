"""
Ruby file analyzer.

Extracts structure from Ruby files including classes, modules, methods, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class RubyAnalyzer:
    """Analyzer for Ruby files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Ruby file and extract its structure.

        Args:
            file_path: Path to Ruby file

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

        requires = self._extract_requires(content)
        modules = self._extract_modules(content)
        classes = self._extract_classes(content)
        functions = self._extract_methods(content)

        return {
            "imports": requires,
            "functions": functions,
            "classes": classes,
            "modules": modules,
            "entry_points": [],  # Ruby doesn't have a standard main entry point
        }

    def _extract_requires(self, content: str) -> List[Dict[str, Any]]:
        """Extract require and require_relative statements."""
        imports = []
        # require "library" or require 'library'
        require_pattern = r"^require\s+(?:['\"])([^'\"]+)(?:['\"])"
        for match in re.finditer(require_pattern, content, re.MULTILINE):
            imports.append({"module": match.group(1), "type": "require"})

        # require_relative "path"
        require_relative_pattern = r"^require_relative\s+(?:['\"])([^'\"]+)(?:['\"])"
        for match in re.finditer(require_relative_pattern, content, re.MULTILINE):
            imports.append({"module": match.group(1), "type": "require_relative"})

        return imports

    def _extract_modules(self, content: str) -> List[Dict[str, Any]]:
        """Extract module definitions."""
        modules = []
        pattern = r"^module\s+(\w+(?:::\w+)*)"
        for match in re.finditer(pattern, content, re.MULTILINE):
            modules.append({"name": match.group(1)})
        return modules

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        classes = []
        # Class pattern: class Name or class Name < Parent
        pattern = r"^class\s+(\w+(?:::\w+)*)(?:\s*<\s*([\w:]+))?"
        for match in re.finditer(pattern, content, re.MULTILINE):
            class_name = match.group(1)
            parent = match.group(2) if match.group(2) else None
            classes.append({
                "name": class_name,
                "extends": parent,
            })
        return classes

    def _extract_methods(self, content: str) -> List[Dict[str, Any]]:
        """Extract method definitions."""
        methods = []
        
        # Method definitions: def method_name or def self.method_name or def ClassName.method_name
        pattern = r"^def\s+(?:self\.|[\w:]+\.)?(\w+)(?:\([^)]*\))?"
        for match in re.finditer(pattern, content, re.MULTILINE):
            method_name = match.group(1)
            full_match = match.group(0)
            
            # Detect if class method (self. or ClassName.)
            is_class_method = "self." in full_match or "." in full_match and "self" not in full_match
            
            methods.append({
                "name": method_name,
                "is_class_method": is_class_method,
            })

        return methods


def analyze_ruby_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Ruby file.

    Args:
        file_path: Path to Ruby file

    Returns:
        Dictionary with extracted information
    """
    analyzer = RubyAnalyzer()
    return analyzer.analyze_file(file_path)

