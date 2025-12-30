"""
Julia file analyzer.

Extracts structure from Julia files including imports, modules, functions, structs, types, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class JuliaAnalyzer:
    """Analyzer for Julia files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Julia file and extract its structure.

        Args:
            file_path: Path to Julia file

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
        modules = self._extract_modules(content)
        structs = self._extract_structs(content)
        types = self._extract_types(content)
        functions = self._extract_functions(content)
        entry_points = self._extract_entry_points(functions)

        # Combine modules, structs, and types into classes list
        all_types = modules + structs + types

        return {
            "imports": imports,
            "functions": functions,
            "classes": all_types,
            "entry_points": entry_points,
        }

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements (using and import)."""
        imports = []
        
        # using Package
        # using Package: Symbol1, Symbol2
        # import Package
        # import Package: Symbol1, Symbol2
        using_pattern = r"(?:using|import)\s+([\w.]+)(?:\s*:\s*([^;\n]+))?"
        for match in re.finditer(using_pattern, content):
            package = match.group(1)
            symbols = match.group(2).strip() if match.group(2) else None
            is_using = match.group(0).startswith("using")
            
            imports.append({
                "module": package,
                "symbols": symbols,
                "type": "using" if is_using else "import",
            })
        
        return imports

    def _extract_modules(self, content: str) -> List[Dict[str, Any]]:
        """Extract module definitions."""
        modules = []
        
        # module ModuleName ... end
        pattern = r"module\s+(\w+)"
        for match in re.finditer(pattern, content):
            module_name = match.group(1)
            modules.append({
                "name": module_name,
                "type": "module",
            })
        
        return modules

    def _extract_structs(self, content: str) -> List[Dict[str, Any]]:
        """Extract struct definitions."""
        structs = []
        
        # struct StructName ... end
        # mutable struct StructName ... end
        pattern = r"(?:mutable\s+)?struct\s+(\w+)"
        for match in re.finditer(pattern, content):
            struct_name = match.group(1)
            full_match = match.group(0)
            
            is_mutable = "mutable" in full_match
            
            structs.append({
                "name": struct_name,
                "type": "struct",
                "is_mutable": is_mutable,
            })
        
        return structs

    def _extract_types(self, content: str) -> List[Dict[str, Any]]:
        """Extract type definitions (deprecated but still valid)."""
        types = []
        
        # type TypeName ... end
        # immutable type TypeName ... end
        pattern = r"(?:immutable\s+)?type\s+(\w+)"
        for match in re.finditer(pattern, content):
            type_name = match.group(1)
            full_match = match.group(0)
            
            is_immutable = "immutable" in full_match
            
            types.append({
                "name": type_name,
                "type": "type",
                "is_immutable": is_immutable,
            })
        
        return types

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        
        # function function_name(...) ... end
        # function function_name(...) = ...
        pattern = r"function\s+([\w.]+)\s*\([^)]*\)"
        for match in re.finditer(pattern, content):
            func_name = match.group(1)
            
            # Check if it's a method (contains dot)
            is_method = "." in func_name
            
            functions.append({
                "name": func_name,
                "is_method": is_method,
            })
        
        # Short function syntax: function_name(...) = ...
        short_pattern = r"^(\w+)\s*\([^)]*\)\s*="
        for match in re.finditer(short_pattern, content, re.MULTILINE):
            func_name = match.group(1)
            # Skip if already found
            if not any(f["name"] == func_name for f in functions):
                functions.append({
                    "name": func_name,
                    "is_method": False,
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


def analyze_julia_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Julia file.

    Args:
        file_path: Path to Julia file

    Returns:
        Dictionary with extracted information
    """
    analyzer = JuliaAnalyzer()
    return analyzer.analyze_file(file_path)

