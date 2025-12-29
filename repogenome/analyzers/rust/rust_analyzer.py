"""
Rust file analyzer.

Extracts structure from Rust files including modules, functions, structs, traits, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class RustAnalyzer:
    """Analyzer for Rust files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Rust file and extract its structure.

        Args:
            file_path: Path to Rust file

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
                "classes": [],  # Structs, traits, enums in Rust
                "entry_points": [],
                "errors": ["Could not read file"],
            }

        module = self._extract_module(content)
        imports = self._extract_use_statements(content)
        types = self._extract_types(content)
        functions = self._extract_functions(content)
        entry_points = self._extract_entry_points(functions)

        return {
            "module": module,
            "imports": imports,
            "functions": functions,
            "classes": types,  # Using "classes" for consistency
            "entry_points": entry_points,
        }

    def _extract_module(self, content: str) -> str:
        """Extract module declaration."""
        match = re.search(r"^(?:pub\s+)?mod\s+(\w+)", content, re.MULTILINE)
        if match:
            return match.group(1)
        return ""

    def _extract_use_statements(self, content: str) -> List[Dict[str, Any]]:
        """Extract use statements."""
        imports = []
        # Match: use path::to::item; or use path::to::{item1, item2};
        pattern = r"^use\s+([\w::{}*]+);"
        for match in re.finditer(pattern, content, re.MULTILINE):
            use_path = match.group(1)
            imports.append({"module": use_path})
        return imports

    def _extract_types(self, content: str) -> List[Dict[str, Any]]:
        """Extract struct, enum, trait, and impl definitions."""
        types = []
        
        # Struct definitions: pub struct Name { ... } or struct Name { ... }
        struct_pattern = r"(?:pub\s+)?struct\s+(\w+)(?:\s*\{|\s*\(|\s*;)"
        for match in re.finditer(struct_pattern, content):
            types.append({"name": match.group(1), "type": "struct"})

        # Enum definitions: pub enum Name { ... }
        enum_pattern = r"(?:pub\s+)?enum\s+(\w+)\s*\{"
        for match in re.finditer(enum_pattern, content):
            types.append({"name": match.group(1), "type": "enum"})

        # Trait definitions: pub trait Name { ... }
        trait_pattern = r"(?:pub\s+)?trait\s+(\w+)\s*\{"
        for match in re.finditer(trait_pattern, content):
            types.append({"name": match.group(1), "type": "trait"})

        return types

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        
        # Function pattern: pub fn function_name(...) -> return_type { or fn function_name(...) { ...
        pattern = r"(?:pub\s+)?fn\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[\w:<>()]+)?\s*\{"
        for match in re.finditer(pattern, content):
            func_name = match.group(1)
            full_match = match.group(0)
            is_pub = "pub" in full_match
            
            functions.append({
                "name": func_name,
                "is_pub": is_pub,
            })

        # Methods in impl blocks: fn method_name(&self, ...) { or fn method_name(&mut self, ...) {
        # This is handled by the general pattern above

        return functions

    def _extract_entry_points(self, functions: List[Dict[str, Any]]) -> List[str]:
        """Extract main functions (entry points)."""
        entry_points = []
        for func in functions:
            if func["name"] == "main":
                entry_points.append(func["name"])
        return entry_points


def analyze_rust_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Rust file.

    Args:
        file_path: Path to Rust file

    Returns:
        Dictionary with extracted information
    """
    analyzer = RustAnalyzer()
    return analyzer.analyze_file(file_path)

