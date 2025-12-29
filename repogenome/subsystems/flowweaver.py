"""
FlowWeaver subsystem - Runtime execution path analysis.

Traces runtime execution paths and identifies side effects.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from repogenome.analyzers.python.ast_analyzer import analyze_python_file
from repogenome.core.schema import Flow
from repogenome.subsystems.base import Subsystem


class FlowWeaver(Subsystem):
    """Trace runtime execution paths and side effects."""

    def __init__(self):
        """Initialize FlowWeaver."""
        super().__init__("flowweaver")
        self.required_analyzers = ["python", "typescript"]
        self.depends_on_subsystems = ["repospider"]

    def analyze(
        self, repo_path: Path, existing_genome: Optional[Dict[str, Any]] = None, progress: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze runtime flows.

        Args:
            repo_path: Path to repository root
            existing_genome: Optional existing genome (needed for nodes/edges)

        Returns:
            Dictionary with flows
        """
        flows: List[Flow] = []

        if not existing_genome:
            return {"flows": []}

        nodes = existing_genome.get("nodes", {})
        edges = existing_genome.get("edges", [])
        entry_points = existing_genome.get("summary", {}).get(
            "entry_points", []
        )

        # Build call graph from edges
        call_graph = self._build_call_graph(edges, nodes)

        # Analyze each entry point
        for entry_point in entry_points:
            entry_flows = self._trace_from_entry(
                repo_path, entry_point, call_graph, nodes
            )
            flows.extend(entry_flows)

        return {"flows": [f.model_dump() for f in flows]}

    def _build_call_graph(
        self, edges: List[Dict[str, Any]], nodes: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Build call graph from edges."""
        graph: Dict[str, List[str]] = {}

        for edge in edges:
            edge_type = edge.get("type")
            if edge_type == "calls":
                from_node = edge.get("from") or edge.get("from_")
                to_node = edge.get("to")
                if from_node and to_node:
                    if from_node not in graph:
                        graph[from_node] = []
                    graph[from_node].append(to_node)

        return graph

    def _trace_from_entry(
        self,
        repo_path: Path,
        entry_point: str,
        call_graph: Dict[str, List[str]],
        nodes: Dict[str, Any],
    ) -> List[Flow]:
        """Trace execution flow from an entry point."""
        flows: List[Flow] = []
        visited: Set[str] = set()

        def dfs(node_id: str, path: List[str], side_effects: Set[str]):
            """Depth-first search to trace execution."""
            if node_id in visited:
                return
            visited.add(node_id)

            node = nodes.get(node_id)
            if not node:
                return

            current_path = path + [node_id]

            # Detect side effects in current node
            node_file = node.get("file")
            if node_file:
                file_side_effects = self._detect_side_effects(
                    repo_path / node_file
                )
                side_effects.update(file_side_effects)

            # If this is a terminal node or no outgoing calls, create flow
            if node_id not in call_graph or not call_graph[node_id]:
                flows.append(
                    Flow(
                        entry=entry_point,
                        path=current_path,
                        side_effects=list(side_effects),
                        confidence=0.8,  # Static analysis confidence
                    )
                )
            else:
                # Continue tracing
                for callee in call_graph[node_id]:
                    dfs(callee, current_path, side_effects.copy())

        # Start from entry point
        entry_node_id = entry_point
        dfs(entry_node_id, [], set())

        return flows

    def _detect_side_effects(self, file_path: Path) -> Set[str]:
        """
        Detect side effects in a file (simplified heuristic-based).

        Args:
            file_path: Path to file

        Returns:
            Set of side effect types
        """
        side_effects: Set[str] = set()

        if not file_path.exists():
            return side_effects

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return side_effects

        # Pattern-based detection (simplified)
        patterns = {
            "db.read": [
                r"\.query\(|\.find\(|\.get\(|SELECT\s+.*FROM",
                r"db\.(get|find|query|select)",
            ],
            "db.write": [
                r"\.(save|insert|update|delete|create|commit)\(|INSERT\s+INTO|UPDATE\s+|DELETE\s+FROM",
                r"db\.(save|insert|update|delete|create|commit)",
            ],
            "file.read": [
                r"open\([^)]+['\"]r['\"]|read\(|\.read_file",
                r"open\(.*['\"]r['\"]",
            ],
            "file.write": [
                r"open\([^)]+['\"]w['\"]|write\(|\.write_file",
                r"open\(.*['\"]w['\"]",
            ],
            "network": [
                r"requests\.(get|post|put|delete)|fetch\(|\.http",
                r"requests\.|fetch\(",
            ],
            "log": [
                r"\.(log|info|warning|error|debug)\(",
                r"logging\.|logger\.",
            ],
        }

        for effect_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, content, re.IGNORECASE):
                    side_effects.add(effect_type)
                    break

        return side_effects

