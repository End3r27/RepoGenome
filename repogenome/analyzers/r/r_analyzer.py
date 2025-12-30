"""
R file analyzer.

Extracts structure from R files including library imports, functions, S3 classes/methods, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class RAnalyzer:
    """Analyzer for R files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze an R file and extract its structure.

        Args:
            file_path: Path to R file

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
        functions = self._extract_functions(content)
        s3_classes = self._extract_s3_classes(functions)
        entry_points = self._extract_entry_points(content)

        return {
            "imports": imports,
            "functions": functions,
            "classes": s3_classes,
            "entry_points": entry_points,
        }

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract library imports and source statements."""
        imports = []
        
        # library(package)
        library_pattern = r"library\s*\(\s*([^)]+)\s*\)"
        for match in re.finditer(library_pattern, content):
            package = match.group(1).strip().strip('"').strip("'")
            imports.append({"module": package, "type": "library"})
        
        # require(package)
        require_pattern = r"require\s*\(\s*([^)]+)\s*\)"
        for match in re.finditer(require_pattern, content):
            package = match.group(1).strip().strip('"').strip("'")
            imports.append({"module": package, "type": "require"})
        
        # source("file.R")
        source_pattern = r'source\s*\(\s*"([^"]+)"\s*\)'
        for match in re.finditer(source_pattern, content):
            file_path = match.group(1)
            imports.append({"module": file_path, "type": "source"})
        
        # source('file.R')
        source_pattern2 = r"source\s*\(\s*'([^']+)'\s*\)"
        for match in re.finditer(source_pattern2, content):
            file_path = match.group(1)
            imports.append({"module": file_path, "type": "source"})
        
        return imports

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        
        # function_name <- function(...) { ... }
        # Handle multiline definitions by looking for <- and function(...)
        pattern = r"(\w+)\s*<-\s*function\s*\([^)]*\)\s*\{"
        for match in re.finditer(pattern, content):
            func_name = match.group(1)
            full_match = match.group(0)
            
            # Check if it's an S3 method (contains dot)
            is_s3_method = "." in func_name
            
            functions.append({
                "name": func_name,
                "is_s3_method": is_s3_method,
            })
        
        return functions

    def _extract_s3_classes(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract S3 classes from function names (method.class pattern)."""
        classes = []
        class_names = set()
        
        for func in functions:
            func_name = func["name"]
            if "." in func_name:
                # Extract class name from method.class pattern
                parts = func_name.split(".", 1)
                if len(parts) == 2:
                    class_name = parts[1]
                    class_names.add(class_name)
        
        for class_name in class_names:
            classes.append({
                "name": class_name,
                "type": "s3_class",
            })
        
        return classes

    def _extract_entry_points(self, content: str) -> List[str]:
        """
        Extract entry points.
        
        R scripts are typically executed top-level, so we consider
        the file itself as an entry point if it has executable content.
        """
        entry_points = []
        
        # Check if file has any executable code (not just comments)
        # Simple heuristic: has non-comment, non-whitespace content
        content_without_comments = re.sub(r"#.*", "", content)
        content_clean = re.sub(r"\s+", "", content_without_comments)
        
        if content_clean:
            entry_points.append("script")
        
        return entry_points


def analyze_r_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze an R file.

    Args:
        file_path: Path to R file

    Returns:
        Dictionary with extracted information
    """
    analyzer = RAnalyzer()
    return analyzer.analyze_file(file_path)

