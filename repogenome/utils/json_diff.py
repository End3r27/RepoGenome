"""Utilities for computing diffs between RepoGenome JSON structures."""

from typing import Any, Dict, List, Set

from repogenome.core.schema import Edge, GenomeDiff


def compute_genome_diff(
    old_genome: Dict[str, Any], new_genome: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute diff between two genomes.

    Args:
        old_genome: Previous genome dictionary
        new_genome: New genome dictionary

    Returns:
        GenomeDiff dictionary
    """
    old_nodes = set(old_genome.get("nodes", {}).keys())
    new_nodes = set(new_genome.get("nodes", {}).keys())

    added_nodes = list(new_nodes - old_nodes)
    removed_nodes = list(old_nodes - new_nodes)
    modified_nodes = []

    # Check for modified nodes
    common_nodes = old_nodes & new_nodes
    for node_id in common_nodes:
        old_node = old_genome.get("nodes", {}).get(node_id, {})
        new_node = new_genome.get("nodes", {}).get(node_id, {})
        if old_node != new_node:
            modified_nodes.append(node_id)

    # Compare edges
    old_edges = _normalize_edges(old_genome.get("edges", []))
    new_edges = _normalize_edges(new_genome.get("edges", []))

    added_edges = [
        edge
        for edge in new_genome.get("edges", [])
        if _edge_to_tuple(edge) not in old_edges
    ]
    removed_edges = [
        edge
        for edge in old_genome.get("edges", [])
        if _edge_to_tuple(edge) not in new_edges
    ]

    return {
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "modified_nodes": modified_nodes,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
    }


def _normalize_edges(edges: List[Dict[str, Any]]) -> Set[tuple]:
    """Normalize edges to tuples for comparison."""
    return {_edge_to_tuple(edge) for edge in edges}


def _edge_to_tuple(edge: Dict[str, Any]) -> tuple:
    """Convert edge dict to comparable tuple."""
    from_val = edge.get("from") or edge.get("from_")
    return (from_val, edge.get("to"), edge.get("type"))


def get_affected_nodes(
    changed_files: List[str], genome: Dict[str, Any]
) -> Set[str]:
    """
    Get set of node IDs affected by changed files.

    Args:
        changed_files: List of changed file paths
        genome: Current genome dictionary

    Returns:
        Set of affected node IDs
    """
    affected = set()

    # Add file nodes directly
    for file_path in changed_files:
        if file_path in genome.get("nodes", {}):
            affected.add(file_path)

    # Find nodes in changed files
    nodes = genome.get("nodes", {})
    for node_id, node_data in nodes.items():
        node_file = node_data.get("file")
        if node_file and any(
            node_file.endswith(f) or f.endswith(node_file)
            for f in changed_files
        ):
            affected.add(node_id)

    return affected

