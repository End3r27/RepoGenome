"""
Shell script analyzer.

Extracts structure from shell scripts including functions, variables, commands, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class ShellAnalyzer:
    """Analyzer for shell script files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a shell script file and extract its structure.

        Args:
            file_path: Path to shell script file

        Returns:
            Dictionary with extracted information
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return {
                "functions": [],
                "variables": [],
                "commands": [],
                "conditionals": [],
                "loops": [],
                "shebang": None,
                "errors": ["Could not read file"],
            }

        shebang = self._extract_shebang(content)
        functions = self._extract_functions(content)
        variables = self._extract_variables(content)
        commands = self._extract_commands(content)
        conditionals = self._extract_conditionals(content)
        loops = self._extract_loops(content)

        return {
            "functions": functions,
            "variables": variables,
            "commands": commands,
            "conditionals": conditionals,
            "loops": loops,
            "shebang": shebang,
        }

    def _extract_shebang(self, content: str) -> str:
        """Extract shebang line."""
        lines = content.split("\n")
        if lines and lines[0].startswith("#!"):
            return lines[0].strip()
        return ""

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        functions = []
        # Bash/Zsh function syntax: function_name() { or function function_name() {
        patterns = [
            r"^\s*(\w+)\s*\(\s*\)\s*\{",  # name() {
            r"^\s*function\s+(\w+)\s*\([^)]*\)\s*\{",  # function name() {
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                func_name = match.group(1)
                functions.append({"name": func_name})
        return functions

    def _extract_variables(self, content: str) -> List[Dict[str, Any]]:
        """Extract variable definitions."""
        variables = []
        # Match variable assignments: VAR=value or export VAR=value or declare VAR=value
        patterns = [
            r"^\s*(?:export\s+|declare\s+)?(\w+)=([^#\n]+)",  # VAR=value
            r"^\s*local\s+(\w+)=([^#\n]+)",  # local VAR=value
            r"^\s*readonly\s+(\w+)=([^#\n]+)",  # readonly VAR=value
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                var_name = match.group(1)
                var_value = match.group(2).strip() if len(match.groups()) > 1 else ""
                variables.append({"name": var_name, "value": var_value[:50]})
        return variables

    def _extract_commands(self, content: str) -> List[Dict[str, Any]]:
        """Extract command invocations."""
        commands = []
        # Common commands (simplified - could be expanded)
        common_commands = [
            "echo", "cat", "grep", "find", "sed", "awk", "curl", "wget",
            "git", "npm", "pip", "python", "node", "docker", "kubectl",
        ]
        for cmd in common_commands:
            pattern = rf"\b{re.escape(cmd)}\s+([^\n;|&]+)"
            for match in re.finditer(pattern, content, re.IGNORECASE):
                args = match.group(1).strip()[:100]
                commands.append({"command": cmd, "args": args})
        return commands[:50]  # Limit to first 50

    def _extract_conditionals(self, content: str) -> List[Dict[str, Any]]:
        """Extract conditional statements."""
        conditionals = []
        # if statements
        if_pattern = r"^\s*if\s+(.+?)\s*;\s*then"
        for match in re.finditer(if_pattern, content, re.MULTILINE):
            condition = match.group(1).strip()
            conditionals.append({"type": "if", "condition": condition[:100]})
        return conditionals

    def _extract_loops(self, content: str) -> List[Dict[str, Any]]:
        """Extract loop statements."""
        loops = []
        # for loops: for var in ...; do
        for_pattern = r"^\s*for\s+(\w+)\s+in\s+(.+?)\s*;\s*do"
        for match in re.finditer(for_pattern, content, re.MULTILINE):
            var = match.group(1)
            items = match.group(2).strip()
            loops.append({"type": "for", "variable": var, "items": items[:100]})

        # while loops: while condition; do
        while_pattern = r"^\s*while\s+(.+?)\s*;\s*do"
        for match in re.finditer(while_pattern, content, re.MULTILINE):
            condition = match.group(1).strip()
            loops.append({"type": "while", "condition": condition[:100]})
        return loops


def analyze_shell_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a shell script file.

    Args:
        file_path: Path to shell script file

    Returns:
        Dictionary with extracted information
    """
    analyzer = ShellAnalyzer()
    return analyzer.analyze_file(file_path)

