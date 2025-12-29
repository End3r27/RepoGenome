# Generate RepoGenome

Generate or regenerate a RepoGenome for the current repository.

## Description

Creates a comprehensive `repogenome.json` file that encodes the structure, behavior, intent, and history of the codebase. This is the foundation for all RepoGenome-based analysis.

## Objective

- Generate a complete RepoGenome artifact for the repository
- Extract structural information (files, functions, classes, dependencies)
- Analyze runtime execution paths and side effects (if FlowWeaver enabled)
- Map domain concepts and responsibilities (if IntentAtlas enabled)
- Track temporal evolution and churn (if ChronoMap enabled)
- Create a machine-readable knowledge graph of the codebase

## Requirements

- Repository must be accessible
- Python 3.8+ with RepoGenome installed
- Git repository (for history analysis if ChronoMap enabled)

## Options

- **Incremental**: Update existing genome instead of full regeneration
- **Compact**: Use short field names to reduce file size
- **Minify**: Remove indentation from JSON output
- **Lite**: Ultra-compact mode with only essential fields
- **Compress**: Compress output with gzip (.json.gz)
- **Subsystems**: Enable specific subsystems (RepoSpider, FlowWeaver, IntentAtlas, ChronoMap, TestGalaxy, ContractLens)
- **Exclude Subsystems**: Exclude specific subsystems
- **Max Summary Length**: Limit summary text length (default: 200, 0 = no summaries)
- **Exclude Defaults**: Exclude fields with default values

## Output

- `repogenome.json` file in the repository root (or specified output path)
- Contains nodes (files, functions, classes, etc.), edges (relationships), and optional subsystems data
- File size varies based on repository size and options selected

## Usage

Use the `repogenome.scan` MCP tool or run:
```bash
repogenome generate .
```

For incremental update:
```bash
repogenome generate . --incremental
```

For maximum compression:
```bash
repogenome generate . --compact --minify --compress
```

