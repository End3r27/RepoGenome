# Query RepoGenome

Search and query the RepoGenome for files, functions, classes, and other nodes.

## Description

Search the RepoGenome graph to find specific nodes (files, functions, classes, etc.) using natural language queries or structured filters. Supports pagination and field selection for efficient context usage.

## Objective

- Find nodes matching search criteria
- Search by type, language, file pattern, or natural language query
- Retrieve minimal context (IDs only) or detailed information
- Filter results with complex AND/OR logic
- Paginate large result sets

## Requirements

- `repogenome.json` file in repository root
- Valid genome file

## Parameters

- **query** (string): Natural language search terms or keywords
- **filters** (object): Structured filters with AND/OR logic
  - Example: `{"type": "function", "language": "Python"}`
  - Complex: `{"and": [{"type": "function"}, {"or": [{"language": "Python"}, {"language": "TypeScript"}]}]}`
- **fields** (array/string): Field selection to reduce context
  - Example: `["id", "type", "file"]` or `"id,type,file"`
  - Field aliases: `t` → `type`, `f` → `file`, `s` → `summary`, `c` → `criticality`
- **ids_only** (boolean): Return only node IDs for minimal context
- **max_summary_length** (integer): Truncate summary text length
- **page** (integer): Page number for pagination (1-indexed)
- **page_size** (integer): Number of results per page (default: 50)

## Output

- Query results with matching nodes
- Pagination information (page, page_size, total_count)
- Selected fields only (if field selection specified)
- Node IDs only (if ids_only=true)

## Usage

Use the `repogenome.query` MCP tool:

**Minimal context (IDs only):**
```python
repogenome.query(query="authentication", ids_only=true, page=1, page_size=50)
```

**With field selection:**
```python
repogenome.query(
    query="database functions",
    fields=["id", "type", "file"],
    page=1,
    page_size=20,
    max_summary_length=100
)
```

**Complex filters:**
```python
repogenome.query(
    query="",
    filters={
        "and": [
            {"type": "function"},
            {"or": [
                {"language": "Python"},
                {"language": "TypeScript"}
            ]}
        ]
    },
    fields=["id", "type", "file", "summary"]
)
```

## Best Practices

1. **Start with IDs-only** for large result sets, then fetch details selectively
2. **Use field selection** to minimize context usage
3. **Paginate** large result sets to avoid overwhelming context
4. **Truncate summaries** if full text isn't needed
5. **Leverage caching** - query results are automatically cached

