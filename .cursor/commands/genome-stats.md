# Get RepoGenome Statistics

Retrieve repository statistics and metrics from the RepoGenome.

## Description

Get comprehensive statistics about the repository including node counts, language distribution, edge counts, and other metrics. Useful for understanding codebase size and composition.

## Objective

- Display repository statistics and metrics
- Show node counts by type and language
- Display edge counts and relationship statistics
- Calculate average criticality and other metrics
- Identify entry points and core domains

## Requirements

- `repogenome.json` file in repository root
- Valid genome file

## Output

Statistics include:
- **Node counts** by type (file, function, class, etc.)
- **Node counts** by language (Python, TypeScript, etc.)
- **Edge counts** by type (calls, imports, etc.)
- **Total nodes** and **total edges**
- **Average criticality** score
- **Entry points** (main files, entry functions)
- **Core domains** (if IntentAtlas enabled)
- **Repository metadata** (languages, frameworks, etc.)

## Usage

Use the `repogenome.stats` MCP tool:
```python
repogenome.stats()
```

Or load the stats resource:
```
repogenome://stats
```

## Example Output

```json
{
  "nodes_by_type": {
    "file": 150,
    "function": 1200,
    "class": 80,
    ...
  },
  "nodes_by_language": {
    "Python": 800,
    "TypeScript": 400,
    ...
  },
  "edges_by_type": {
    "calls": 5000,
    "imports": 2000,
    ...
  },
  "total_nodes": 1500,
  "total_edges": 7000,
  "average_criticality": 0.65,
  "entry_points": ["main.py", "app.py"],
  ...
}
```

## Use Cases

- **Quick overview** of repository size and composition
- **Language distribution** analysis
- **Codebase health** metrics
- **Planning** for refactoring or analysis
- **Documentation** of repository characteristics

## Notes

- Statistics are calculated from the current genome state
- Some metrics require specific subsystems to be enabled
- Statistics are cached for performance

