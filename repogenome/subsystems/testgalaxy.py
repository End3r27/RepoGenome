"""
TestGalaxy subsystem - Test coverage analysis.

Identifies test files, maps tests to code, and calculates coverage.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from repogenome.core.schema import Edge, EdgeType, Node, NodeType, Tests
from repogenome.subsystems.base import Subsystem


class TestGalaxy(Subsystem):
    """Test coverage analysis (optional subsystem)."""

    def __init__(self):
        """Initialize TestGalaxy."""
        super().__init__("testgalaxy")
        self.is_required = False
        self.depends_on_subsystems = ["repospider"]

    def analyze(
        self, repo_path: Path, existing_genome: Optional[Dict[str, Any]] = None, progress: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze test files and coverage.

        Args:
            repo_path: Path to repository root
            existing_genome: Optional existing genome

        Returns:
            Dictionary with test data
        """
        test_files: List[str] = []
        test_nodes: Dict[str, Node] = {}
        test_edges: List[Edge] = []

        if not existing_genome:
            return {"tests": None}

        nodes = existing_genome.get("nodes", {})

        # Find test files
        test_patterns = [
            "test_*.py",
            "*_test.py",
            "*.test.ts",
            "*.test.js",
            "*.spec.ts",
            "*.spec.js",
            "__tests__/*.ts",
            "__tests__/*.js",
            "tests/**/*.py",
        ]

        for pattern in test_patterns:
            test_files.extend(list(repo_path.rglob(pattern)))

        # Filter out non-test directories
        test_files = [
            f
            for f in test_files
            if not any(
                part in str(f)
                for part in [".git", "__pycache__", "node_modules", ".venv"]
            )
        ]

        # Extract test functions from test files
        for test_file in test_files:
            rel_path = str(test_file.relative_to(repo_path))
            language = self._detect_language(test_file)

            # Add test file node if not already present
            if rel_path not in nodes:
                test_nodes[rel_path] = Node(
                    type=NodeType.TEST,
                    file=rel_path,
                    language=language,
                    visibility="public",
                )

            # Extract test functions
            test_functions = self._extract_test_functions(test_file, language)
            for test_func in test_functions:
                test_func_id = f"{rel_path}.{test_func}"
                test_nodes[test_func_id] = Node(
                    type=NodeType.FUNCTION,
                    file=rel_path,
                    language=language,
                    visibility="public",
                )

                # Try to map test to code under test
                tested_code = self._find_tested_code(
                    test_func, rel_path, nodes, repo_path
                )
                for code_id in tested_code:
                    test_edges.append(
                        Edge(
                            from_=test_func_id,
                            to=code_id,
                            type=EdgeType.TESTS,
                        )
                    )

        # Try to load coverage data if available
        coverage = self._load_coverage_data(repo_path)

        tests_data = Tests(
            coverage=coverage,
            test_files=[str(f.relative_to(repo_path)) for f in test_files],
        )

        return {
            "test_nodes": {k: v.model_dump() for k, v in test_nodes.items()},
            "test_edges": [e.model_dump(by_alias=True) for e in test_edges],
            "tests": tests_data.model_dump(),
        }

    def _detect_language(self, file_path: Path) -> str:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        if ext == ".py":
            return "Python"
        elif ext in [".ts", ".js"]:
            return "TypeScript" if ext == ".ts" else "JavaScript"
        return "Unknown"

    def _extract_test_functions(self, test_file: Path, language: str) -> List[str]:
        """Extract test function names from a test file."""
        test_functions: List[str] = []

        try:
            with open(test_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return test_functions

        if language == "Python":
            # Match test functions: def test_*, def Test*::test_*
            patterns = [
                r"def\s+(test_\w+)",
                r"def\s+(\w+)\s*\([^)]*self[^)]*\)",  # Methods in Test classes
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    func_name = match.group(1)
                    if func_name.startswith("test_") or "test" in func_name.lower():
                        test_functions.append(func_name)

        elif language in ["TypeScript", "JavaScript"]:
            # Match: test('name', ...), it('name', ...), describe('name', ...)
            patterns = [
                r"(?:test|it|describe)\(['\"]([^'\"]+)['\"]",
                r"(?:test|it|describe)\(`([^`]+)`",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    test_functions.append(match.group(1))

        return test_functions

    def _find_tested_code(
        self,
        test_func: str,
        test_file: str,
        nodes: Dict[str, Any],
        repo_path: Path,
    ) -> List[str]:
        """Find code that a test function likely tests."""
        tested_code: List[str] = []

        # Heuristic: test functions often import or reference the code they test
        # This is simplified - full implementation would analyze imports and calls

        # Extract module name from test file name
        test_base = Path(test_file).stem
        if test_base.startswith("test_"):
            module_name = test_base[5:]  # Remove "test_" prefix
        elif test_base.endswith("_test"):
            module_name = test_base[:-5]  # Remove "_test" suffix
        else:
            module_name = test_base

        # Find matching nodes
        for node_id, node_data in nodes.items():
            node_file = node_data.get("file", "")
            if module_name in node_file:
                tested_code.append(node_id)

        return tested_code

    def _load_coverage_data(self, repo_path: Path) -> Optional[Dict[str, float]]:
        """Try to load coverage data from coverage.json or similar."""
        coverage_files = [
            repo_path / "coverage.json",
            repo_path / ".coverage.json",
            repo_path / "coverage" / "coverage.json",
        ]

        for cov_file in coverage_files:
            if cov_file.exists():
                try:
                    import json

                    with open(cov_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Parse coverage data (format varies by tool)
                        # This is a placeholder - would need tool-specific parsing
                        return None
                except Exception:
                    pass

        return None

