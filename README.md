# RepoGenome

🧬 **Unified Repository Intelligence Artifact Generator**

RepoGenome.json is a continuously evolving, machine-readable knowledge organism that encodes the structure, behavior, intent, and history of a codebase.

## Overview

RepoGenome generates a comprehensive JSON artifact (`repogenome.json`) that combines multiple analysis perspectives:

- **RepoSpider**: Structural graph (files, symbols, dependencies)
- **FlowWeaver**: Runtime execution paths and side effects
- **IntentAtlas**: Domain concepts and responsibilities
- **ChronoMap**: Temporal evolution and churn analysis
- **TestGalaxy**: Test coverage analysis (optional)
- **ContractLens**: Public API contract analysis

## Installation

```bash
git clone https://github.com/End3r27/RepoGenome
cd RepoGenome
pip install -e .
```

### Requirements

- Python 3.8+
- Git (for repository analysis)
- PyYAML (for YAML file analysis, included in dependencies)

Optional dependencies:
- tree-sitter and tree-sitter-typescript (for enhanced TypeScript/JavaScript analysis)

## Quick Start

### CLI Usage

Generate a RepoGenome for your repository:

```bash
repogenome generate /path/to/repository
```

This creates a `repogenome.json` file in the repository root.

Generate with debug logging:

```bash
repogenome generate /path/to/repository --log debug
```

**Note for macOS users**: RepoGenome automatically uses subprocess-based git operations on macOS to avoid hanging issues. To force GitPython usage, set `REPOGENOME_USE_GITPYTHON=true`.

Update an existing genome incrementally:

```bash
repogenome update /path/to/repository
```

Validate a genome file:

```bash
repogenome validate repogenome.json
```

Compare two genomes:

```bash
repogenome diff old_genome.json new_genome.json
```

### Library Usage

```python
from repogenome import RepoGenomeGenerator, Genome

# Generate genome
generator = RepoGenomeGenerator(repo_path="./myproject")
genome = generator.generate()
genome.save("repogenome.json")

# Load and query genome
genome = Genome.load("repogenome.json")

# Query nodes
functions = genome.get_nodes_by_type("function")
edges_from = genome.get_edges_from("auth.login_user")

# Access genome data
print(f"Total nodes: {len(genome.genome.nodes)}")
print(f"Total edges: {len(genome.genome.edges)}")
```

## RepoGenome Schema

The `repogenome.json` file contains the following sections:

### Metadata
```json
{
  "metadata": {
    "generated_at": "2025-01-12T18:42:00Z",
    "repo_hash": "a8f3c1...",
    "languages": ["Python", "TypeScript", "Java", "Go", "Rust"],
    "frameworks": ["FastAPI", "React"],
    "repogenome_version": "0.6.0"
  }
}
```

### Summary
High-level overview for quick agent boot:
```json
{
  "summary": {
    "entry_points": ["main.py", "app.py"],
    "architectural_style": ["Layered", "API-First"],
    "core_domains": ["authentication", "payments"],
    "hotspots": ["auth.py", "db.py"],
    "do_not_touch": ["legacy/billing_old.py"]
  }
}
```

### Nodes
Every meaningful entity in the codebase:
```json
{
  "nodes": {
    "auth.login_user": {
      "type": "function",
      "file": "auth.py",
      "language": "Python",
      "visibility": "public",
      "summary": "Authenticates a user",
      "criticality": 0.9
    }
  }
}
```

### Edges
Relationships between nodes:
```json
{
  "edges": [
    {
      "from": "auth.login_user",
      "to": "db.get_user",
      "type": "calls"
    }
  ]
}
```

### Flows
Runtime execution paths:
```json
{
  "flows": [
    {
      "entry": "POST /login",
      "path": ["api.login", "auth.login_user", "db.get_user"],
      "side_effects": ["db.read"],
      "confidence": 0.82
    }
  ]
}
```

### Concepts
Domain groupings:
```json
{
  "concepts": {
    "authentication": {
      "nodes": ["auth.py", "login_user", "refresh_token"],
      "description": "User identity and session management"
    }
  }
}
```

### History
Temporal evolution data:
```json
{
  "history": {
    "auth.py": {
      "churn_score": 0.85,
      "last_major_change": "2024-11-02",
      "notes": "Frequent bug fixes"
    }
  }
}
```

### Risk
Risk assessment per node:
```json
{
  "risk": {
    "auth.login_user": {
      "risk_score": 0.78,
      "reasons": ["High fan-in", "Low test coverage"]
    }
  }
}
```

### Contracts
Public API contracts:
```json
{
  "contracts": {
    "POST /login": {
      "depends_on": ["auth.login_user"],
      "breaking_change_risk": 0.9
    }
  }
}
```

## Architecture

RepoGenome uses a modular architecture with pluggable subsystems:

