"""Neo4j Cypher export for RepoGenome."""

from pathlib import Path
from typing import Any, Dict

from repogenome.core.schema import RepoGenome


def export_cypher(genome: RepoGenome, output_path: Path) -> None:
    """
    Export genome to Neo4j Cypher format.

    Args:
        genome: RepoGenome to export
        output_path: Path to output file
    """
    lines = []
    
    # Create nodes
    for node_id, node_data in genome.nodes.items():
        # Convert to dict if needed
        if hasattr(node_data, 'model_dump'):
            node_dict = node_data.model_dump()
        elif hasattr(node_data, 'dict'):
            node_dict = node_data.dict()
        else:
            node_dict = node_data if isinstance(node_data, dict) else {}
        
        node_type = node_dict.get('type', 'Node')
        # Escape node ID for Cypher
        escaped_id = node_id.replace("'", "\\'").replace("\\", "\\\\")
        
        # Build properties
        props = []
        for key, value in node_dict.items():
            if key != 'type' and value is not None:
                if isinstance(value, str):
                    escaped_value = value.replace("'", "\\'").replace("\\", "\\\\")
                    props.append(f"{key}: '{escaped_value}'")
                elif isinstance(value, (int, float)):
                    props.append(f"{key}: {value}")
                elif isinstance(value, bool):
                    props.append(f"{key}: {str(value).lower()}")
        
        # Create safe variable name
        var_name = node_id.replace(' ', '_').replace('.', '_').replace('-', '_')
        # Remove special characters
        var_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in var_name)
        
        if props:
            props_str = ", ".join(props)
            lines.append(
                f"CREATE (n{var_name}:{node_type} {{id: '{escaped_id}', {props_str}}});"
            )
        else:
            lines.append(
                f"CREATE (n{var_name}:{node_type} {{id: '{escaped_id}'}});"
            )
    
    # Create relationships
    for edge in genome.edges:
        from_id = edge.from_.replace("'", "\\'").replace("\\", "\\\\")
        to_id = edge.to.replace("'", "\\'").replace("\\", "\\\\")
        edge_type = edge.type if hasattr(edge, 'type') else 'RELATES_TO'
        
        # Escape identifiers
        from_var = edge.from_.replace(' ', '_').replace('.', '_')
        to_var = edge.to.replace(' ', '_').replace('.', '_')
        
        lines.append(
            f"MATCH (a), (b) WHERE a.id = '{from_id}' AND b.id = '{to_id}' "
            f"CREATE (a)-[:{edge_type}]->(b);"
        )
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("// Neo4j Cypher export from RepoGenome\n")
        f.write("// Run this script in Neo4j to import the graph\n\n")
        f.write("\n".join(lines))

