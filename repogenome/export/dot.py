"""DOT format export for RepoGenome (Graphviz)."""

from pathlib import Path

from repogenome.core.schema import RepoGenome


def export_dot(genome: RepoGenome, output_path: Path) -> None:
    """
    Export genome to DOT format (Graphviz).

    Args:
        genome: RepoGenome to export
        output_path: Path to output file
    """
    nodes = genome.nodes
    edges = genome.edges

    lines = ["digraph RepoGenome {", '  rankdir="LR";', "  node [shape=box];"]

    # Add nodes with labels
    for node_id, node_data in nodes.items():
        node_type = node_data.get("type", "")
        node_id_escaped = _escape_dot_id(node_id)

        # Create label
        label_parts = [node_id.split("\\")[-1].split("/")[-1]]  # Short name
        if node_type:
            label_parts.append(f"({node_type})")

        label = "\\n".join(label_parts)
        label_escaped = _escape_dot_label(label)

        lines.append(f'  "{node_id_escaped}" [label="{label_escaped}"];')

    # Add edges
    for edge in edges:
        edge_from = _escape_dot_id(edge.from_)
        edge_to = _escape_dot_id(edge.to)
        edge_type = edge.type.value if hasattr(edge.type, "value") else str(edge.type)

        # Add edge type as label
        if edge_type:
            lines.append(
                f'  "{edge_from}" -> "{edge_to}" [label="{_escape_dot_label(edge_type)}"];'
            )
        else:
            lines.append(f'  "{edge_from}" -> "{edge_to}";')

    lines.append("}")

    # Write file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _escape_dot_id(identifier: str) -> str:
    """Escape identifier for DOT format."""
    # Replace special characters
    return (
        identifier.replace("\\", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace('"', '\\"')
    )


def _escape_dot_label(label: str) -> str:
    """Escape label text for DOT format."""
    return label.replace('"', '\\"').replace("\n", "\\n")

