"""
MATLAB file analyzer.

Extracts structure from MATLAB files including functions, classes, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class MATLABAnalyzer:
    """Analyzer for MATLAB files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a MATLAB file and extract its structure.

        Args:
            file_path: Path to MATLAB file

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

        functions = self._extract_functions(content)
        classes = self._extract_classes(content)
        entry_points = self._extract_entry_points(content, functions)

        return {
            "imports": [],  # MATLAB doesn't have explicit imports in the file
            "functions": functions,
            "classes": classes,
            "entry_points": entry_points,
        }

    def _remove_comments(self, content: str) -> str:
        """Remove MATLAB comments."""
        # Remove single-line comments (% comment)
        content = re.sub(r"%.*", "", content)
        # Remove block comments (%{ ... %})
        content = re.sub(r"%\{.*?%\}", "", content, flags=re.DOTALL)
        return content

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        
        # function [output1, output2] = function_name(input1, input2)
        # function function_name(input1, input2)
        pattern = r"function\s+(?:\[[^\]]+\]\s*=\s*)?(\w+)\s*\([^)]*\)"
        for match in re.finditer(pattern, content, re.MULTILINE):
            func_name = match.group(1)
            full_match = match.group(0)
            
            # Check if it's a method (inside a classdef block)
            is_method = False
            # Simple check: if function appears after classdef in file
            func_pos = content.find(full_match)
            if func_pos > 0:
                before_func = content[:func_pos]
                if "classdef" in before_func:
                    is_method = True
            
            functions.append({
                "name": func_name,
                "is_method": is_method,
            })
        
        return functions

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        classes = []
        
        # classdef ClassName < handle
        # classdef ClassName
        pattern = r"classdef\s+(\w+)(?:\s*<\s*([^\s]+))?"
        for match in re.finditer(pattern, content, re.MULTILINE):
            class_name = match.group(1)
            superclass = match.group(2) if match.group(2) else None
            
            classes.append({
                "name": class_name,
                "type": "class",
                "superclass": superclass,
            })
        
        return classes

    def _extract_entry_points(self, content: str, functions: List[Dict[str, Any]]) -> List[str]:
        """
        Extract entry points.
        
        In MATLAB, entry points can be:
        - Script files (files without function definitions)
        - Main functions (typically named 'main' or the file name)
        """
        entry_points = []
        
        # Check if it's a script (no function definitions at top level)
        if not functions:
            # Script file - entire file is entry point
            entry_points.append("script")
        else:
            # Check for main function
            for func in functions:
                func_name = func["name"]
                # Check if function name matches file name (common MATLAB pattern)
                # Or if it's explicitly named 'main'
                if func_name == "main":
                    entry_points.append("main")
                    break
        
        return entry_points


def analyze_matlab_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a MATLAB file.

    Args:
        file_path: Path to MATLAB file

    Returns:
        Dictionary with extracted information
    """
    analyzer = MATLABAnalyzer()
    return analyzer.analyze_file(file_path)

