"""
PHP file analyzer.

Extracts structure from PHP files including classes, functions, namespaces, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class PHPAnalyzer:
    """Analyzer for PHP files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a PHP file and extract its structure.

        Args:
            file_path: Path to PHP file

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
        imports = self._extract_use_statements(content)
        classes = self._extract_classes(content)
        functions = self._extract_functions(content)

        return {
            "namespace": namespace,
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "entry_points": [],  # PHP doesn't have a standard main entry point
        }

    def _remove_comments(self, content: str) -> str:
        """Remove PHP comments."""
        # Remove single-line comments
        content = re.sub(r"//.*", "", content)
        content = re.sub(r"#.*", "", content)
        # Remove multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        return content

    def _extract_namespace(self, content: str) -> str:
        """Extract namespace declaration."""
        match = re.search(r"^namespace\s+([\w\\]+);", content, re.MULTILINE)
        if match:
            return match.group(1)
        return ""

    def _extract_use_statements(self, content: str) -> List[Dict[str, Any]]:
        """Extract use statements (imports)."""
        imports = []
        # Match: use Namespace\Class; or use Namespace\Class as Alias;
        pattern = r"^use\s+([\w\\]+)(?:\s+as\s+(\w+))?;"
        for match in re.finditer(pattern, content, re.MULTILINE):
            namespace = match.group(1)
            alias = match.group(2) if match.group(2) else None
            imports.append({"module": namespace, "alias": alias})
        return imports

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class, interface, and trait definitions."""
        classes = []
        
        # Class/interface/trait pattern
        pattern = r"(?:abstract\s+|final\s+)?(?:class|interface|trait)\s+(\w+)(?:\s+extends\s+([\w\\]+))?(?:\s+implements\s+([\w\\,\s]+))?"
        
        for match in re.finditer(pattern, content):
            class_name = match.group(1)
            full_match = match.group(0)
            extends = match.group(2) if match.group(2) else None
            implements_str = match.group(3)
            implements = [i.strip() for i in implements_str.split(",")] if implements_str else []
            
            # Determine type
            if "class" in full_match:
                class_type = "class"
            elif "interface" in full_match:
                class_type = "interface"
            elif "trait" in full_match:
                class_type = "trait"
            else:
                class_type = "class"
            
            classes.append({
                "name": class_name,
                "type": class_type,
                "extends": extends,
                "implements": implements,
            })

        return classes

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function and method definitions."""
        functions = []
        
        # Function pattern: function function_name(...) { or public function method_name(...) {
        pattern = r"(?:public|private|protected|static)?\s*(?:abstract\s+|final\s+)?function\s+(\w+)\s*\([^)]*\)"
        
        for match in re.finditer(pattern, content):
            func_name = match.group(1)
            full_match = match.group(0)
            
            # Detect visibility (for methods)
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "protected" if "protected" in full_match else "public"
            is_static = "static" in full_match
            is_abstract = "abstract" in full_match
            is_final = "final" in full_match
            
            functions.append({
                "name": func_name,
                "visibility": visibility,
                "is_static": is_static,
                "is_abstract": is_abstract,
                "is_final": is_final,
            })

        return functions


def analyze_php_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a PHP file.

    Args:
        file_path: Path to PHP file

    Returns:
        Dictionary with extracted information
    """
    analyzer = PHPAnalyzer()
    return analyzer.analyze_file(file_path)

