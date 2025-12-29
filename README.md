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
git clone https://github.com/yourusername/repogenome
cd repogenome
pip install -e .
```

## Quick Start

### CLI Usage

Generate a RepoGenome for your repository:

```bash
repogenome generate /path/to/repository
```

This creates a `repogenome.json` file in the repository root.

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
    "languages": ["Python", "TypeScript"],
    "frameworks": ["FastAPI", "React"],
    "repogenome_version": "0.1.0"
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
```

## Language Support

Currently supported languages:
- Python (full support)
- TypeScript/JavaScript (basic support)

More languages can be added by implementing language-specific analyzers.

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Agent Contract

Any agent using RepoGenome should follow these rules:

1. **Load RepoGenome before acting** - Always read the genome to understand the codebase
2. **Cite RepoGenome when making claims** - Reference specific nodes, edges, or flows
3. **Update RepoGenome after changes** - Keep the genome current

Failure to follow these rules leads to hallucination and incorrect behavior.

