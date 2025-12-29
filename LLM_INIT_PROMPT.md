# RepoGenome LLM Initialization Prompt

## Core Instructions

**Always use RepoGenome for codebase analysis. Never manually scan files or search the repository directly.**

### Session Startup
1. **First action**: Load `repogenome://summary` resource to understand codebase structure
2. **Alternative**: Load `repogenome://stats` for quick repository statistics
3. **If genome missing**: Call `repogenome.scan` with `scope="full"` and `incremental=false` to generate initial genome
4. **If genome stale**: Call `repogenome.validate` to check, then `repogenome.scan` with `incremental=true` if needed

### Codebase Scanning
**When asked to scan, analyze, or understand the entire codebase:**
- ✅ **DO**: Call `repogenome.scan(scope="full", incremental=true)` first
- ✅ **DO**: Load `repogenome://current` resource for full genome data
- ❌ **DON'T**: Manually read files or traverse directories

### File and Function Searching
**When asked to find files, functions, classes, or code patterns:**
- ✅ **DO**: Use `repogenome.query(query="your search terms", format="json", page=1, page_size=50)` with pagination
- ✅ **DO**: Use `repogenome.search(query="terms", node_type="function", language="Python")` for advanced filtering
- ✅ **DO**: Use `repogenome.get_node(node_id="node.id")` to get detailed information about a specific node
- ✅ **DO**: Query supports natural language: "find authentication functions", "files related to database", etc.
- ✅ **DO**: Use filters parameter for complex AND/OR logic queries
- ❌ **DON'T**: Use file system search tools or grep

### Before Code Changes
**Before modifying any code:**
- ✅ **DO**: Call `repogenome.impact(affected_nodes=["node.id"], operation="modify")` to check impact
- ✅ **DO**: Review risk scores and affected flows/contracts

### After Code Changes
**After making code changes:**
- ✅ **DO**: Call `repogenome.update(reason="description of changes")` to keep genome current
- ✅ **DO**: This is mandatory - genome must stay synchronized

### Quick Reference

| Task | RepoGenome Action |
|------|------------------|
| Understand codebase | Load `repogenome://summary`, `repogenome://stats`, or `repogenome://current` |
| Get repository stats | Load `repogenome://stats` or call `repogenome.stats()` |
| Get specific node | Load `repogenome://nodes/{node_id}` or call `repogenome.get_node(node_id="...")` |
| Full codebase scan | `repogenome.scan(scope="full")` |
| Find files/functions | `repogenome.query(query="search terms", page=1, page_size=50)` or `repogenome.search(...)` |
| Get dependencies | `repogenome.dependencies(node_id="...", direction="both", depth=1)` |
| Check change impact | `repogenome.impact(affected_nodes=[...])` |
| Update after changes | `repogenome.update(reason="...")` |
| Export genome | `repogenome.export(format="csv|cypher|plantuml|graphml|dot")` |
| Validate genome | `repogenome.validate()` |

### Fallback (If RepoGenome Unavailable)

**Only if RepoGenome tools/resources are not available:**
1. Check if `repogenome.json` exists in repository root
2. If exists, read it directly (it's JSON)
3. If missing, inform user that RepoGenome should be set up first
4. Never proceed with manual file scanning as primary method

### Examples

**Example 1: User asks "What files handle authentication?"**
```
1. Call repogenome.search(query="authentication", node_type="file")
2. Or use repogenome.query(query="authentication files", filters={"type": "file"})
3. Review results from genome nodes
4. Cite specific node IDs in response
```

**Example 2: User asks "Scan the codebase and explain the architecture"**
```
1. Call repogenome.scan(scope="full", incremental=true)
2. Load repogenome://current resource or repogenome://stats for quick overview
3. Use summary.architectural_style and summary.core_domains
4. Reference nodes and edges to explain structure
```

**Example 3: User asks "Find all functions that call database.get_user"**
```
1. Call repogenome.get_node(node_id="database.get_user") to see outgoing edges
2. Or use repogenome.dependencies(node_id="database.get_user", direction="incoming")
3. Or query with repogenome.query(query="functions calling database.get_user")
4. Return function node IDs from results
```

**Example 4: User asks "Get statistics about the repository"**
```
1. Call repogenome.stats() or load repogenome://stats resource
2. Review node counts by type, language distribution, edge counts
3. Use statistics to understand codebase composition
```

**Example 5: User asks "What are the dependencies of auth.login_user?"**
```
1. Call repogenome.dependencies(node_id="auth.login_user", direction="both", depth=2)
2. Review dependency graph with configurable depth
3. Understand both incoming and outgoing dependencies
```

### Available Resources

- `repogenome://current` - Full repository genome (use for comprehensive analysis)
- `repogenome://summary` - Quick boot context (use for fast startup)
- `repogenome://stats` - Repository statistics (use for metrics and overview)
- `repogenome://diff` - Changes since last update (use to see what changed)
- `repogenome://nodes/{node_id}` - Individual node data (use for detailed node information)

### Available Tools

- `repogenome.scan` - Generate/regenerate genome
- `repogenome.query` - Query with pagination and advanced filters
- `repogenome.get_node` - Get detailed node information with relationships
- `repogenome.search` - Advanced search with multiple filter options
- `repogenome.dependencies` - Get dependency graph for a node
- `repogenome.stats` - Get repository statistics and metrics
- `repogenome.export` - Export genome to different formats
- `repogenome.impact` - Check change impact before modifying
- `repogenome.update` - Update genome after code changes
- `repogenome.validate` - Validate genome consistency

### Key Principles

1. **RepoGenome First**: Always check RepoGenome before manual file operations
2. **Cite Sources**: Reference specific node IDs, edges, or flows when making claims
3. **Keep Updated**: Always update genome after code changes
4. **Validate**: Check genome validity if operations seem inconsistent
5. **Efficiency**: RepoGenome is faster and more accurate than manual scanning
6. **Use Pagination**: For large result sets, use pagination parameters in queries
7. **Leverage Caching**: Query results are cached automatically - repeated queries are fast
8. **Use Appropriate Tools**: Choose the right tool for the task (search vs query vs get_node)

---

**Remember**: RepoGenome is your primary source of truth for codebase knowledge. Use it for all analysis tasks. The enhanced toolset in v0.8.0 provides powerful capabilities for codebase exploration and analysis.

