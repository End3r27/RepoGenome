"""
Swift file analyzer.

Extracts structure from Swift files including imports, classes, structs, enums, functions, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class SwiftAnalyzer:
    """Analyzer for Swift files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Swift file and extract its structure.

        Args:
            file_path: Path to Swift file

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

        imports = self._extract_imports(content)
        classes = self._extract_classes(content)
        structs = self._extract_structs(content)
        enums = self._extract_enums(content)
        functions = self._extract_functions(content)
        entry_points = self._extract_entry_points(content, functions)

        # Combine classes, structs, and enums into classes list
        all_types = classes + structs + enums

        return {
            "imports": imports,
            "functions": functions,
            "classes": all_types,
            "entry_points": entry_points,
        }

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        # import ModuleName
        # import kind ModuleName
        pattern = r"^import\s+(?:(\w+)\s+)?([\w.]+)"
        for match in re.finditer(pattern, content, re.MULTILINE):
            kind = match.group(1) if match.group(1) else None
            module = match.group(2)
            imports.append({"module": module, "kind": kind})
        return imports

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        classes = []
        # class ClassName: SuperClass, Protocol1, Protocol2 { ... }
        # Handle visibility modifiers and inheritance
        pattern = r"(?:public|private|internal|fileprivate|open)?\s*(?:final|abstract)?\s*class\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            class_name = match.group(1)
            inheritance = match.group(2).strip() if match.group(2) else None
            full_match = match.group(0)
            
            # Detect visibility
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "internal" if "internal" in full_match else "fileprivate" if "fileprivate" in full_match else "internal"
            
            classes.append({
                "name": class_name,
                "type": "class",
                "visibility": visibility,
                "inheritance": inheritance,
            })
        return classes

    def _extract_structs(self, content: str) -> List[Dict[str, Any]]:
        """Extract struct definitions."""
        structs = []
        # struct StructName: Protocol1, Protocol2 { ... }
        pattern = r"(?:public|private|internal|fileprivate)?\s*struct\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            struct_name = match.group(1)
            protocols = match.group(2).strip() if match.group(2) else None
            full_match = match.group(0)
            
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "internal" if "internal" in full_match else "fileprivate" if "fileprivate" in full_match else "internal"
            
            structs.append({
                "name": struct_name,
                "type": "struct",
                "visibility": visibility,
                "protocols": protocols,
            })
        return structs

    def _extract_enums(self, content: str) -> List[Dict[str, Any]]:
        """Extract enum definitions."""
        enums = []
        # enum EnumName: Type { ... }
        # enum EnumName { ... }
        pattern = r"(?:public|private|internal|fileprivate)?\s*(?:indirect\s+)?enum\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            enum_name = match.group(1)
            raw_value_type = match.group(2).strip() if match.group(2) else None
            full_match = match.group(0)
            
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "internal" if "internal" in full_match else "fileprivate" if "fileprivate" in full_match else "internal"
            
            enums.append({
                "name": enum_name,
                "type": "enum",
                "visibility": visibility,
                "raw_value_type": raw_value_type,
            })
        return enums

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function and method definitions."""
        functions = []
        
        # func functionName(...) -> ReturnType { ... }
        # Handle static, mutating, async, throws, etc.
        pattern = r"(?:public|private|internal|fileprivate|open|static|mutating|async|throws)?\s*(?:static\s+|mutating\s+|async\s+|throws\s+)*func\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[^{]+)?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            func_name = match.group(1)
            full_match = match.group(0)
            
            # Detect visibility and modifiers
            visibility = "public" if "public" in full_match else "private" if "private" in full_match else "internal" if "internal" in full_match else "fileprivate" if "fileprivate" in full_match else "internal"
            is_static = "static" in full_match
            is_mutating = "mutating" in full_match
            is_async = "async" in full_match
            is_throwing = "throws" in full_match
            
            functions.append({
                "name": func_name,
                "visibility": visibility,
                "is_static": is_static,
                "is_mutating": is_mutating,
                "is_async": is_async,
                "is_throwing": is_throwing,
            })
        
        return functions

    def _extract_entry_points(self, content: str, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract entry points (@main attribute or main function)."""
        entry_points = []
        
        # Check for @main attribute
        if "@main" in content:
            # Try to find the associated struct, class, or enum
            main_pattern = r"@main\s+(?:struct|class|enum)\s+(\w+)"
            match = re.search(main_pattern, content)
            if match:
                entry_points.append(match.group(1))
            else:
                entry_points.append("@main")
        
        # Check for main() function
        for func in functions:
            if func["name"] == "main":
                entry_points.append("main")
                break
        
        return entry_points


def analyze_swift_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Swift file.

    Args:
        file_path: Path to Swift file

    Returns:
        Dictionary with extracted information
    """
    analyzer = SwiftAnalyzer()
    return analyzer.analyze_file(file_path)

