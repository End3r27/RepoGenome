"""
SQL file analyzer.

Extracts structure from SQL files including queries, tables, columns, joins, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Set


class SQLAnalyzer:
    """Analyzer for SQL files."""

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a SQL file and extract its structure.

        Args:
            file_path: Path to SQL file

        Returns:
            Dictionary with extracted information
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return {
                "queries": [],
                "tables": [],
                "columns": [],
                "joins": [],
                "views": [],
                "procedures": [],
                "errors": ["Could not read file"],
            }

        queries = self._extract_queries(content)
        tables = self._extract_tables(content)
        columns = self._extract_columns(content)
        joins = self._extract_joins(content)
        views = self._extract_views(content)
        procedures = self._extract_procedures(content)

        return {
            "queries": queries,
            "tables": tables,
            "columns": columns,
            "joins": joins,
            "views": views,
            "procedures": procedures,
        }

    def _extract_queries(self, content: str) -> List[Dict[str, Any]]:
        """Extract SQL queries."""
        queries = []
        # Match main query types (simplified - SQL parsing is complex)
        query_types = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
        for query_type in query_types:
            pattern = rf"\b{query_type}\s+[^;]+"
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                query_text = match.group(0).strip()[:200]
                queries.append({"type": query_type, "query": query_text})
        return queries

    def _extract_tables(self, content: str) -> List[str]:
        """Extract table names."""
        tables: Set[str] = set()
        # FROM clause
        from_pattern = r"\bFROM\s+([\w.]+)"
        for match in re.finditer(from_pattern, content, re.IGNORECASE):
            table = match.group(1).strip()
            tables.add(table)

        # JOIN clauses
        join_pattern = r"\bJOIN\s+([\w.]+)"
        for match in re.finditer(join_pattern, content, re.IGNORECASE):
            table = match.group(1).strip()
            tables.add(table)

        # INTO clause
        into_pattern = r"\bINTO\s+([\w.]+)"
        for match in re.finditer(into_pattern, content, re.IGNORECASE):
            table = match.group(1).strip()
            tables.add(table)

        # UPDATE clause
        update_pattern = r"\bUPDATE\s+([\w.]+)"
        for match in re.finditer(update_pattern, content, re.IGNORECASE):
            table = match.group(1).strip()
            tables.add(table)

        # CREATE TABLE
        create_table_pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)"
        for match in re.finditer(create_table_pattern, content, re.IGNORECASE):
            table = match.group(1).strip()
            tables.add(table)

        return sorted(list(tables))

    def _extract_columns(self, content: str) -> List[Dict[str, Any]]:
        """Extract column references."""
        columns = []
        # SELECT columns
        select_pattern = r"SELECT\s+((?:[^F]|F(?!ROM\b))+?)\s+FROM"
        for match in re.finditer(select_pattern, content, re.IGNORECASE | re.DOTALL):
            columns_text = match.group(1)
            # Split by comma
            for col in columns_text.split(","):
                col = col.strip()
                if col and col != "*":
                    columns.append({"column": col, "context": "SELECT"})

        # WHERE conditions
        where_pattern = r"\bWHERE\s+([^;]+)"
        for match in re.finditer(where_pattern, content, re.IGNORECASE):
            where_clause = match.group(1)
            # Extract column names (simplified)
            col_pattern = r"(\w+)\.(\w+)|(\w+)\s*[=<>]"
            for col_match in re.finditer(col_pattern, where_clause):
                if col_match.group(1) and col_match.group(2):
                    columns.append(
                        {
                            "column": f"{col_match.group(1)}.{col_match.group(2)}",
                            "context": "WHERE",
                        }
                    )
                elif col_match.group(3):
                    columns.append({"column": col_match.group(3), "context": "WHERE"})

        return columns[:100]  # Limit to first 100

    def _extract_joins(self, content: str) -> List[Dict[str, Any]]:
        """Extract JOIN statements."""
        joins = []
        # JOIN ... ON patterns
        join_pattern = r"(\w+)\s+JOIN\s+([\w.]+)\s+ON\s+([^;]+)"
        for match in re.finditer(join_pattern, content, re.IGNORECASE):
            join_type = match.group(1).upper()
            table = match.group(2)
            condition = match.group(3).strip()[:100]
            joins.append({"type": join_type, "table": table, "condition": condition})
        return joins

    def _extract_views(self, content: str) -> List[Dict[str, Any]]:
        """Extract CREATE VIEW statements."""
        views = []
        pattern = r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([\w.]+)"
        for match in re.finditer(pattern, content, re.IGNORECASE):
            view_name = match.group(1)
            views.append({"name": view_name})
        return views

    def _extract_procedures(self, content: str) -> List[Dict[str, Any]]:
        """Extract stored procedures/functions."""
        procedures = []
        # CREATE PROCEDURE or CREATE FUNCTION
        pattern = r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\s+([\w.]+)"
        for match in re.finditer(pattern, content, re.IGNORECASE):
            proc_name = match.group(1)
            procedures.append({"name": proc_name})
        return procedures


def analyze_sql_file(file_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze a SQL file.

    Args:
        file_path: Path to SQL file

    Returns:
        Dictionary with extracted information
    """
    analyzer = SQLAnalyzer()
    return analyzer.analyze_file(file_path)

