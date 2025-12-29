"""
HTML file analyzer.

Extracts structure from HTML files including tags, links, scripts, forms, etc.
"""

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Set


class HTMLStructureParser(HTMLParser):
    """HTML parser for extracting structure."""

    def __init__(self):
        super().__init__()
        self.tags: List[Dict[str, Any]] = []
        self.links: List[Dict[str, Any]] = []
        self.scripts: List[Dict[str, Any]] = []
        self.stylesheets: List[Dict[str, Any]] = []
        self.forms: List[Dict[str, Any]] = []
        self.meta_tags: List[Dict[str, Any]] = []
        self.headings: List[Dict[str, Any]] = []
        self.images: List[Dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list):
        """Handle opening tags."""
        attrs_dict = dict(attrs)
        tag_info = {"tag": tag, "attributes": attrs_dict}
        self.tags.append(tag_info)

        # Extract specific elements
        if tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            is_internal = not href.startswith(("http://", "https://", "mailto:", "ftp://", "#"))
            self.links.append(
                {
                    "text": "",  # Will be filled by handle_data
                    "url": href,
                    "is_internal": is_internal,
                }
            )
        elif tag == "script":
            src = attrs_dict.get("src", "")
            script_type = attrs_dict.get("type", "text/javascript")
            self.scripts.append({"src": src, "type": script_type})
        elif tag == "link" and attrs_dict.get("rel") == "stylesheet":
            href = attrs_dict.get("href", "")
            self.stylesheets.append({"href": href})
        elif tag == "form":
            action = attrs_dict.get("action", "")
            method = attrs_dict.get("method", "get")
            self.forms.append({"action": action, "method": method})
        elif tag == "meta":
            self.meta_tags.append(attrs_dict)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.headings.append({"level": level, "text": ""})
        elif tag == "img":
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "")
            self.images.append({"src": src, "alt": alt})

    def handle_data(self, data: str):
        """Handle text data between tags."""
        # Try to associate data with the last link or heading
        if self.links and data.strip():
            self.links[-1]["text"] = data.strip()
        if self.headings and data.strip():
            self.headings[-1]["text"] = data.strip()


class HTMLAnalyzer:
    """Analyzer for HTML files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze an HTML file and extract its structure.

        Args:
            file_path: Path to HTML file

        Returns:
            Dictionary with extracted information
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return {
                "tags": [],
                "links": [],
                "scripts": [],
                "stylesheets": [],
                "forms": [],
                "meta_tags": [],
                "headings": [],
                "images": [],
                "errors": ["Could not read file"],
            }

        parser = HTMLStructureParser()
        try:
            parser.feed(content)
        except Exception as e:
            return {
                "tags": parser.tags,
                "links": parser.links,
                "scripts": parser.scripts,
                "stylesheets": parser.stylesheets,
                "forms": parser.forms,
                "meta_tags": parser.meta_tags,
                "headings": parser.headings,
                "images": parser.images,
                "errors": [str(e)],
            }

        # Extract unique tag types
        tag_types = list(set(tag["tag"] for tag in parser.tags))

        return {
            "tags": parser.tags[:100],  # Limit to first 100 tags
            "tag_types": tag_types,
            "links": parser.links,
            "scripts": parser.scripts,
            "stylesheets": parser.stylesheets,
            "forms": parser.forms,
            "meta_tags": parser.meta_tags,
            "headings": parser.headings,
            "images": parser.images,
        }


def analyze_html_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze an HTML file.

    Args:
        file_path: Path to HTML file

    Returns:
        Dictionary with extracted information
    """
    analyzer = HTMLAnalyzer()
    return analyzer.analyze_file(file_path)