```
┌─────────────────────────────────────────┐
│         RepoGenome Core                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │Schema   │  │Generator│  │Merger   │ │
│  └─────────┘  └─────────┘  └─────────┘ │
└─────────────────────────────────────────┘
           │          │          │
    ┌──────┴──────┬───┴──────┬───┴──────┐
    │             │          │          │
┌───▼────┐  ┌────▼────┐  ┌──▼───┐  ┌──▼───┐
│Repo    │  │Flow     │  │Intent│  │Chrono│
│Spider  │  │Weaver   │  │Atlas │  │Map   │
└────────┘  └─────────┘  └──────┘  └──────┘
    │
    ├─── Language Analyzers ────────────────┐
    │   Python, TypeScript, Java, Go,       │
    │   C++, Rust, C#, Ruby, PHP            │
    │                                        │
    └─── File Type Analyzers ────────────────┤
        Markdown, JSON, YAML, HTML, CSS,     │
        Shell, SQL                           │
                                            │
```

### Analyzer Architecture

RepoGenome includes specialized analyzers for different file types:

- **Code Analyzers**: Extract functions, classes, imports, and structural relationships
- **Documentation Analyzers**: Extract headings, links, and document structure
- **Config Analyzers**: Parse configuration file structure and keys
- **Web Analyzers**: Extract HTML structure, CSS selectors, and relationships
- **Data Analyzers**: Extract SQL queries, tables, and database structure

All analyzers follow a consistent interface and return structured data that is integrated into the unified RepoGenome graph.

## Language Support

RepoGenome provides comprehensive structural analysis for a wide range of programming languages and file types:

### Programming Languages (Full Structural Analysis)
- **Python** - Functions, classes, imports, call graphs, entry points
- **TypeScript/JavaScript** - Functions, classes, imports, API routes
- **Java** - Classes, methods, packages, imports, entry points
- **Go** - Functions, types (structs/interfaces), packages, imports, entry points
- **C++** - Classes, functions, includes, entry points
- **Rust** - Functions, structs, enums, traits, modules, use statements, entry points
- **C#** - Classes, methods, namespaces, using statements, entry points
- **Ruby** - Classes, modules, methods, requires
- **PHP** - Classes, functions, namespaces, use statements

### File Type Analyzers
- **Markdown** - Headings, links, code blocks, images, lists
- **JSON** - Structure, keys, nested data
- **YAML** - Structure, keys, anchors
- **HTML** - Tags, links, scripts, stylesheets, forms, meta tags
- **CSS** - Selectors, rules, media queries, keyframes
- **Shell Scripts** - Functions, variables, commands, conditionals
- **SQL** - Queries, tables, columns, joins, views, procedures

### Additional File Types
RepoGenome also detects and processes many other file types including:
- Configuration files: `.toml`, `.xml`, `.ini`, `.cfg`
- Documentation: `.rst`, `.txt`
- Web: `.html`, `.css`, `.scss`, `.sass`, `.less`
- And many more (see metadata detection for full list)

All analyzers extract structured information including functions, classes, imports, and relationships, enabling comprehensive cross-language repository analysis.

## Incremental Updates

RepoGenome supports incremental updates to avoid full regeneration:

```python
# Load existing genome
genome = RepoGenome.load("repogenome.json")

# Update incrementally (only analyzes changed files)
generator = RepoGenomeGenerator(repo_path="./myproject")
updated_genome = generator.generate(incremental=True, existing_genome_path=Path("repogenome.json"))

# Save updated genome
updated_genome.save("repogenome.json")
```

## Features

- **Multi-Language Support**: Analyzes code in 9+ programming languages
- **Comprehensive File Type Coverage**: Supports code, documentation, config, web, and data files
- **Cross-Language Analysis**: Builds unified graphs across all languages in a repository
- **Incremental Updates**: Efficient updates by analyzing only changed files
- **Platform Compatibility**: Works on Windows, macOS, and Linux with platform-specific optimizations
- **Extensible Architecture**: Easy to add support for new languages and file types

## Troubleshooting

### macOS Git Hang Issue

If RepoGenome hangs on macOS when using GitPython, it will automatically fall back to subprocess-based git operations. This is handled transparently. To force GitPython usage (not recommended on macOS), set:

```bash
export REPOGENOME_USE_GITPYTHON=true
```

### Large Repositories

For very large repositories, consider:
- Using incremental updates instead of full generation
- Excluding specific subsystems if not needed
- Processing specific file types only

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Adding New Language Support

To add support for a new programming language:

1. Create a new analyzer in `repogenome/analyzers/<language>/`
2. Implement the analyzer following the pattern of existing analyzers
3. Add the language handler in `repogenome/subsystems/repospider.py`
4. Update language detection in `repogenome/core/metadata.py`

## License

MIT License - see LICENSE file for details.

## MCP Server

RepoGenome can run as a Model Context Protocol (MCP) server, exposing repository knowledge as MCP resources and tools for AI agents.

### Starting the MCP Server

```bash
repogenome mcp-server /path/to/repository
```

The server runs on stdio and communicates via the MCP protocol. Configure it in your MCP client to use RepoGenome resources and tools.

### MCP Resources

