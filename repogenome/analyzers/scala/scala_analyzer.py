"""
Scala file analyzer.

Extracts structure from Scala files including imports, classes, objects, traits, functions, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class ScalaAnalyzer:
    """Analyzer for Scala files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Scala file and extract its structure.

        Args:
            file_path: Path to Scala file

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
        objects = self._extract_objects(content)
        traits = self._extract_traits(content)
        functions = self._extract_functions(content)
        entry_points = self._extract_entry_points(functions)

        # Combine classes, objects, and traits into classes list
        all_types = classes + objects + traits

        return {
            "package": package,
            "imports": imports,
            "functions": functions,
            "classes": all_types,
            "entry_points": entry_points,
        }

    def _remove_comments(self, content: str) -> str:
        """Remove Scala comments."""
        # Remove single-line comments
        content = re.sub(r"//.*", "", content)
        # Remove multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        return content

    def _extract_package(self, content: str) -> str:
        """Extract package declaration."""
        match = re.search(r"^package\s+([\w.]+)", content, re.MULTILINE)
        if match:
            return match.group(1)
        return ""

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        # import package.Class
        # import package.{Class1, Class2}
        # import package.Class as Alias
        pattern = r"^import\s+([\w.{}]+)(?:\s+as\s+(\w+))?"
        for match in re.finditer(pattern, content, re.MULTILINE):
            module = match.group(1)
            alias = match.group(2) if match.group(2) else None
            imports.append({"module": module, "alias": alias})
        return imports

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        classes = []
        # class ClassName extends SuperClass with Trait1 with Trait2 { ... }
        # class ClassName { ... }
        pattern = r"(?:case\s+|abstract\s+|sealed\s+|final\s+)?(?:case\s+|abstract\s+|sealed\s+|final\s+)*class\s+(\w+)(?:\([^)]*\))?(?:\s+extends\s+([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            class_name = match.group(1)
            inheritance = match.group(2).strip() if match.group(2) else None
            full_match = match.group(0)
            
            # Detect modifiers
            is_case = "case" in full_match
            is_abstract = "abstract" in full_match
            is_sealed = "sealed" in full_match
            is_final = "final" in full_match
            
            classes.append({
                "name": class_name,
                "type": "class",
                "inheritance": inheritance,
                "is_case": is_case,
                "is_abstract": is_abstract,
                "is_sealed": is_sealed,
                "is_final": is_final,
            })
        return classes

    def _extract_objects(self, content: str) -> List[Dict[str, Any]]:
        """Extract object definitions."""
        objects = []
        # object ObjectName extends Trait { ... }
        pattern = r"(?:case\s+)?object\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            object_name = match.group(1)
            traits = match.group(2).strip() if match.group(2) else None
            full_match = match.group(0)
            
            is_case = "case" in full_match
            
            objects.append({
                "name": object_name,
                "type": "object",
                "traits": traits,
                "is_case": is_case,
            })
        return objects

    def _extract_traits(self, content: str) -> List[Dict[str, Any]]:
        """Extract trait definitions."""
        traits = []
        # trait TraitName extends ParentTrait { ... }
        pattern = r"trait\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{"
        for match in re.finditer(pattern, content, re.MULTILINE):
            trait_name = match.group(1)
            parent = match.group(2).strip() if match.group(2) else None
            
            traits.append({
                "name": trait_name,
                "type": "trait",
                "parent": parent,
            })
        return traits

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function and method definitions."""
        functions = []
        
        # def functionName(...): ReturnType = { ... }
        # def functionName(...): ReturnType = expression
        pattern = r"(?:override\s+|final\s+|protected\s+|private\s+)?(?:override\s+|final\s+|protected\s+|private\s+)*def\s+(\w+)\s*\([^)]*\)(?:\s*:\s*[^=]+)?\s*="
        for match in re.finditer(pattern, content, re.MULTILINE):
            func_name = match.group(1)
            full_match = match.group(0)
            
            # Detect modifiers
            is_override = "override" in full_match
            is_final = "final" in full_match
            is_protected = "protected" in full_match
            is_private = "private" in full_match
            
            visibility = "protected" if is_protected else "private" if is_private else "public"
            
            functions.append({
                "name": func_name,
                "visibility": visibility,
                "is_override": is_override,
                "is_final": is_final,
            })
        
        return functions

    def _extract_entry_points(self, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract main methods (entry points)."""
        entry_points = []
        for func in functions:
            if func["name"] == "main":
                entry_points.append("main")
                break
        return entry_points


def analyze_scala_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Scala file.

    Args:
        file_path: Path to Scala file

    Returns:
        Dictionary with extracted information
    """
    analyzer = ScalaAnalyzer()
    return analyzer.analyze_file(file_path)

