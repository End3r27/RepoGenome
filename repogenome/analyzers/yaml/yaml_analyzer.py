"""
YAML file analyzer.

Extracts structure from YAML files including keys, types, and nested structure.
"""

from pathlib import Path
from typing import Any, Dict, List, Union

try:
    import yaml
except ImportError:
    yaml = None


class YAMLAnalyzer:
    """Analyzer for YAML files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a YAML file and extract its structure.

        Args:
            file_path: Path to YAML file

        Returns:
            Dictionary with extracted information
        """
        if yaml is None:
            return {
                "keys": [],
                "structure": {},
                "type": "error",
                "errors": ["PyYAML not installed"],
            }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return {
                "keys": [],
                "structure": {},
                "type": "error",
                "errors": [f"YAML parse error: {e}"],
            }
        except Exception as e:
            return {
                "keys": [],
                "structure": {},
                "type": "error",
                "errors": [f"Could not read file: {e}"],
            }

        if data is None:
            return {
                "keys": [],
                "structure": {},
                "type": "null",
            }

        yaml_type = (
            "array"
            if isinstance(data, list)
            else "object"
            if isinstance(data, dict)
            else "value"
        )
        keys = self._extract_keys(data)
        structure = self._extract_structure(data)
        anchors = self._extract_anchors(file_path)

        return {
            "keys": keys,
            "structure": structure,
            "type": yaml_type,
            "anchors": anchors,
            "size": len(data) if isinstance(data, (list, dict)) else 1,
        }

    def _extract_keys(self, data: Union[dict, list, Any]) -> List[str]:
        """Extract top-level keys or array metadata."""
        if isinstance(data, dict):
            return list(data.keys())
        elif isinstance(data, list):
            if len(data) > 0:
                first_item = data[0]
                if isinstance(first_item, dict):
                    return list(first_item.keys())
            return []
        return []

    def _extract_structure(
        self, data: Union[dict, list, Any], max_depth: int = 5, current_depth: int = 0
    ) -> Dict[str, Any]:
        """
        Extract structure metadata from YAML data.

        Args:
            data: YAML data to analyze
            max_depth: Maximum depth to analyze
            current_depth: Current depth in recursion

        Returns:
            Dictionary with structure information
        """
        if current_depth >= max_depth:
            return {"type": "truncated"}

        if isinstance(data, dict):
            structure = {
                "type": "object",
                "keys": list(data.keys()),
                "count": len(data),
                "properties": {},
            }
            for key, value in data.items():
                structure["properties"][key] = self._extract_structure(
                    value, max_depth, current_depth + 1
                )
            return structure
        elif isinstance(data, list):
            structure = {
                "type": "array",
                "count": len(data),
                "item_type": "mixed",
            }
            if len(data) > 0:
                item_types = set()
                for item in data[:5]:
                    item_type = type(item).__name__
                    item_types.add(item_type)
                    if len(item_types) > 1:
                        break
                if len(item_types) == 1:
                    structure["item_type"] = list(item_types)[0]
                    if data:
                        structure["item_structure"] = self._extract_structure(
                            data[0], max_depth, current_depth + 1
                        )
            return structure
        else:
            return {"type": type(data).__name__, "value": str(data)[:50]}

    def _extract_anchors(self, file_path: Path) -> List[str]:
        """
        Extract YAML anchors and aliases from file.

        Args:
            file_path: Path to YAML file

        Returns:
            List of anchor names found
        """
        anchors = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Match anchors: &anchor_name
                import re
                pattern = r"&\s*(\w+)"
                for match in re.finditer(pattern, content):
                    anchors.append(match.group(1))
        except Exception:
            pass
        return anchors


def analyze_yaml_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Dictionary with extracted information
    """
    analyzer = YAMLAnalyzer()
    return analyzer.analyze_file(file_path)

