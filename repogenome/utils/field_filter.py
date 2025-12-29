"""Field filtering utilities for context reduction."""

from typing import Any, Dict, List, Optional, Set, Union


# Field aliases for compact queries
FIELD_ALIASES: Dict[str, str] = {
    # Node fields
    "t": "type",
    "f": "file",
    "lang": "language",
    "v": "visibility",
    "s": "summary",
    "c": "criticality",
    # Edge fields
    "fr": "from",
    "to": "to",
    # Common fields
    "id": "id",
    "n": "nodes",
    "d": "description",
}


def expand_field_aliases(fields: Union[str, List[str]]) -> List[str]:
    """
    Expand field aliases to full field names.
    
    Args:
        fields: Field names or aliases (string or list)
        
    Returns:
        List of expanded field names
    """
    if isinstance(fields, str):
        # Handle comma-separated string
        field_list = [f.strip() for f in fields.split(",") if f.strip()]
    else:
        field_list = list(fields)
    
    expanded = []
    for field in field_list:
        # Handle dot notation (e.g., "node.id")
        if "." in field:
            parts = field.split(".")
            expanded_parts = []
            for part in parts:
                expanded_parts.append(FIELD_ALIASES.get(part, part))
            expanded.append(".".join(expanded_parts))
        else:
            # Check if it's an alias
            expanded.append(FIELD_ALIASES.get(field, field))
    
    return expanded


def parse_field_spec(field_spec: str) -> Dict[str, Any]:
    """
    Parse a field specification into filter rules.
    
    Supports:
    - Simple fields: "id", "type"
    - Dot notation: "node.id", "edges.from"
    - Wildcards: "node.*"
    - Exclusions: "-summary"
    
    Args:
        field_spec: Field specification string
        
    Returns:
        Dict with 'include', 'exclude', 'wildcard' keys
    """
    is_exclude = field_spec.startswith("-")
    field = field_spec.lstrip("-")
    
    if field.endswith(".*"):
        return {
            "type": "wildcard",
            "prefix": field[:-2],
            "exclude": is_exclude,
        }
    
    return {
        "type": "field",
        "path": field.split("."),
        "exclude": is_exclude,
    }


def filter_fields(
    data: Any,
    fields: Optional[Union[str, List[str]]] = None,
    context: Optional[str] = None,
) -> Any:
    """
    Filter data structure to include only specified fields.
    
    Args:
        data: Data structure to filter (dict, list, or primitive)
        fields: Field specifications (None = all fields, "*" = all fields)
        context: Context for field expansion (e.g., "node", "edge")
        
    Returns:
        Filtered data structure
    """
    if fields is None or fields == "*" or fields == ["*"]:
        return data
    
    if not isinstance(data, (dict, list)):
        return data
    
    # Expand aliases
    if isinstance(fields, str):
        field_list = [f.strip() for f in fields.split(",") if f.strip()]
    else:
        field_list = list(fields)
    
    # Parse field specifications
    field_rules = [parse_field_spec(f) for f in field_list]
    
    # Separate includes and excludes
    includes = [r for r in field_rules if not r.get("exclude", False)]
    excludes = [r for r in field_rules if r.get("exclude", False)]
    
    # If no includes specified, include all (then apply excludes)
    include_all = len(includes) == 0
    
    if isinstance(data, dict):
        return _filter_dict(data, includes, excludes, include_all, context or "")
    elif isinstance(data, list):
        return [
            filter_fields(item, fields, context)
            if isinstance(item, (dict, list))
            else item
            for item in data
        ]
    
    return data


def _filter_dict(
    data: Dict[str, Any],
    includes: List[Dict[str, Any]],
    excludes: List[Dict[str, Any]],
    include_all: bool,
    context: str,
) -> Dict[str, Any]:
    """Filter a dictionary based on field rules."""
    result: Dict[str, Any] = {}
    
    for key, value in data.items():
        # Check if key should be excluded
        if _should_exclude(key, excludes, context):
            continue
        
        # Check if key should be included
        if not include_all and not _should_include(key, includes, context):
            continue
        
        # Handle nested structures
        if isinstance(value, dict):
            # Check if we need to filter nested fields
            nested_includes = _get_nested_rules(key, includes, context)
            nested_excludes = _get_nested_rules(key, excludes, context)
            
            if nested_includes or nested_excludes:
                nested_include_all = len(nested_includes) == 0
                result[key] = _filter_dict(value, nested_includes, nested_excludes, nested_include_all, key)
            else:
                result[key] = value
        elif isinstance(value, list):
            result[key] = [
                filter_fields(item, None, key) if isinstance(item, (dict, list)) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


def _should_include(key: str, includes: List[Dict[str, Any]], context: str) -> bool:
    """Check if a key should be included based on include rules."""
    if not includes:
        return True
    
    for rule in includes:
        if rule["type"] == "wildcard":
            prefix = rule["prefix"]
            if prefix == "" or key.startswith(prefix + "."):
                return True
        elif rule["type"] == "field":
            path = rule["path"]
            if len(path) == 1:
                # Top-level field
                if path[0] == key:
                    return True
            elif len(path) > 1 and path[0] == context:
                # Nested field matching context
                if path[1] == key:
                    return True
            elif context == "" and path[0] == key:
                # Top-level match
                return True
    
    return False


def _should_exclude(key: str, excludes: List[Dict[str, Any]], context: str) -> bool:
    """Check if a key should be excluded based on exclude rules."""
    for rule in excludes:
        if rule["type"] == "wildcard":
            prefix = rule["prefix"]
            if prefix == "" or key.startswith(prefix + "."):
                return True
        elif rule["type"] == "field":
            path = rule["path"]
            if len(path) == 1:
                if path[0] == key:
                    return True
            elif len(path) > 1 and path[0] == context:
                if path[1] == key:
                    return True
            elif context == "" and path[0] == key:
                return True
    
    return False


def _get_nested_rules(
    key: str, rules: List[Dict[str, Any]], context: str
) -> List[Dict[str, Any]]:
    """Get rules that apply to a nested key."""
    nested_rules = []
    
    for rule in rules:
        if rule["type"] == "field" and len(rule["path"]) > 1:
            if rule["path"][0] == key or (context == "" and rule["path"][0] == key):
                # Create nested rule
                nested_rule = rule.copy()
                nested_rule["path"] = rule["path"][1:]
                nested_rules.append(nested_rule)
        elif rule["type"] == "wildcard":
            prefix = rule["prefix"]
            if prefix == key or (prefix and key.startswith(prefix + ".")):
                nested_rules.append(rule)
    
    return nested_rules

