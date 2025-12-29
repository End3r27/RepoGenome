"""Convenience wrapper for RepoGenome with query methods."""

from typing import Any, Dict, List, Optional

from repogenome.core.schema import Edge, Node, RepoGenome


class Genome:
    """
    Wrapper around RepoGenome with convenience query methods.

    Provides a more ergonomic API for querying genome data.
    """

    def __init__(self, genome: RepoGenome):
        """
        Initialize Genome wrapper.

        Args:
            genome: RepoGenome instance
        """
        self.genome = genome

    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """
        Get all nodes of a specific type.

        Args:
            node_type: Type of node (e.g., "function", "class", "file")

        Returns:
            List of matching nodes
        """
        return [
            Node(**node_data)
            for node_id, node_data in self.genome.nodes.items()
            if node_data.get("type") == node_type
        ]

    def get_edges_from(self, from_node: str) -> List[Edge]:
        """
        Get all edges originating from a node.

        Args:
            from_node: Source node ID

        Returns:
            List of edges
        """
        edges = []
        for edge_data in self.genome.edges:
            edge_from = edge_data.get("from") or edge_data.get("from_")
            if edge_from == from_node:
                edges.append(Edge(**edge_data))
        return edges

    def get_edges_to(self, to_node: str) -> List[Edge]:
        """
        Get all edges pointing to a node.

        Args:
            to_node: Target node ID

        Returns:
            List of edges
        """
        edges = []
        for edge_data in self.genome.edges:
            if edge_data.get("to") == to_node:
                edges.append(Edge(**edge_data))
        return edges

    def get_node(self, node_id: str) -> Optional[Node]:
        """
        Get a specific node by ID.

        Args:
            node_id: Node ID

        Returns:
            Node or None if not found
        """
        node_data = self.genome.nodes.get(node_id)
        if node_data:
            return Node(**node_data)
        return None

    def save(self, path: str) -> None:
        """Save genome to file."""
        self.genome.save(path)

    @classmethod
    def load(cls, path: str) -> "Genome":
        """Load genome from file."""
        genome = RepoGenome.load(path)
        return cls(genome)

