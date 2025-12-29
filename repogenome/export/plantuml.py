"""PlantUML export for RepoGenome architecture diagrams."""

from pathlib import Path
from typing import Dict, Set

from repogenome.core.schema import RepoGenome


def export_plantuml(genome: RepoGenome, output_path: Path) -> None:
    """
    Export genome to PlantUML format for architecture diagrams.

    Args:
        genome: RepoGenome to export
        output_path: Path to output file
    """
    lines = ["@startuml", "!theme plain", ""]
    
    # Group nodes by file/package
    packages: Dict[str, Set[str]] = {}
    node_to_package: Dict[str, str] = {}
    
    for node_id, node_data in genome.nodes.items():
        # Convert to dict if needed
        if hasattr(node_data, 'model_dump'):
            node_dict = node_data.model_dump()
        elif hasattr(node_data, 'dict'):
            node_dict = node_data.dict()
        else:
            node_dict = node_data if isinstance(node_data, dict) else {}
        
        file_path = node_dict.get('file', '')
        if file_path:
            # Extract package/namespace
            parts = file_path.replace('\\', '/').split('/')
            if len(parts) > 1:
                package = '/'.join(parts[:-1])
            else:
                package = 'root'
            
            if package not in packages:
                packages[package] = set()
            packages[package].add(node_id)
            node_to_package[node_id] = package
    
    # Create packages and components
    for package, node_ids in packages.items():
        package_name = package.replace('/', '.').replace('\\', '.')
        lines.append(f"package \"{package_name}\" {{")
        
        for node_id in node_ids:
            node_data = genome.nodes[node_id]
            if hasattr(node_data, 'model_dump'):
                node_dict = node_data.model_dump()
            elif hasattr(node_data, 'dict'):
                node_dict = node_data.dict()
            else:
                node_dict = node_data if isinstance(node_data, dict) else {}
            
            node_type = node_dict.get('type', 'Node')
            node_name = node_id.split('\\')[-1].split('/')[-1]
            
            # Format based on type
            if node_type == 'class':
                lines.append(f"  class {node_name}")
            elif node_type == 'function':
                lines.append(f"  function {node_name}")
            elif node_type == 'file':
                lines.append(f"  file {node_name}")
            else:
                lines.append(f"  component {node_name}")
        
        lines.append("}")
        lines.append("")
    
    # Add relationships
    lines.append("' Relationships")
    for edge in genome.edges:
        from_name = edge.from_.split('\\')[-1].split('/')[-1]
        to_name = edge.to.split('\\')[-1].split('/')[-1]
        edge_type = edge.type if hasattr(edge, 'type') else '-->'
        
        # Use appropriate arrow based on edge type
        if 'depends' in str(edge_type).lower():
            arrow = "..>"
        elif 'imports' in str(edge_type).lower() or 'uses' in str(edge_type).lower():
            arrow = "-->"
        else:
            arrow = "-->"
        
        lines.append(f"{from_name} {arrow} {to_name}")
    
    lines.append("")
    lines.append("@enduml")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

