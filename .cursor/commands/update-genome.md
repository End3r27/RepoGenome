# Update RepoGenome

Incrementally update an existing RepoGenome after code changes.

## Description

Updates the RepoGenome artifact to reflect recent code changes. This is more efficient than full regeneration as it only analyzes changed files and affected subsystems.

## Objective

- Update the existing `repogenome.json` file with recent changes
- Re-analyze only modified files and their dependencies
- Update affected subsystems (RepoSpider, FlowWeaver, etc.) based on change patterns
- Maintain consistency with the repository state

## Requirements

- Existing `repogenome.json` file in repository root
- Repository must be accessible
- Git repository (for change detection)

## Process

1. Detect changed files using Git
2. Identify affected subsystems based on change patterns
3. Re-analyze only changed files and their dependencies
4. Merge updates into existing genome
5. Update metadata and timestamps

## Output

- Updated `repogenome.json` file
- Preserves existing data for unchanged files
- Updates nodes, edges, and subsystem data for changed areas

## Usage

**IMPORTANT**: Always call this after making code changes to keep the genome current.

Use the `repogenome.update` MCP tool:
```python
repogenome.update(reason="Added new authentication function")
```

Or run via CLI:
```bash
repogenome update .
```

## Notes

- Incremental updates are significantly faster than full regeneration
- Only affected subsystems are re-analyzed (up to 80% reduction in processing time)
- Change detection is based on file modification times and Git history

