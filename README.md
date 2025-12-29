<div align="center">

[![Version](https://img.shields.io/badge/version-0.7.0-blue.svg?style=for-the-badge&logo=github)](https://github.com/End3r27/RepoGenome/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Stars](https://img.shields.io/github/stars/End3r27/RepoGenome?style=for-the-badge&logo=github&color=yellow)](https://github.com/End3r27/RepoGenome/stargazers)
[![Forks](https://img.shields.io/github/forks/End3r27/RepoGenome?style=for-the-badge&logo=github&color=blue)](https://github.com/End3r27/RepoGenome/network/members)
[![Issues](https://img.shields.io/github/issues/End3r27/RepoGenome?style=for-the-badge&logo=github&color=orange)](https://github.com/End3r27/RepoGenome/issues)


</div>

---

<div align="center">

# 🧬 RepoGenome

### Unified Repository Intelligence Artifact Generator

*A continuously evolving, machine-readable knowledge organism that encodes the structure, behavior, intent, and history of your codebase.*

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## ✨ Features

RepoGenome generates a comprehensive JSON artifact (`repogenome.json`) that combines multiple analysis perspectives:

- **🔍 RepoSpider** - Structural graph analysis (files, symbols, dependencies)
- **🌊 FlowWeaver** - Runtime execution paths and side effects tracking
- **🗺️ IntentAtlas** - Domain concepts and responsibility mapping
- **⏱️ ChronoMap** - Temporal evolution and churn analysis
- **🧪 TestGalaxy** - Test coverage analysis (optional)
- **📋 ContractLens** - Public API contract analysis

**Key Capabilities:**
- **Multi-Language Support** - Analyzes code in 9+ programming languages
- **Comprehensive File Type Coverage** - Supports code, documentation, config, web, and data files
- **Cross-Language Analysis** - Builds unified graphs across all languages in a repository
- **Incremental Updates** - Efficient updates by analyzing only changed files
- **Platform Compatibility** - Works on Windows, macOS, and Linux with platform-specific optimizations
- **Extensible Architecture** - Easy to add support for new languages and file types
- **MCP Server Integration** - Expose repository knowledge to AI agents via Model Context Protocol
- **Context Optimization** - Compact modes, compression, and streaming for LLM-friendly output (new in v0.7.0)
- **Advanced Query Language** - SQL-like and GraphQL-style queries for complex genome queries (new in v0.7.0)
- **Graph Database Backend** - Optional SQLite backend for large repositories (new in v0.7.0)
- **Watch Mode** - Auto-regenerate genome on file changes (new in v0.7.0)
- **Progress Tracking** - Real-time progress bars for long-running operations (new in v0.7.0)

## 📥 Installation

### Prerequisites

- Python 3.8 or higher
- Git (for repository analysis)

### Install from Source

```bash
git clone https://github.com/End3r27/RepoGenome
cd RepoGenome
pip install -e .
```

### Optional Dependencies

For enhanced TypeScript/JavaScript analysis:
```bash
pip install tree-sitter-typescript
```

## 🚀 Quick Start

### CLI Usage

Generate a RepoGenome for your repository:

```bash
repogenome generate /path/to/repository
```

This creates a `repogenome.json` file in the repository root.

**Additional CLI Commands:**

```bash
# Generate with debug logging
repogenome generate /path/to/repository --log debug

# Generate with compression options (reduce file size)
repogenome generate /path/to/repository --compact --minify --compress

# Generate ultra-compact lite version (essential data only)
repogenome generate /path/to/repository --lite

# Update an existing genome incrementally
repogenome update /path/to/repository

# Validate a genome file
repogenome validate repogenome.json

# Compare two genomes
repogenome diff old_genome.json new_genome.json

# Watch repository and auto-regenerate on changes
repogenome watch /path/to/repository --debounce 2.0

# Start MCP server for AI agent integration
repogenome mcp-server /path/to/repository
```

> **Note for macOS users**: RepoGenome automatically uses subprocess-based git operations on macOS to avoid hanging issues. To force GitPython usage, set `REPOGENOME_USE_GITPYTHON=true`.

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

### Incremental Updates

RepoGenome supports incremental updates to avoid full regeneration:

```python
from pathlib import Path
from repogenome import RepoGenomeGenerator

# Load existing genome
genome = Genome.load("repogenome.json")

# Update incrementally (only analyzes changed files)
generator = RepoGenomeGenerator(repo_path="./myproject")
updated_genome = generator.generate(
    incremental=True, 
    existing_genome_path=Path("repogenome.json")
)

# Save updated genome
updated_genome.save("repogenome.json")
```

### Advanced Features (v0.7.0+)

#### Context Optimization

RepoGenome now supports multiple compression modes to reduce file size for LLM context windows:

```python
# Compact mode: Use short field names
genome.save("genome.json", compact=True)

# Minified: Remove indentation
genome.save("genome.json", minify=True)

# Lite mode: Only essential fields
genome.save("genome.json", lite=True)

# Gzip compression
genome.save("genome.json", compress=True)

# Combine options for maximum compression
genome.save("genome.json", compact=True, minify=True, compress=True, exclude_defaults=True)
```

#### Advanced Query Language

Query genomes using SQL-like or GraphQL-style syntax:

```python
from repogenome.core.advanced_query import AdvancedQuery

query = AdvancedQuery(genome)

# SQL-like queries
results = query.execute("SELECT * FROM nodes WHERE type='function' AND criticality>0.8")

# GraphQL-style queries
results = query.execute("{ nodes(type: function, criticality_gt: 0.8) { id, file, summary } }")

# Natural language queries
results = query.execute("find all authentication functions")
```

#### Graph Database Backend

For large repositories, use SQLite backend for efficient storage and querying:

```python
from repogenome.core.db_backend import SQLiteBackend

# Save to database
backend = SQLiteBackend("genome.db")
backend.save_genome(genome)

# Load from database
genome = backend.load_genome()

# Query nodes
results = backend.query_nodes({"type": "function", "criticality__gt": 0.8})

# Query edges
edges = backend.query_edges(from_node="auth.login_user", edge_type="calls")
```

#### Security Analysis

The security subsystem detects vulnerabilities, secrets, and permission issues:

```python
from repogenome.core.generator import RepoGenomeGenerator

generator = RepoGenomeGenerator(repo_path="./myproject")
genome = generator.generate()

# Security findings are in the security section (if enabled)
if "security" in genome.__dict__:
    for file_id, findings in genome.security.items():
        print(f"{file_id}: {findings['severity']} - {len(findings['findings'])} issues")
```

#### Watch Mode

Automatically regenerate genome when files change:

```bash
# Watch repository and auto-regenerate
repogenome watch /path/to/repository --debounce 2.0
```

The watch mode monitors file changes and automatically regenerates the genome after a debounce period.

## 📚 Documentation

### RepoGenome Schema

The `repogenome.json` file contains the following sections:

<details>
<summary><b>Metadata</b> - Repository and generation information</summary>

```json
{
  "metadata": {
    "generated_at": "2025-01-12T18:42:00Z",
    "repo_hash": "a8f3c1...",
    "languages": ["Python", "TypeScript", "Java", "Go", "Rust"],
    "frameworks": ["FastAPI", "React"],
    "repogenome_version": "0.7.0"
  }
}
```

</details>

<details>
<summary><b>Summary</b> - High-level overview for quick agent boot</summary>

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

</details>

<details>
<summary><b>Nodes</b> - Every meaningful entity in the codebase</summary>

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

</details>

<details>
<summary><b>Edges</b> - Relationships between nodes</summary>

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

</details>

<details>
<summary><b>Flows</b> - Runtime execution paths</summary>

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

</details>

<details>
<summary><b>Concepts</b> - Domain groupings</summary>

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

</details>

<details>
<summary><b>History</b> - Temporal evolution data</summary>

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

</details>

<details>
<summary><b>Risk</b> - Risk assessment per node</summary>

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

</details>

<details>
<summary><b>Contracts</b> - Public API contracts</summary>

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

</details>

## 🏗️ Architecture

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

## 🌐 Language Support

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

## 🔌 MCP Server

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

<details>
<summary><b>Cursor</b> - Click to expand configuration</summary>

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

</details>

<details>
<summary><b>Claude Desktop (Claude Code)</b> - Click to expand configuration</summary>

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

</details>

<details>
<summary><b>Qwen Code</b> - Click to expand configuration</summary>

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

</details>

<details>
<summary><b>Generic MCP Client Configuration</b> - Click to expand</summary>

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

</details>

### Agent Contract

Any agent using RepoGenome should follow these rules:

1. **Load RepoGenome before acting** - Always read the genome to understand the codebase
2. **Cite RepoGenome when making claims** - Reference specific nodes, edges, or flows
3. **Update RepoGenome after changes** - Keep the genome current

Failure to follow these rules leads to hallucination and incorrect behavior.

## 🧪 Testing

RepoGenome includes a test suite using pytest. To run tests:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=repogenome --cov-report=html
```

## 🔧 Troubleshooting

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

## 🤝 Contributing

Contributions are welcome! We appreciate your help in making RepoGenome better.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Adding New Language Support

To add support for a new programming language:

1. Create a new analyzer in `repogenome/analyzers/<language>/`
2. Implement the analyzer following the pattern of existing analyzers
3. Add the language handler in `repogenome/subsystems/repospider.py`
4. Update language detection in `repogenome/core/metadata.py`
5. Add tests for the new analyzer
6. Update this README with the new language

## 🛣️ Roadmap

Future enhancements and planned features:

- [x] Real-time genome updates via file watchers (✅ v0.7.0)
- [x] Advanced query language for genome exploration (✅ v0.7.0)
- [x] Performance optimizations for very large repositories (✅ v0.7.0)
- [ ] Enhanced visualization tools for genome exploration
- [ ] Support for additional programming languages
- [ ] Integration with popular IDEs and editors (VS Code extension)
- [ ] Cloud-based genome storage and sharing
- [ ] Machine learning models for code understanding

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Show Your Support

If you find RepoGenome useful, please consider giving it a star! It helps others discover the project.

---

<div align="center">

**Made with ❤️ by End3r27**

[Report Bug](https://github.com/End3r27/RepoGenome/issues) • [Request Feature](https://github.com/End3r27/RepoGenome/issues) • [Documentation](#-documentation)

</div>
