"""
Kotlin file analyzer.

Extracts structure from Kotlin files including imports, classes, objects, interfaces, functions, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class KotlinAnalyzer:
    """Analyzer for Kotlin files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Kotlin file and extract its structure.

        Args:
            file_path: Path to Kotlin file

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

        imports = self._extract_imports(content)
        classes = self._extract_classes(content)
        objects = self._extract_objects(content)
        interfaces = self._extract_interfaces(content)
        functions = self._extract_functions(content)
        entry_points = self._extract_entry_points(functions)

        # Combine classes, objects, and interfaces into classes list
        all_types = classes + objects + interfaces

        return {
            "imports": imports,
            "functions": functions,
            "classes": all_types,
            "entry_points": entry_points,
        }

    def _remove_comments(self, content: str) -> str:
        """Remove Kotlin comments."""
        # Remove single-line comments
        content = re.sub(r"//.*", "", content)
        # Remove multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        return content

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        # import package.Class
        # import package.Class as Alias
        pattern = r"^import\s+([\w.]+)(?:\s+as\s+(\w+))?"
        for match in re.finditer(pattern, content, re.MULTILINE):
            module = match.group(1)
            alias = match.group(2) if match.group(2) else None
            imports.append({"module": module, "alias": alias})
        return imports

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        classes = []
        # class ClassName constructor(...) : SuperClass, Interface { ... }
        # class ClassName { ... }
        pattern = r"(?:public|private|protected|internal|open|abstract|data|sealed)?\s*(?:open\s+|abstract\s+|data\s+|sealed\s+)*class\s+(\w+)(?:\([^)]*\))?(?:\s*:\s*([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            class_name = match.group(1)
            inheritance = match.group(2).strip() if match.group(2) else None
            full_match = match.group(0)
            
            # Detect visibility and modifiers
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "protected" if "protected" in full_match else "internal" if "internal" in full_match else "public"
            is_data = "data" in full_match
            is_sealed = "sealed" in full_match
            is_abstract = "abstract" in full_match
            is_open = "open" in full_match
            
            classes.append({
                "name": class_name,
                "type": "class",
                "visibility": visibility,
                "inheritance": inheritance,
                "is_data": is_data,
                "is_sealed": is_sealed,
                "is_abstract": is_abstract,
                "is_open": is_open,
            })
        return classes

    def _extract_objects(self, content: str) -> List[Dict[str, Any]]:
        """Extract object definitions."""
        objects = []
        # object ObjectName : Interface { ... }
        pattern = r"(?:public|private|protected|internal)?\s*object\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            object_name = match.group(1)
            interfaces = match.group(2).strip() if match.group(2) else None
            full_match = match.group(0)
            
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "protected" if "protected" in full_match else "internal" if "internal" in full_match else "public"
            
            objects.append({
                "name": object_name,
                "type": "object",
                "visibility": visibility,
                "interfaces": interfaces,
            })
        return objects

    def _extract_interfaces(self, content: str) -> List[Dict[str, Any]]:
        """Extract interface definitions."""
        interfaces = []
        # interface InterfaceName : ParentInterface { ... }
        pattern = r"(?:public|private|protected|internal)?\s*interface\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            interface_name = match.group(1)
            parent = match.group(2).strip() if match.group(2) else None
            full_match = match.group(0)
            
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "protected" if "protected" in full_match else "internal" if "internal" in full_match else "public"
            
            interfaces.append({
                "name": interface_name,
                "type": "interface",
                "visibility": visibility,
                "parent": parent,
            })
        return interfaces

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        
        # fun functionName(...): ReturnType { ... }
        # fun ClassName.functionName(...): ReturnType { ... } (extension function)
        pattern = r"(?:public|private|protected|internal|override|open|abstract|final)?\s*(?:override\s+|open\s+|abstract\s+|final\s+|suspend\s+)*fun\s+(?:\w+\.)?(\w+)\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            func_name = match.group(1)
            full_match = match.group(0)
            
            # Detect visibility and modifiers
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "protected" if "protected" in full_match else "internal" if "internal" in full_match else "public"
            is_suspend = "suspend" in full_match
            is_override = "override" in full_match
            is_open = "open" in full_match
            is_abstract = "abstract" in full_match
            is_extension = "." in full_match[:full_match.find(func_name)]
            
            functions.append({
                "name": func_name,
                "visibility": visibility,
                "is_suspend": is_suspend,
                "is_override": is_override,
                "is_open": is_open,
                "is_abstract": is_abstract,
                "is_extension": is_extension,
            })
        
        return functions

    def _extract_entry_points(self, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract main functions (entry points)."""
        entry_points = []
        for func in functions:
            if func["name"] == "main":
                entry_points.append("main")
                break
        return entry_points


def analyze_kotlin_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Kotlin file.

    Args:
        file_path: Path to Kotlin file

    Returns:
        Dictionary with extracted information
    """
    analyzer = KotlinAnalyzer()
    return analyzer.analyze_file(file_path)

