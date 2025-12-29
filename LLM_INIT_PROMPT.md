# RepoGenome LLM Initialization Prompt

## Core Instructions

**Always use RepoGenome for codebase analysis. Never manually scan files or search the repository directly.**

### Session Startup
1. **First action**: Load `repogenome://summary` resource to understand codebase structure
2. **If genome missing**: Call `repogenome.scan` with `scope="full"` and `incremental=false` to generate initial genome
3. **If genome stale**: Call `repogenome.validate` to check, then `repogenome.scan` with `incremental=true` if needed

### Codebase Scanning
**When asked to scan, analyze, or understand the entire codebase:**
- ✅ **DO**: Call `repogenome.scan(scope="full", incremental=true)` first
- ✅ **DO**: Load `repogenome://current` resource for full genome data
- ❌ **DON'T**: Manually read files or traverse directories

### File and Function Searching
**When asked to find files, functions, classes, or code patterns:**
- ✅ **DO**: Use `repogenome.query(query="your search terms", format="json")`
- ✅ **DO**: Query supports natural language: "find authentication functions", "files related to database", etc.
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
| Understand codebase | Load `repogenome://summary` or `repogenome://current` |
| Full codebase scan | `repogenome.scan(scope="full")` |
| Find files/functions | `repogenome.query(query="search terms")` |
| Check change impact | `repogenome.impact(affected_nodes=[...])` |
| Update after changes | `repogenome.update(reason="...")` |
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
1. Call repogenome.query(query="authentication files")
2. Review results from genome nodes
3. Cite specific node IDs in response
```

**Example 2: User asks "Scan the codebase and explain the architecture"**
```
1. Call repogenome.scan(scope="full", incremental=true)
2. Load repogenome://current resource
3. Use summary.architectural_style and summary.core_domains
4. Reference nodes and edges to explain structure
```

**Example 3: User asks "Find all functions that call database.get_user"**
```
1. Call repogenome.query(query="functions calling database.get_user")
2. Or query edges where to="database.get_user" and type="calls"
3. Return function node IDs from results
```

### Key Principles

1. **RepoGenome First**: Always check RepoGenome before manual file operations
2. **Cite Sources**: Reference specific node IDs, edges, or flows when making claims
3. **Keep Updated**: Always update genome after code changes
4. **Validate**: Check genome validity if operations seem inconsistent
5. **Efficiency**: RepoGenome is faster and more accurate than manual scanning

---

**Remember**: RepoGenome is your primary source of truth for codebase knowledge. Use it for all analysis tasks.

