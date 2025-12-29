# RepoGenome LLM Prompt

## Quick Start

RepoGenome is a machine-readable knowledge artifact (`repogenome.json`) encoding codebase structure, behavior, and history. **Agent Contract**: Load genome before acting, cite nodes/edges when making claims, update genome after code changes.

## Essential Schema

### Core Sections

| Section | Purpose | Key Fields |
|---------|---------|------------|
| `summary` | Quick boot info | `entry_points`, `core_domains`, `hotspots`, `do_not_touch` |
| `nodes` | All entities (files, functions, classes) | `type`, `file`, `language`, `visibility`, `summary`, `criticality` |
| `edges` | Relationships | `from`, `to`, `type` (imports, calls, defines, tests) |
| `flows` | Runtime execution paths | `entry`, `path`, `side_effects`, `confidence` |
| `concepts` | Domain groupings | `nodes`, `description` |
| `history` | Temporal evolution | `churn_score`, `last_major_change`, `notes` |
| `risk` | Risk assessment | `risk_score`, `reasons` |
| `contracts` | Public APIs | `depends_on`, `breaking_change_risk` |

### Node Types

- `file` - Source files
- `function` - Functions/methods
- `class` - Classes
- `module` - Modules/packages
- `test` - Test cases
- `config` - Configuration files
- `resource` - Non-code resources

### Edge Types

- `imports` - Module/package imports
- `calls` - Function/method calls
- `defines` - Containment (file defines function)
- `tests` - Test coverage
- `depends_on` - Dependencies
- `mutates` - Data mutations
- `emits` - Events/signals

### Compact Format Field Mappings

| Full Name | Compact | Full Name | Compact |
|-----------|---------|-----------|---------|
| `type` | `t` | `file` | `f` |
| `language` | `lang` | `visibility` | `v` |
| `summary` | `s` | `criticality` | `c` |
| `from` | `fr` | `to` | `to` |
| `entry_points` | `ep` | `core_domains` | `cd` |
| `churn_score` | `cs` | `risk_score` | `rs` |

## Reading Genome

```python
from repogenome import RepoGenome

# Load (auto-detects compact format and .json.gz)
genome = RepoGenome.load("repogenome.json")

# Access data
entry_points = genome.summary.entry_points
node = genome.nodes["auth.login_user"]
edges = genome.edges
```

## Key Query Patterns

| Task | Pattern |
|------|---------|
| Entry points | `genome.summary.entry_points` |
| Get node | `genome.nodes[node_id]` |
| Find by type | `[n for n in genome.nodes.values() if n.get("type") == "function"]` |
| Edges from node | `[e for e in genome.edges if e.get("from") == node_id]` |
| Edges to node | `[e for e in genome.edges if e.get("to") == node_id]` |
| High criticality | `[nid for nid, n in genome.nodes.items() if n.get("criticality", 0) > 0.7]` |
| Hotspots | `genome.summary.hotspots` |
| Legacy code | `genome.summary.do_not_touch` |
| Core domains | `genome.summary.core_domains` |

## Staying Updated

1. **Check freshness**: Compare `metadata.generated_at` with recent repo changes
2. **Regenerate**: `repogenome generate --incremental` (faster than full)
3. **After changes**: Always update genome after modifying code
4. **Stale detection**: If genome missing or `repo_hash` mismatch, regenerate

## Interpretation Quick Reference

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| `criticality` | > 0.7 | Important component, high impact if changed |
| `risk_score` | > 0.7 | Risky to modify, high fan-in or low coverage |
| `churn_score` | > 0.7 | Frequently changed, potential instability |
| `confidence` (flows) | < 0.5 | Uncertain execution path |
| `breaking_change_risk` | > 0.7 | Public API, breaking changes affect many |
| `hotspots` | Listed | Files with high churn or complexity |
| `do_not_touch` | Listed | Legacy/deprecated, avoid modifying |

## Common Tasks

- **Find all functions**: Filter nodes by `type == "function"`
- **Trace dependencies**: Follow `edges` from entry point
- **Identify public APIs**: Check `contracts` section
- **Understand flow**: Use `flows` for execution paths
- **Check test coverage**: See `tests` section or `edges` with `type == "tests"`
- **Find related code**: Use `concepts` for domain groupings

## Notes

- Compact format uses short field names (auto-expanded on load)
- `.json.gz` files are automatically decompressed
- Node IDs: `file.py` for files, `file.function_name` for functions
- Always cite specific node IDs or edges when referencing code structure
