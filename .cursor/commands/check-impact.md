# Check Change Impact

Analyze the impact of proposed code changes before making them.

## Description

Simulates the impact of modifying, deleting, or adding nodes in the codebase. Identifies affected flows, dependencies, and calculates risk scores to help make informed decisions about changes.

## Objective

- Assess the impact of proposed changes
- Identify affected execution paths and flows
- Calculate risk scores based on dependencies
- Determine if changes require approval
- Prevent breaking changes by understanding dependencies

## Requirements

- `repogenome.json` file in repository root
- Valid node IDs for affected nodes

## Parameters

- **affected_nodes** (array, required): List of node IDs that will be affected
  - Examples: `["auth.login_user", "db.get_user"]`
- **operation** (string): Type of operation
  - `"modify"`: Modifying existing nodes (default)
  - `"delete"`: Deleting nodes
  - `"add"`: Adding new nodes

## Output

- **risk_score** (float): Risk score from 0.0 to 1.0
  - Higher scores indicate more risk
- **affected_flows** (array): List of execution paths that will be affected
- **affected_nodes** (array): List of nodes that depend on the changed nodes
- **requires_approval** (boolean): Whether the change requires approval
- **warnings** (array): List of warnings about potential issues

## Usage

Use the `repogenome.impact` MCP tool:

**Before modifying a function:**
```python
repogenome.impact(
    affected_nodes=["auth.login_user"],
    operation="modify"
)
```

**Before deleting a file:**
```python
repogenome.impact(
    affected_nodes=["legacy/billing_old.py"],
    operation="delete"
)
```

**Multiple nodes:**
```python
repogenome.impact(
    affected_nodes=["auth.login_user", "auth.refresh_token", "auth.logout"],
    operation="modify"
)
```

## Best Practices

1. **Always check impact** before making significant changes
2. **Review affected flows** to understand downstream effects
3. **Consider risk score** when planning changes
4. **Check requires_approval** flag for critical changes
5. **Review warnings** to identify potential issues

## Next Steps

After checking impact:
- If risk is acceptable, proceed with changes
- If risk is high, consider alternative approaches
- Update genome after changes using `repogenome.update()`

