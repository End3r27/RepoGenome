"""GraphML export for RepoGenome."""

from pathlib import Path
from typing import Any, Dict

from repogenome.core.schema import RepoGenome


def export_graphml(genome: RepoGenome, output_path: Path) -> None:
    """
    Export genome to GraphML format.

    Args:
        genome: RepoGenome to export
        output_path: Path to output file
    """
    nodes = genome.nodes
    edges = genome.edges

    # Build GraphML
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
        '          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '          xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns',
        '          http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
        '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
        '  <key id="language" for="node" attr.name="language" attr.type="string"/>',
        '  <key id="file" for="node" attr.name="file" attr.type="string"/>',
        '  <key id="edge_type" for="edge" attr.name="type" attr.type="string"/>',
        '  <graph id="G" edgedefault="directed">',
    ]

    # Add nodes
    for node_id, node_data in nodes.items():
        node_id_escaped = _escape_xml(node_id)
        node_type = node_data.get("type", "")
        language = node_data.get("language", "")
        file_path = node_data.get("file", "")

        lines.append(f'    <node id="{node_id_escaped}">')
        lines.append(f'      <data key="type">{_escape_xml(str(node_type))}</data>')
        if language:
            lines.append(f'      <data key="language">{_escape_xml(language)}</data>')
        if file_path:
            lines.append(f'      <data key="file">{_escape_xml(file_path)}</data>')
        lines.append("    </node>")

    # Add edges
    for edge in edges:
        edge_from = edge.from_
        edge_to = edge.to
        edge_type = edge.type.value if hasattr(edge.type, "value") else str(edge.type)

        from_escaped = _escape_xml(edge_from)
        to_escaped = _escape_xml(edge_to)

        lines.append(f'    <edge source="{from_escaped}" target="{to_escaped}">')
        lines.append(f'      <data key="edge_type">{_escape_xml(edge_type)}</data>')
        lines.append("    </edge>")

    lines.extend(["  </graph>", "</graphml>"])

    # Write file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