- **`repogenome://current`** - Full, up-to-date repository genome (JSON)
- **`repogenome://summary`** - Fast boot context (summary section only)
- **`repogenome://diff`** - Changes since last update

### MCP Tools

- **`repogenome.scan`** - Generate or regenerate RepoGenome
  - Parameters: `scope` (full/structure/flows/history), `incremental` (boolean)
  
- **`repogenome.query`** - Query RepoGenome graph
  - Parameters: `query` (string), `format` (json/graph)
  - Supports natural language queries: "find all nodes related to authentication"
  
- **`repogenome.impact`** - Simulate impact of proposed changes
  - Parameters: `affected_nodes` (array), `operation` (modify/delete/add)
  - Returns: Risk score, affected flows, requires_approval flag
  
- **`repogenome.update`** - Incrementally update genome after code changes
  - Parameters: `added_nodes`, `removed_nodes`, `updated_edges`, `reason`
  - **Mandatory**: Must be called after any code edits
  
- **`repogenome.validate`** - Ensure RepoGenome matches repo state
  - Returns: Validation result with consistency checks

### Agent Contract (MCP)

When using RepoGenome via MCP, agents must follow these rules:

1. **Load `repogenome://current` at session start** - Always read the genome first
2. **Cite RepoGenome when reasoning** - Reference specific nodes/edges when making claims
3. **Use `repogenome.impact` before edits** - Check impact before modifying code
4. **Call `repogenome.update` after edits** - Keep genome current after changes
5. **Refuse actions if validation fails** - Stop if `repogenome.validate` fails

The MCP server enforces these rules through contract middleware.

### Configuring MCP Server with Coding Agents

#### Cursor

1. Open Cursor Settings (File → Preferences → Settings)
2. Navigate to "MCP Servers" or "Model Context Protocol"
3. Add RepoGenome server configuration:

```json
{
  "mcpServers": {
    "repogenome": {
      "command": "repogenome",
      "args": ["mcp-server", "${workspaceFolder}"],
      "env": {}
    }
  }
}
```

4. Restart Cursor to load the MCP server
5. The RepoGenome resources and tools will be available in the AI chat

**Usage in Cursor:**
- Ask: "Load repogenome://current to understand the codebase structure"
- Query: "Use repogenome.query to find all authentication-related functions"
- Before editing: "Check impact with repogenome.impact for nodes: auth.login_user"
- After editing: "Update genome with repogenome.update"

#### Claude Desktop (Claude Code)

1. Open Claude Desktop settings
2. Navigate to MCP configuration (usually in `~/.config/claude-desktop/mcp.json` or similar)
3. Add RepoGenome server:

```json
{
  "mcpServers": {
    "repogenome": {
      "command": "repogenome",
      "args": ["mcp-server"],
      "cwd": "/path/to/your/repository"
    }
  }
}
```

4. Restart Claude Desktop
5. Claude will have access to RepoGenome resources and tools

**Usage with Claude:**
- Claude automatically loads `repogenome://summary` for quick context
- Use tools via natural language: "What functions call auth.login_user?"
- Impact analysis: "What breaks if I modify db.connect?"

#### Qwen Code

1. Open Qwen Code settings
2. Find MCP configuration section
3. Add server configuration:

```json
{
  "mcp": {
    "servers": {
      "repogenome": {
        "command": "repogenome",
        "args": ["mcp-server"],
        "workingDirectory": "${workspaceRoot}"
      }
    }
  }
}
```

4. Restart Qwen Code
5. Qwen will use RepoGenome for code understanding

**Usage with Qwen:**
- Qwen reads `repogenome://summary` for fast boot
- Deep queries use `repogenome.query` on demand
- Updates genome automatically after code changes

#### Generic MCP Client Configuration

For any MCP-compatible client, use this configuration:

```json
{
  "mcpServers": {
    "repogenome": {
      "command": "repogenome",
      "args": ["mcp-server", "/absolute/path/to/repository"],
      "env": {
        "REPOGENOME_REPO_PATH": "/absolute/path/to/repository"
      }
    }
  }
}
```

**Environment Variables:**
- `REPOGENOME_REPO_PATH`: Repository root path (if not provided as argument)

**Verifying MCP Server Connection:**

1. Check server is running: The MCP client should show RepoGenome in available servers
2. Test resources: Try loading `repogenome://summary`
3. Test tools: Call `repogenome.validate` to verify connection

**Troubleshooting:**

- **Server not found**: Ensure `repogenome` is in your PATH (`pip install -e .`)
- **Permission errors**: Check repository path is accessible
- **No genome found**: Run `repogenome generate` first to create initial genome
- **Connection timeout**: Verify MCP client supports stdio servers

## Agent Contract

Any agent using RepoGenome should follow these rules:

1. **Load RepoGenome before acting** - Always read the genome to understand the codebase
2. **Cite RepoGenome when making claims** - Reference specific nodes, edges, or flows
3. **Update RepoGenome after changes** - Keep the genome current

Failure to follow these rules leads to hallucination and incorrect behavior.

