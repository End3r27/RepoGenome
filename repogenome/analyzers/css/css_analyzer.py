"""
CSS file analyzer.

Extracts structure from CSS files including selectors, rules, media queries, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class CSSAnalyzer:
    """Analyzer for CSS files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a CSS file and extract its structure.

        Args:
            file_path: Path to CSS file

        Returns:
            Dictionary with extracted information
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return {
                "selectors": [],
                "rules": [],
                "media_queries": [],
                "keyframes": [],
                "imports": [],
                "errors": ["Could not read file"],
            }

        # Remove comments first
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        selectors = self._extract_selectors(content)
        rules = self._extract_rules(content)
        media_queries = self._extract_media_queries(content)
        keyframes = self._extract_keyframes(content)
        imports = self._extract_imports(content)
        urls = self._extract_urls(content)

        return {
            "selectors": selectors,
            "rules": rules,
            "media_queries": media_queries,
            "keyframes": keyframes,
            "imports": imports,
            "urls": urls,
        }

    def _extract_selectors(self, content: str) -> List[Dict[str, Any]]:
        """Extract CSS selectors."""
        selectors = []
        # Match CSS selectors (before {)
        # This is a simplified version - real CSS parsing is more complex
        pattern = r"([^{]+)\{"
        for match in re.finditer(pattern, content):
            selector_text = match.group(1).strip()
            # Split multiple selectors
            for selector in selector_text.split(","):
                selector = selector.strip()
                if selector:
                    selector_type = self._classify_selector(selector)
                    selectors.append(
                        {
                            "selector": selector,
                            "type": selector_type,
                        }
                    )
        return selectors

    def _classify_selector(self, selector: str) -> str:
        """Classify selector type."""
        selector = selector.strip()
        if selector.startswith("."):
            return "class"
        elif selector.startswith("#"):
            return "id"
        elif selector.startswith("@"):
            return "at-rule"
        elif ":" in selector or "::" in selector:
            return "pseudo"
        elif " " in selector or ">" in selector or "+" in selector or "~" in selector:
            return "compound"
        else:
            return "element"

    def _extract_rules(self, content: str) -> List[Dict[str, Any]]:
        """Extract CSS rules (property: value pairs)."""
        rules = []
        # Match rules inside braces: property: value;
        pattern = r"\{([^}]+)\}"
        for match in re.finditer(pattern, content):
            rules_text = match.group(1)
            # Extract individual rules
            rule_pattern = r"([^:;]+):\s*([^;]+);"
            for rule_match in re.finditer(rule_pattern, rules_text):
                property_name = rule_match.group(1).strip()
                value = rule_match.group(2).strip()
                rules.append({"property": property_name, "value": value})
        return rules

    def _extract_media_queries(self, content: str) -> List[Dict[str, Any]]:
        """Extract media queries."""
        media_queries = []
        pattern = r"@media\s+([^{]+)\{"
        for match in re.finditer(pattern, content, re.IGNORECASE):
            query = match.group(1).strip()
            media_queries.append({"query": query})
        return media_queries

    def _extract_keyframes(self, content: str) -> List[Dict[str, Any]]:
        """Extract @keyframes animations."""
        keyframes = []
        pattern = r"@keyframes\s+(\w+)\s*\{"
        for match in re.finditer(pattern, content, re.IGNORECASE):
            name = match.group(1)
            keyframes.append({"name": name})
        return keyframes

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract @import statements."""
        imports = []
        pattern = r"@import\s+(?:url\()?['\"]?([^'\")]+)['\"]?\)?;"
        for match in re.finditer(pattern, content, re.IGNORECASE):
            url = match.group(1)
            imports.append({"url": url})
        return imports

    def _extract_urls(self, content: str) -> List[str]:
        """Extract URLs from url() functions."""
        urls = []
        pattern = r"url\(['\"]?([^'\")]+)['\"]?\)"
        for match in re.finditer(pattern, content, re.IGNORECASE):
            url = match.group(1)
            urls.append(url)
        return urls


def analyze_css_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a CSS file.

    Args:
        file_path: Path to CSS file

    Returns:
        Dictionary with extracted information
    """
    analyzer = CSSAnalyzer()
    return analyzer.analyze_file(file_path)

