"""Query language for RepoGenome data."""

import re
from typing import Any, Dict, List, Optional

from repogenome.core.schema import RepoGenome


class GenomeQuery:
    """Query interface for RepoGenome."""

    def __init__(self, genome: RepoGenome):
        """
        Initialize query interface.

        Args:
            genome: RepoGenome to query
        """
        self.genome = genome

    def query_nodes(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[tuple]:
        """
        Query nodes with filters.

        Args:
            filters: Dictionary of filters (e.g., {"type": "function", "criticality__gt": 0.8})

        Returns:
            List of (node_id, node_data) tuples
        """
        results = []

        for node_id, node_data in self.genome.nodes.items():
            if self._match_filters(node_data, filters):
                results.append((node_id, node_data))

        return results

    def query_edges(
        self,
        from_node: Optional[str] = None,
        to_node: Optional[str] = None,
        edge_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query edges.

        Args:
            from_node: Filter by source node
            to_node: Filter by target node
            edge_type: Filter by edge type

        Returns:
            List of edge dictionaries
        """
        results = []

        for edge in self.genome.edges:
            edge_from = edge.from_
            edge_to = edge.to
            etype = edge.type.value if hasattr(edge.type, "value") else str(edge.type)

            if from_node and edge_from != from_node:
                continue
            if to_node and edge_to != to_node:
                continue
            if edge_type and etype != edge_type:
                continue

            results.append(edge.model_dump(by_alias=True))

        return results

    def get_neighbors(
        self, node_id: str, direction: str = "both"
    ) -> List[str]:
        """
        Get neighboring nodes.

        Args:
            node_id: Node ID
            direction: "in", "out", or "both"

        Returns:
            List of neighbor node IDs
        """
        neighbors = set()

        for edge in self.genome.edges:
            edge_from = edge.from_
            edge_to = edge.to

            if direction in ["out", "both"] and edge_from == node_id:
                neighbors.add(edge_to)
            if direction in ["in", "both"] and edge_to == node_id:
                neighbors.add(edge_from)

        return list(neighbors)

    def _match_filters(self, node_data: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        """Check if node matches filters."""
        if not filters:
            return True

        for key, value in filters.items():
            # Handle special operators (e.g., criticality__gt)
            if "__" in key:
                field, op = key.split("__", 1)
                node_value = node_data.get(field)

                if op == "gt" and not (node_value is not None and node_value > value):
                    return False
                elif op == "gte" and not (node_value is not None and node_value >= value):
                    return False
                elif op == "lt" and not (node_value is not None and node_value < value):
                    return False
                elif op == "lte" and not (node_value is not None and node_value <= value):
                    return False
                elif op == "in" and node_value not in value:
                    return False
            else:
                # Simple equality
                if node_data.get(key) != value:
                    return False

        return True


def parse_simple_query(query_str: str) -> Dict[str, Any]:
    """
    Parse a simple query string.

    Example: "nodes where type=function and criticality>0.8"

    Args:
        query_str: Query string

    Returns:
        Dictionary with query components
    """
    # Simple parser - could be enhanced
    query_lower = query_str.lower().strip()

    if query_lower.startswith("nodes where"):
        # Extract filters
        filters = {}
        where_clause = query_str[12:].strip()

        # Parse conditions (simple)
        conditions = re.split(r"\s+and\s+", where_clause, flags=re.IGNORECASE)

        for condition in conditions:
            condition = condition.strip()
            if "=" in condition:
                key, value = condition.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                filters[key] = value
            elif ">" in condition:
                key, value = condition.split(">", 1)
                key = key.strip()
                value = value.strip()
                try:
                    filters[f"{key}__gt"] = float(value)
                except ValueError:
                    pass

        return {"type": "nodes", "filters": filters}

    return {}

