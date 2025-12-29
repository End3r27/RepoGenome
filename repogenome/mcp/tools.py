"""MCP tool implementations for RepoGenome."""

from typing import Any, Dict, List, Optional

from repogenome.core.generator import RepoGenomeGenerator
from repogenome.core.query import GenomeQuery, parse_simple_query
from repogenome.mcp.storage import GenomeStorage


class RepoGenomeTools:
    """Handles MCP tools for RepoGenome."""

    def __init__(self, storage: GenomeStorage, repo_path: str):
        """
        Initialize tool handlers.

        Args:
            storage: GenomeStorage instance
            repo_path: Path to repository root
        """
        self.storage = storage
        self.repo_path = repo_path

    def scan(
        self, scope: str = "full", incremental: bool = True
    ) -> Dict[str, Any]:
        """
        Scan repository and generate RepoGenome.

        Args:
            scope: Scan scope ("full", "structure", "flows", "history")
            incremental: Use incremental update if possible

        Returns:
            Result dict with success status and message
        """
        try:
            from pathlib import Path

            generator = RepoGenomeGenerator(Path(self.repo_path))

            # Determine which subsystems to enable based on scope
            if scope == "structure":
                enabled_subsystems = ["repospider"]
            elif scope == "flows":
                enabled_subsystems = ["repospider", "flowweaver"]
            elif scope == "history":
                enabled_subsystems = ["repospider", "chronomap"]
            else:  # full
                enabled_subsystems = None

            generator.subsystems = {
                k: v
                for k, v in generator.subsystems.items()
                if enabled_subsystems is None or k in enabled_subsystems
            }

            # Check if incremental update is possible
            existing_genome = self.storage.load_genome()
            if incremental and existing_genome and not self.storage.is_stale():
                genome = generator.generate(
                    incremental=True,
                    existing_genome_path=self.storage.genome_path,
                )
            else:
                genome = generator.generate(incremental=False)

            # Save genome
            self.storage.save_genome(genome)

            return {
                "success": True,
                "message": f"Genome generated successfully ({scope} scan)",
                "nodes": len(genome.nodes),
                "edges": len(genome.edges),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def query(self, query: str, format: str = "json") -> Dict[str, Any]:
        """
        Query RepoGenome graph.

        Args:
            query: Query string (natural language or structured)
            format: Output format ("json" or "graph")

        Returns:
            Query results
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        try:
            query_obj = GenomeQuery(genome)

            # Try to parse as structured query
            parsed = parse_simple_query(query)
            if parsed:
                if parsed.get("type") == "nodes":
                    results = query_obj.query_nodes(parsed.get("filters", {}))
                    return {
                        "type": "nodes",
                        "count": len(results),
                        "results": [
                            {
                                "id": node_id,
                                **(node_data.model_dump() if hasattr(node_data, 'model_dump') else (node_data if isinstance(node_data, dict) else {}))
                            }
                            for node_id, node_data in results
                        ],
                    }
            else:
                # Natural language query - simple keyword matching
                query_lower = query.lower()
                results = []

                # Search in nodes
                for node_id, node_data in genome.nodes.items():
                    # Convert Pydantic model to dict if needed
                    if hasattr(node_data, 'model_dump'):
                        node_dict = node_data.model_dump()
                    elif hasattr(node_data, 'dict'):
                        node_dict = node_data.dict()
                    else:
                        node_dict = node_data if isinstance(node_data, dict) else {}
                    
                    summary = node_dict.get('summary', '') or ''
                    file_path = node_dict.get('file', '') or ''
                    node_str = f"{node_id} {summary} {file_path}".lower()
                    if any(word in node_str for word in query_lower.split()):
                        results.append({"id": node_id, **node_dict})

                # Search in concepts
                for concept_id, concept_data in genome.concepts.items():
                    if any(word in concept_id.lower() for word in query_lower.split()):
                        results.append(
                            {
                                "id": concept_id,
                                "type": "concept",
                                **concept_data.model_dump(),
                            }
                        )

                return {
                    "type": "search",
                    "query": query,
                    "count": len(results),
                    "results": results[:50],  # Limit to 50 results
                }
        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}

    def impact(
        self, affected_nodes: List[str], operation: str = "modify"
    ) -> Dict[str, Any]:
        """
        Simulate impact of proposed changes.

        Args:
            affected_nodes: List of node IDs that will be affected
            operation: Operation type ("modify", "delete", "add")

        Returns:
            Impact analysis with risk score and affected components
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        try:
            affected_flows = []
            affected_contracts = []
            total_risk = 0.0
            max_risk = 0.0

            for node_id in affected_nodes:
                if node_id not in genome.nodes:
                    continue

                node = genome.nodes[node_id]

                # Check flows
                for flow in genome.flows:
                    if node_id in flow.path:
                        affected_flows.append(flow.entry)

                # Check contracts
                for contract_id, contract in genome.contracts.items():
                    if node_id in contract.depends_on:
                        affected_contracts.append(contract_id)

                # Get risk score
                risk_data = genome.risk.get(node_id)
                if risk_data:
                    risk_score = risk_data.risk_score
                    total_risk += risk_score
                    max_risk = max(max_risk, risk_score)

            # Calculate average risk
            avg_risk = total_risk / len(affected_nodes) if affected_nodes else 0.0

            # Determine if approval required
            requires_approval = (
                max_risk > 0.7
                or len(affected_flows) > 5
                or len(affected_contracts) > 0
            )

            return {
                "risk_score": max(max_risk, avg_risk),
                "affected_flows": list(set(affected_flows)),
                "affected_contracts": list(set(affected_contracts)),
                "affected_nodes_count": len(affected_nodes),
                "requires_approval": requires_approval,
                "operation": operation,
            }
        except Exception as e:
            return {"error": f"Impact analysis failed: {str(e)}"}

    def update(
        self,
        added_nodes: Optional[List[str]] = None,
        removed_nodes: Optional[List[str]] = None,
        updated_edges: Optional[List[Dict[str, Any]]] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Incrementally update genome after code changes.

        Args:
            added_nodes: List of new node IDs
            removed_nodes: List of removed node IDs
            updated_edges: List of updated edge dicts
            reason: Reason for update

        Returns:
            Update result
        """
        try:
            # Trigger incremental scan
            result = self.scan(scope="full", incremental=True)
            if not result.get("success"):
                return result

            genome = self.storage.load_genome()
            if genome is None:
                return {"error": "Failed to load updated genome"}

            # Log the update reason if provided
            update_info = {
                "success": True,
                "message": "Genome updated successfully",
                "reason": reason,
                "nodes": len(genome.nodes),
                "edges": len(genome.edges),
            }

            if genome.genome_diff:
                update_info["diff"] = {
                    "added_nodes": len(genome.genome_diff.added_nodes),
                    "removed_nodes": len(genome.genome_diff.removed_nodes),
                    "modified_nodes": len(genome.genome_diff.modified_nodes),
                }

            return update_info
        except Exception as e:
            return {"error": f"Update failed: {str(e)}"}

    def validate(self) -> Dict[str, Any]:
        """
        Validate RepoGenome consistency with repository.

        Returns:
            Validation result
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {
                "valid": False,
                "error": "No genome found",
                "action": "Run repogenome.scan to generate genome",
            }

        # Check if stale
        if self.storage.is_stale():
            return {
                "valid": False,
                "error": "Genome is stale (repo hash mismatch)",
                "action": "Run repogenome.scan to regenerate",
            }

        # Basic validation checks
        issues = []

        # Check for orphaned edges
        node_ids = set(genome.nodes.keys())
        for edge in genome.edges:
            if edge.from_ not in node_ids:
                issues.append(f"Edge from missing node: {edge.from_}")
            if edge.to not in node_ids:
                issues.append(f"Edge to missing node: {edge.to}")

        if issues:
            return {
                "valid": False,
                "error": "Genome has consistency issues",
                "issues": issues,
                "action": "Run repogenome.scan to regenerate",
            }

        return {
            "valid": True,
            "message": "Genome is valid and up-to-date",
            "nodes": len(genome.nodes),
            "edges": len(genome.edges),
        }

