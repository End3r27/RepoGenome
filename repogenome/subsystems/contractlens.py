"""
ContractLens subsystem - Public API contract analysis.

Identifies public APIs and calculates breaking change risks.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from repogenome.core.schema import Contract
from repogenome.subsystems.base import Subsystem


class ContractLens(Subsystem):
    """Public API contract analysis."""

    def __init__(self):
        """Initialize ContractLens."""
        super().__init__("contractlens")
        self.depends_on_subsystems = ["repospider"]

    def analyze(
        self, repo_path: Path, existing_genome: Optional[Dict[str, Any]] = None, progress: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze public API contracts.

        Args:
            repo_path: Path to repository root
            existing_genome: Optional existing genome

        Returns:
            Dictionary with contracts
        """
        contracts: Dict[str, Contract] = {}

        if not existing_genome:
            return {"contracts": {}}

        nodes = existing_genome.get("nodes", {})
        edges = existing_genome.get("edges", [])

        # Identify public APIs
        public_apis = self._identify_public_apis(nodes, edges)

        # Calculate breaking change risk for each contract
        for api_id, api_data in public_apis.items():
            # Find dependencies
            dependencies = self._find_dependencies(api_id, edges)

            # Calculate risk based on number of dependents
            fan_in = self._calculate_fan_in(api_id, edges)
            breaking_risk = min(1.0, fan_in / 10.0)  # Normalize to 0-1

            contracts[api_id] = Contract(
                depends_on=dependencies,
                breaking_change_risk=breaking_risk,
            )

        return {"contracts": {k: v.model_dump() for k, v in contracts.items()}}

    def _identify_public_apis(
        self, nodes: Dict[str, Any], edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identify public API endpoints and exported functions."""
        public_apis: Dict[str, Any] = {}

        for node_id, node_data in nodes.items():
            # Check if node is public
            visibility = node_data.get("visibility", "private")
            node_type = node_data.get("type")

            # API routes are public by definition
            if node_type == "function":
                file_path = node_data.get("file", "")
                # Check if it's an API route (simplified heuristic)
                if any(
                    keyword in node_id.lower()
                    for keyword in ["route", "endpoint", "handler", "api"]
                ):
                    public_apis[node_id] = node_data

            # Exported/public functions in main modules
            if visibility == "public" and node_type in ["function", "class"]:
                file_path = node_data.get("file", "")
                # Check if file suggests public API
                if any(
                    keyword in file_path.lower()
                    for keyword in ["api", "public", "export", "interface"]
                ):
                    public_apis[node_id] = node_data

        return public_apis

    def _find_dependencies(
        self, api_id: str, edges: List[Dict[str, Any]]
    ) -> List[str]:
        """Find nodes that this API depends on."""
        dependencies: set = set()

        for edge in edges:
            edge_from = edge.get("from") or edge.get("from_")
            edge_type = edge.get("type")

            if edge_from == api_id and edge_type in ["calls", "imports"]:
                dependencies.add(edge.get("to"))

        return list(dependencies)

    def _calculate_fan_in(self, node_id: str, edges: List[Dict[str, Any]]) -> int:
        """Calculate fan-in (number of incoming edges)."""
        count = 0

        for edge in edges:
            edge_to = edge.get("to")
            edge_type = edge.get("type")

            if edge_to == node_id and edge_type in ["calls", "imports"]:
                count += 1

        return count

