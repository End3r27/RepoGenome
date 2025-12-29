# Get Node Details

Retrieve detailed information about a specific node in the RepoGenome.

## Description

Get comprehensive information about a single node (file, function, class, etc.) including its properties, relationships, and metadata. Supports field selection and depth control for efficient context usage.

## Objective

- Retrieve detailed node information
- Get incoming and outgoing edges (relationships)
- Access node metadata (criticality, visibility, summary, etc.)
- Control relationship depth to limit context
- Select only needed fields

## Requirements

- `repogenome.json` file in repository root
- Valid node ID

## Parameters

- **node_id** (string, required): The ID of the node to retrieve
  - Examples: `"auth.login_user"`, `"repogenome/core/generator.py"`, `"UserService"`
- **fields** (array/string): Field selection to reduce context
  - Example: `["id", "type", "file", "summary"]` or `"id,type,file,summary"`
  - Field aliases: `t` → `type`, `f` → `file`, `s` → `summary`, `c` → `criticality`
- **max_depth** (integer): Relationship depth limit
  - `0`: Node data only (no relationships)
  - `1`: Direct relationships only (default)
  - `2+`: Multiple levels (use sparingly)
- **include_edges** (boolean): Include edge data (default: true)
- **edge_types** (array): Filter edges by type
  - Example: `["calls", "imports"]` - Only show call and import relationships

## Output

- Node details with selected fields
- Incoming edges (nodes that reference this node)
- Outgoing edges (nodes this node references)
- Node metadata (criticality, visibility, summary, language, etc.)
- Risk information (if available)

## Usage

Use the `repogenome.get_node` MCP tool:

**Node only (no relationships):**
```python
repogenome.get_node(
    node_id="auth.login_user",
    fields=["id", "type", "file", "summary"],
    max_depth=0
)
```

**With direct relationships:**
```python
repogenome.get_node(
    node_id="auth.login_user",
    fields=["id", "type", "file", "summary", "incoming_edges", "outgoing_edges"],
    max_depth=1
)
```

**Filter by edge type:**
```python
repogenome.get_node(
    node_id="auth.login_user",
    edge_types=["calls"],
    max_depth=1
)
```

**Minimal context:**
```python
repogenome.get_node(
    node_id="auth.login_user",
    fields=["id", "type", "file"],
    max_depth=0,
    include_edges=false
)
```

## Best Practices

1. **Start with max_depth=0** if you only need node properties
2. **Use field selection** to minimize context
3. **Filter edge types** if you only need specific relationships
4. **Set include_edges=false** if relationships aren't needed

