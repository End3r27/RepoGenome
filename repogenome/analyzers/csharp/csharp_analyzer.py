"""
C# file analyzer.

Extracts structure from C# files including classes, methods, namespaces, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class CSharpAnalyzer:
    """Analyzer for C# files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a C# file and extract its structure.

        Args:
            file_path: Path to C# file

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

        namespace = self._extract_namespace(content)
        imports = self._extract_using_statements(content)
        classes = self._extract_classes(content)
        functions = self._extract_methods(content)
        entry_points = self._extract_entry_points(functions)

        return {
            "namespace": namespace,
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "entry_points": entry_points,
        }

    def _remove_comments(self, content: str) -> str:
        """Remove C# comments."""
        # Remove single-line comments
        content = re.sub(r"//.*", "", content)
        # Remove multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        # Remove XML documentation comments (simplified)
        content = re.sub(r"///.*", "", content)
        return content

    def _extract_namespace(self, content: str) -> str:
        """Extract namespace declaration."""
        match = re.search(r"^namespace\s+([\w.]+)", content, re.MULTILINE)
        if match:
            return match.group(1)
        return ""

    def _extract_using_statements(self, content: str) -> List[Dict[str, Any]]:
        """Extract using statements."""
        imports = []
        # Match: using Namespace; or using alias = Namespace;
        pattern = r"^using\s+(?:(\w+)\s*=\s*)?([\w.]+);"
        for match in re.finditer(pattern, content, re.MULTILINE):
            alias = match.group(1)
            namespace = match.group(2)
            imports.append({"module": namespace, "alias": alias})
        return imports

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class, interface, struct, and enum definitions."""
        classes = []
        
        # Class/interface/struct/enum pattern
        pattern = r"(?:public|private|internal|protected)?\s*(?:abstract|sealed|static|partial)?\s*(?:class|interface|struct|enum)\s+(\w+)(?:\s*:\s*[\w.,\s<>]+)?\s*\{"
        
        for match in re.finditer(pattern, content):
            class_name = match.group(1)
            full_match = match.group(0)
            
            # Determine type
            if "class" in full_match:
                class_type = "class"
            elif "interface" in full_match:
                class_type = "interface"
            elif "struct" in full_match:
                class_type = "struct"
            elif "enum" in full_match:
                class_type = "enum"
            else:
                class_type = "class"
            
            # Detect visibility
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "internal" if "internal" in full_match else "protected" if "protected" in full_match else "internal"
            
            classes.append({
                "name": class_name,
                "type": class_type,
                "visibility": visibility,
            })

        return classes

    def _extract_methods(self, content: str) -> List[Dict[str, Any]]:
        """Extract method definitions."""
        methods = []
        
        # Method pattern: [modifiers] return_type MethodName(parameters) [where ...] {
        pattern = r"(?:public|private|internal|protected)?\s*(?:static|virtual|override|abstract|async)?\s*(?:[\w<>\[\].]+\s+)?(\w+)\s*\([^)]*\)(?:\s+where\s+[^{]+)?\s*\{"
        
        for match in re.finditer(pattern, content):
            method_name = match.group(1)
            full_match = match.group(0)
            
            # Skip constructors (same name as class - simplified check)
            # Skip properties (get; set; pattern)
            if method_name in ["get", "set", "add", "remove"]:
                continue
            
            # Detect visibility
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "internal" if "internal" in full_match else "protected" if "protected" in full_match else "internal"
            is_static = "static" in full_match
            is_virtual = "virtual" in full_match
            is_override = "override" in full_match
            is_abstract = "abstract" in full_match
            is_async = "async" in full_match
            
            methods.append({
                "name": method_name,
                "visibility": visibility,
                "is_static": is_static,
                "is_virtual": is_virtual,
                "is_override": is_override,
                "is_abstract": is_abstract,
                "is_async": is_async,
            })
        
        return methods

    def _extract_entry_points(self, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract Main methods (entry points)."""
        entry_points = []
        for func in functions:
            if func["name"] == "Main":
                entry_points.append(func["name"])
        return entry_points


def analyze_csharp_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a C# file.

    Args:
        file_path: Path to C# file

    Returns:
        Dictionary with extracted information
    """
    analyzer = CSharpAnalyzer()
    return analyzer.analyze_file(file_path)

