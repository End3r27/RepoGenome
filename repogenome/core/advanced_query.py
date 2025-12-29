"""
Advanced query language for RepoGenome.

Supports SQL-like and GraphQL-style queries for complex genome queries.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from repogenome.core.schema import RepoGenome, Node, Edge, NodeType, EdgeType


class AdvancedQuery:
    """Advanced query parser and executor for RepoGenome."""

    def __init__(self, genome: RepoGenome):
        """
        Initialize advanced query interface.

        Args:
            genome: RepoGenome to query
        """
        self.genome = genome

    def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute a query string.

        Supports:
        - SQL-like: "SELECT nodes WHERE type='function' AND criticality>0.8"
        - GraphQL-like: "{ nodes(type: function, criticality_gt: 0.8) { id, file, summary } }"

        Args:
            query: Query string

        Returns:
            Query results
        """
        query = query.strip()

        # Try GraphQL-style first
        if query.startswith("{"):
            return self._execute_graphql(query)

        # Try SQL-like
        if query.upper().startswith("SELECT"):
            return self._execute_sql(query)

        # Fallback to simple query
        return self._execute_simple(query)

    def _execute_sql(self, query: str) -> Dict[str, Any]:
        """Execute SQL-like query."""
        # Parse: SELECT <fields> FROM <source> WHERE <conditions> ORDER BY <field> LIMIT <n>
        query_upper = query.upper()

        # Extract SELECT clause
        select_match = re.search(r"SELECT\s+(.+?)\s+FROM", query_upper, re.IGNORECASE)
        if not select_match:
            return {"error": "Invalid SELECT query: missing FROM clause"}

        fields_str = select_match.group(1).strip()
        fields = [f.strip() for f in fields_str.split(",")] if fields_str != "*" else None

        # Extract FROM clause
        from_match = re.search(r"FROM\s+(\w+)", query_upper, re.IGNORECASE)
        if not from_match:
            return {"error": "Invalid SELECT query: missing FROM clause"}

        source = from_match.group(1).lower()

        # Extract WHERE clause
        where_match = re.search(r"WHERE\s+(.+?)(?:\s+ORDER|\s+LIMIT|$)", query_upper, re.IGNORECASE)
        conditions = {}
        if where_match:
            where_clause = where_match.group(1).strip()
            conditions = self._parse_where_clause(where_clause)

        # Extract ORDER BY
        order_match = re.search(r"ORDER\s+BY\s+(\w+)(?:\s+(ASC|DESC))?", query_upper, re.IGNORECASE)
        order_by = None
        order_dir = "asc"
        if order_match:
            order_by = order_match.group(1).lower()
            if order_match.group(2):
                order_dir = order_match.group(2).lower()

        # Extract LIMIT
        limit_match = re.search(r"LIMIT\s+(\d+)", query_upper, re.IGNORECASE)
        limit = None
        if limit_match:
            limit = int(limit_match.group(1))

        # Execute query
        if source == "nodes":
            results = self._query_nodes_sql(conditions, fields, order_by, order_dir, limit)
        elif source == "edges":
            results = self._query_edges_sql(conditions, fields, order_by, order_dir, limit)
        else:
            return {"error": f"Unknown source: {source}"}

        return {"type": source, "count": len(results), "results": results}

    def _execute_graphql(self, query: str) -> Dict[str, Any]:
        """Execute GraphQL-style query."""
        # Simple GraphQL parser
        # Format: { nodes(type: function, criticality_gt: 0.8) { id, file, summary } }

        # Extract query type
        query_type_match = re.search(r"\{\s*(\w+)\s*\(", query)
        if not query_type_match:
            return {"error": "Invalid GraphQL query"}

        query_type = query_type_match.group(1).lower()

        # Extract arguments
        args_match = re.search(r"\(([^)]+)\)", query)
        conditions = {}
        if args_match:
            args_str = args_match.group(1)
            conditions = self._parse_graphql_args(args_str)

        # Extract fields
        fields_match = re.search(r"\{\s*([^}]+)\s*\}", query)
        fields = None
        if fields_match:
            fields_str = fields_match.group(1)
            fields = [f.strip() for f in fields_str.split(",")]

        # Execute query
        if query_type == "nodes":
            results = self._query_nodes_graphql(conditions, fields)
        elif query_type == "edges":
            results = self._query_edges_graphql(conditions, fields)
        else:
            return {"error": f"Unknown query type: {query_type}"}

        return {"type": query_type, "count": len(results), "results": results}

    def _execute_simple(self, query: str) -> Dict[str, Any]:
        """Execute simple query (fallback)."""
        # Simple keyword search
        query_lower = query.lower()
        results = []

        for node_id, node in self.genome.nodes.items():
            node_dict = node.model_dump() if hasattr(node, "model_dump") else node
            summary = str(node_dict.get("summary", "")).lower()
            file_path = str(node_dict.get("file", "")).lower()

            if any(word in summary or word in file_path or word in node_id.lower() for word in query_lower.split()):
                results.append({"id": node_id, **node_dict})

        return {"type": "search", "count": len(results), "results": results[:50]}

    def _parse_where_clause(self, where_clause: str) -> Dict[str, Any]:
        """Parse WHERE clause conditions."""
        conditions = {}
        
        # Split by AND/OR
        parts = re.split(r"\s+(AND|OR)\s+", where_clause, flags=re.IGNORECASE)
        
        for part in parts:
            part = part.strip()
            if part.upper() in ["AND", "OR"]:
                continue

            # Handle operators: =, !=, >, <, >=, <=, LIKE, IN
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                conditions[key] = value
            elif "!=" in part:
                key, value = part.split("!=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                conditions[f"{key}__ne"] = value
            elif ">=" in part:
                key, value = part.split(">=", 1)
                key = key.strip()
                value = value.strip()
                try:
                    conditions[f"{key}__gte"] = float(value)
                except ValueError:
                    pass
            elif "<=" in part:
                key, value = part.split("<=", 1)
                key = key.strip()
                value = value.strip()
                try:
                    conditions[f"{key}__lte"] = float(value)
                except ValueError:
                    pass
            elif ">" in part:
                key, value = part.split(">", 1)
                key = key.strip()
                value = value.strip()
                try:
                    conditions[f"{key}__gt"] = float(value)
                except ValueError:
                    pass
            elif "<" in part:
                key, value = part.split("<", 1)
                key = key.strip()
                value = value.strip()
                try:
                    conditions[f"{key}__lt"] = float(value)
                except ValueError:
                    pass
            elif "LIKE" in part.upper():
                key, pattern = re.split(r"\s+LIKE\s+", part, flags=re.IGNORECASE)
                key = key.strip()
                pattern = pattern.strip().strip("'\"")
                conditions[f"{key}__like"] = pattern
            elif "IN" in part.upper():
                match = re.search(r"(\w+)\s+IN\s+\(([^)]+)\)", part, re.IGNORECASE)
                if match:
                    key = match.group(1)
                    values = [v.strip().strip("'\"") for v in match.group(2).split(",")]
                    conditions[f"{key}__in"] = values

        return conditions

    def _parse_graphql_args(self, args_str: str) -> Dict[str, Any]:
        """Parse GraphQL arguments."""
        conditions = {}
        
        # Split by comma
        parts = [p.strip() for p in args_str.split(",")]
        
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                
                # Handle operators (e.g., criticality_gt)
                if "_gt" in key:
                    key = key.replace("_gt", "")
                    try:
                        conditions[f"{key}__gt"] = float(value)
                    except ValueError:
                        pass
                elif "_gte" in key:
                    key = key.replace("_gte", "")
                    try:
                        conditions[f"{key}__gte"] = float(value)
                    except ValueError:
                        pass
                elif "_lt" in key:
                    key = key.replace("_lt", "")
                    try:
                        conditions[f"{key}__lt"] = float(value)
                    except ValueError:
                        pass
                elif "_lte" in key:
                    key = key.replace("_lte", "")
                    try:
                        conditions[f"{key}__lte"] = float(value)
                    except ValueError:
                        pass
                else:
                    conditions[key] = value

        return conditions

    def _query_nodes_sql(
        self,
        conditions: Dict[str, Any],
        fields: Optional[List[str]],
        order_by: Optional[str],
        order_dir: str,
        limit: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Query nodes with SQL-like interface."""
        results = []

        for node_id, node in self.genome.nodes.items():
            if self._match_conditions(node, conditions):
                node_dict = node.model_dump() if hasattr(node, "model_dump") else {}
                
                # Select fields
                if fields:
                    filtered_dict = {"id": node_id}
                    for field in fields:
                        if field in node_dict:
                            filtered_dict[field] = node_dict[field]
                    results.append(filtered_dict)
                else:
                    results.append({"id": node_id, **node_dict})

        # Sort
        if order_by:
            reverse = order_dir == "desc"
            try:
                results.sort(key=lambda x: x.get(order_by, ""), reverse=reverse)
            except Exception:
                pass

        # Limit
        if limit:
            results = results[:limit]

        return results

    def _query_edges_sql(
        self,
        conditions: Dict[str, Any],
        fields: Optional[List[str]],
        order_by: Optional[str],
        order_dir: str,
        limit: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Query edges with SQL-like interface."""
        results = []

        for edge in self.genome.edges:
            edge_dict = edge.model_dump(by_alias=True)
            if self._match_edge_conditions(edge, conditions):
                # Select fields
                if fields:
                    filtered_dict = {}
                    for field in fields:
                        if field in edge_dict:
                            filtered_dict[field] = edge_dict[field]
                    results.append(filtered_dict)
                else:
                    results.append(edge_dict)

        # Sort
        if order_by:
            reverse = order_dir == "desc"
            try:
                results.sort(key=lambda x: x.get(order_by, ""), reverse=reverse)
            except Exception:
                pass

        # Limit
        if limit:
            results = results[:limit]

        return results

    def _query_nodes_graphql(
        self, conditions: Dict[str, Any], fields: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Query nodes with GraphQL-like interface."""
        results = []

        for node_id, node in self.genome.nodes.items():
            if self._match_conditions(node, conditions):
                node_dict = node.model_dump() if hasattr(node, "model_dump") else {}
                
                # Select fields
                if fields:
                    filtered_dict = {"id": node_id}
                    for field in fields:
                        if field in node_dict:
                            filtered_dict[field] = node_dict[field]
                    results.append(filtered_dict)
                else:
                    results.append({"id": node_id, **node_dict})

        return results

    def _query_edges_graphql(
        self, conditions: Dict[str, Any], fields: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Query edges with GraphQL-like interface."""
        results = []

        for edge in self.genome.edges:
            edge_dict = edge.model_dump(by_alias=True)
            if self._match_edge_conditions(edge, conditions):
                # Select fields
                if fields:
                    filtered_dict = {}
                    for field in fields:
                        if field in edge_dict:
                            filtered_dict[field] = edge_dict[field]
                    results.append(filtered_dict)
                else:
                    results.append(edge_dict)

        return results

    def _match_conditions(self, node: Node, conditions: Dict[str, Any]) -> bool:
        """Check if node matches conditions."""
        if not conditions:
            return True

        node_dict = node.model_dump() if hasattr(node, "model_dump") else {}

        for key, value in conditions.items():
            if "__" in key:
                field, op = key.split("__", 1)
                node_value = node_dict.get(field)

                if op == "gt" and not (node_value is not None and node_value > value):
                    return False
                elif op == "gte" and not (node_value is not None and node_value >= value):
                    return False
                elif op == "lt" and not (node_value is not None and node_value < value):
                    return False
                elif op == "lte" and not (node_value is not None and node_value <= value):
                    return False
                elif op == "ne" and node_value == value:
                    return False
                elif op == "in" and node_value not in value:
                    return False
                elif op == "like":
                    node_str = str(node_value or "")
                    pattern = value.replace("%", ".*").replace("_", ".")
                    if not re.search(pattern, node_str, re.IGNORECASE):
                        return False
            else:
                node_value = node_dict.get(key)
                if hasattr(node_value, "value"):
                    node_value = node_value.value
                if str(node_value) != str(value):
                    return False

        return True

    def _match_edge_conditions(self, edge: Edge, conditions: Dict[str, Any]) -> bool:
        """Check if edge matches conditions."""
        if not conditions:
            return True

        edge_dict = edge.model_dump(by_alias=True)

        for key, value in conditions.items():
            if key == "from" or key == "from_node":
                if edge.from_ != value:
                    return False
            elif key == "to" or key == "to_node":
                if edge.to != value:
                    return False
            elif key == "type":
                edge_type = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
                if edge_type != value:
                    return False
            else:
                edge_value = edge_dict.get(key)
                if edge_value != value:
                    return False

        return True

