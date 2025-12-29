# Validate RepoGenome

Validate that the RepoGenome matches the current repository state.

## Description

Checks the consistency and validity of the `repogenome.json` file against the actual repository state. Ensures the genome is up-to-date and accurate.

## Objective

- Verify that `repogenome.json` exists and is valid
- Check that genome metadata matches repository state
- Validate node and edge consistency
- Detect any discrepancies between genome and actual codebase
- Ensure all referenced files still exist

## Requirements

- `repogenome.json` file in repository root
- Repository must be accessible

## Validation Checks

- Genome file exists and is valid JSON
- Repository hash matches current state
- All referenced files exist in repository
- Node IDs are consistent
- Edge references are valid
- Metadata is current

## Output

- Validation result with status (valid/invalid)
- List of any inconsistencies found
- Recommendations for fixing issues (if any)

## Usage

Use the `repogenome.validate` MCP tool:
```python
repogenome.validate()
```

Or run via CLI:
```bash
repogenome validate repogenome.json
```

## When to Use

- Before starting a new analysis session
- If you suspect the genome is stale
- After repository operations (merges, rebases, etc.)
- Periodically to ensure genome accuracy

## Next Steps

If validation fails:
1. Run `repogenome.scan(incremental=true)` to update the genome
2. Or run full regeneration if incremental update doesn't resolve issues

