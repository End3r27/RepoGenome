"""
Java file analyzer.

Extracts structure from Java files including classes, methods, imports, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class JavaAnalyzer:
    """Analyzer for Java files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Java file and extract its structure.

        Args:
            file_path: Path to Java file

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

        # Remove comments first
        content = self._remove_comments(content)

        package = self._extract_package(content)
        imports = self._extract_imports(content)
        classes = self._extract_classes(content)
        functions = self._extract_methods(content, classes)
        entry_points = self._extract_entry_points(functions)

        return {
            "package": package,
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "entry_points": entry_points,
        }

    def _remove_comments(self, content: str) -> str:
        """Remove Java comments."""
        # Remove single-line comments
        content = re.sub(r"//.*", "", content)
        # Remove multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        return content

    def _extract_package(self, content: str) -> str:
        """Extract package declaration."""
        match = re.search(r"^package\s+([\w.]+);", content, re.MULTILINE)
        if match:
            return match.group(1)
        return ""

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        pattern = r"^import\s+(?:static\s+)?([\w.*]+);"
        for match in re.finditer(pattern, content, re.MULTILINE):
            import_path = match.group(1)
            is_static = "static" in match.group(0)
            imports.append({"module": import_path, "is_static": is_static})
        return imports

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class, interface, and enum definitions."""
        classes = []
        # Match class, interface, enum, @interface
        patterns = [
            r"(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?(?:class|interface|enum|@interface)\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w.,\s]+))?",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                class_name = match.group(1)
                extends = match.group(2) if match.group(2) else None
                implements = match.group(3).split(",") if match.group(3) else []
                implements = [i.strip() for i in implements]
                
                # Detect visibility
                visibility = "public" if "public" in match.group(0) else "private" if "private" in match.group(0) else "protected" if "protected" in match.group(0) else "package"
                
                classes.append({
                    "name": class_name,
                    "extends": extends,
                    "implements": implements,
                    "visibility": visibility,
                })
        return classes

    def _extract_methods(self, content: str, classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract method definitions."""
        methods = []
        
        # Match method declarations
        # Pattern: [modifiers] return_type method_name(parameters) [throws ...]
        method_pattern = r"(?:public|private|protected|static|final|abstract|synchronized|native|strictfp)\s+.*?\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w.,\s]+)?\s*\{"
        
        # More comprehensive pattern
        pattern = r"(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:abstract)?\s*(?:synchronized)?\s*(?:native)?\s*(?:strictfp)?\s+(?:[\w<>\[\].]+\s+)?(\w+)\s*\([^)]*\)"
        
        for match in re.finditer(pattern, content):
            method_name = match.group(1)
            full_match = match.group(0)
            
            # Skip constructors (same name as class)
            is_constructor = any(cls["name"] == method_name for cls in classes)
            
            # Detect visibility
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "protected" if "protected" in full_match else "package"
            is_static = "static" in full_match
            is_abstract = "abstract" in full_match
            is_final = "final" in full_match
            
            methods.append({
                "name": method_name,
                "visibility": visibility,
                "is_static": is_static,
                "is_abstract": is_abstract,
                "is_final": is_final,
                "is_constructor": is_constructor,
            })
        
        return methods

    def _extract_entry_points(self, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract main methods (entry points)."""
        entry_points = []
        for func in functions:
            if func["name"] == "main" and func.get("is_static"):
                entry_points.append(func["name"])
        return entry_points


def analyze_java_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Java file.

    Args:
        file_path: Path to Java file

    Returns:
        Dictionary with extracted information
    """
    analyzer = JavaAnalyzer()
    return analyzer.analyze_file(file_path)

