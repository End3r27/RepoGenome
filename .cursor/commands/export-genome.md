# Export RepoGenome

Export the RepoGenome to different formats for visualization or analysis.

## Description

Converts the RepoGenome JSON format to various export formats suitable for different tools and use cases, including graph visualization, database import, and documentation generation.

## Objective

- Export genome to GraphML for Cytoscape, yEd, etc.
- Export to DOT format for Graphviz visualization
- Export to CSV for spreadsheet analysis
- Export to Neo4j Cypher for graph database import
- Export to PlantUML for architecture diagrams

## Requirements

- `repogenome.json` file in repository root
- Valid genome file

## Parameters

- **format** (string, required): Export format
  - `"json"`: JSON format (default, same as input)
  - `"graphml"`: GraphML format (for Cytoscape, yEd, etc.)
  - `"dot"`: DOT format (for Graphviz)
  - `"csv"`: CSV format (creates nodes.csv and edges.csv)
  - `"cypher"`: Neo4j Cypher format (for graph database import)
  - `"plantuml"`: PlantUML format (for architecture diagrams)
- **output_path** (string, optional): Output file path
  - If not specified, uses default naming based on format
  - Example: `"genome.graphml"`, `"genome.dot"`, etc.

## Output

- Exported file in the specified format
- File location depends on output_path parameter
- For CSV format, creates two files: `{output_path}.nodes.csv` and `{output_path}.edges.csv`

## Usage

Use the `repogenome.export` MCP tool:

**Export to GraphML:**
```python
repogenome.export(format="graphml", output_path="genome.graphml")
```

**Export to DOT:**
```python
repogenome.export(format="dot", output_path="genome.dot")
```

**Export to CSV:**
```python
repogenome.export(format="csv", output_path="genome")
# Creates: genome.nodes.csv and genome.edges.csv
```

**Export to Neo4j Cypher:**
```python
repogenome.export(format="cypher", output_path="genome.cypher")
```

**Export to PlantUML:**
```python
repogenome.export(format="plantuml", output_path="genome.puml")
```

## Use Cases

- **GraphML**: Visualize genome in graph visualization tools
- **DOT**: Generate diagrams with Graphviz
- **CSV**: Analyze genome data in spreadsheets or BI tools
- **Cypher**: Import into Neo4j for advanced graph queries
- **PlantUML**: Generate architecture diagrams

## Notes

- Export formats preserve node and edge relationships
- Some formats may have limitations on data representation
- Large genomes may take time to export

