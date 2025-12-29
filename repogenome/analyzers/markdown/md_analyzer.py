"""
Markdown file analyzer.

Extracts structure from Markdown files including headings, links, code blocks, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class MarkdownAnalyzer:
    """Analyzer for Markdown files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Markdown file and extract its structure.

        Args:
            file_path: Path to Markdown file

        Returns:
            Dictionary with extracted information
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return {
                "headings": [],
                "links": [],
                "code_blocks": [],
                "images": [],
                "lists": [],
                "blockquotes": [],
                "errors": ["Could not read file"],
            }

        headings = self._extract_headings(content)
        links = self._extract_links(content)
        code_blocks = self._extract_code_blocks(content)
        images = self._extract_images(content)
        lists = self._extract_lists(content)
        blockquotes = self._extract_blockquotes(content)

        return {
            "headings": headings,
            "links": links,
            "code_blocks": code_blocks,
            "images": images,
            "lists": lists,
            "blockquotes": blockquotes,
        }

    def _extract_headings(self, content: str) -> List[Dict[str, Any]]:
        """Extract headings with their level and text."""
        headings = []
        # Match ATX headings (# ## ### etc.)
        atx_pattern = r"^(#{1,6})\s+(.+)$"
        for match in re.finditer(atx_pattern, content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({"level": level, "text": text, "type": "atx"})

        # Match Setext headings (=== and ---)
        setext_pattern = r"^(.+)\n(={3,}|-{3,})$"
        for match in re.finditer(setext_pattern, content, re.MULTILINE):
            text = match.group(1).strip()
            level = 1 if match.group(2).startswith("=") else 2
            headings.append({"level": level, "text": text, "type": "setext"})

        return headings

    def _extract_links(self, content: str) -> List[Dict[str, Any]]:
        """Extract links (both inline and reference style)."""
        links = []
        # Inline links: [text](url)
        inline_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(inline_pattern, content):
            text = match.group(1)
            url = match.group(2)
            is_internal = not url.startswith(("http://", "https://", "mailto:", "ftp://"))
            links.append(
                {"text": text, "url": url, "type": "inline", "is_internal": is_internal}
            )

        # Reference links: [text][ref] or [text]
        ref_pattern = r"\[([^\]]+)\](?:\[([^\]]+)\])?"
        ref_def_pattern = r"^\s*\[([^\]]+)\]:\s*(.+)$"
        ref_defs = {}
        for match in re.finditer(ref_def_pattern, content, re.MULTILINE):
            ref_defs[match.group(1)] = match.group(2).strip()

        for match in re.finditer(ref_pattern, content):
            text = match.group(1)
            ref = match.group(2) or text
            if ref in ref_defs:
                url = ref_defs[ref]
                is_internal = not url.startswith(("http://", "https://", "mailto:", "ftp://"))
                links.append(
                    {
                        "text": text,
                        "url": url,
                        "type": "reference",
                        "is_internal": is_internal,
                    }
                )

        return links

    def _extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract code blocks with language detection."""
        code_blocks = []
        # Fenced code blocks: ```language or ``````
        fenced_pattern = r"```(\w+)?\n(.*?)```"
        for match in re.finditer(fenced_pattern, content, re.DOTALL):
            language = match.group(1) or "unknown"
            code = match.group(2).strip()
            code_blocks.append({"language": language, "code": code[:100], "type": "fenced"})

        # Indented code blocks (4 spaces or 1 tab)
        # This is more complex, so we'll skip it for now or do a simplified version

        return code_blocks

    def _extract_images(self, content: str) -> List[Dict[str, Any]]:
        """Extract images."""
        images = []
        # Inline images: ![alt](url)
        pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
        for match in re.finditer(pattern, content):
            alt = match.group(1)
            url = match.group(2)
            is_internal = not url.startswith(("http://", "https://"))
            images.append({"alt": alt, "url": url, "is_internal": is_internal})

        return images

    def _extract_lists(self, content: str) -> List[Dict[str, Any]]:
        """Extract lists (ordered and unordered)."""
        lists = []
        # Unordered lists: - * +
        unordered_pattern = r"^(\s*)([-*+])\s+(.+)$"
        for match in re.finditer(unordered_pattern, content, re.MULTILINE):
            indent = len(match.group(1))
            text = match.group(3).strip()
            lists.append({"text": text, "type": "unordered", "indent": indent})

        # Ordered lists: 1. 2. etc.
        ordered_pattern = r"^(\s*)(\d+\.)\s+(.+)$"
        for match in re.finditer(ordered_pattern, content, re.MULTILINE):
            indent = len(match.group(1))
            text = match.group(3).strip()
            lists.append({"text": text, "type": "ordered", "indent": indent})

        return lists

    def _extract_blockquotes(self, content: str) -> List[Dict[str, Any]]:
        """Extract blockquotes."""
        blockquotes = []
        # Blockquotes: > text
        pattern = r"^>\s+(.+)$"
        for match in re.finditer(pattern, content, re.MULTILINE):
            text = match.group(1).strip()
            blockquotes.append({"text": text})

        return blockquotes


def analyze_markdown_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a Markdown file.

    Args:
        file_path: Path to Markdown file

    Returns:
        Dictionary with extracted information
    """
    analyzer = MarkdownAnalyzer()
    return analyzer.analyze_file(file_path)

