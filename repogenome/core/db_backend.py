"""
Graph database backend for RepoGenome.

Provides optional database backends (SQLite, Neo4j) for storing and querying
large genomes more efficiently than JSON files.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from abc import ABC, abstractmethod

from repogenome.core.schema import (
    RepoGenome,
    Node,
    Edge,
    Metadata,
    Summary,
    Flow,
    Concept,
    History,
    Risk,
    Contract,
    Tests,
    NodeType,
    EdgeType,
)


class GraphBackend(ABC):
    """Abstract base class for graph database backends."""

    @abstractmethod
    def save_genome(self, genome: RepoGenome) -> None:
        """Save genome to database."""
        pass

    @abstractmethod
    def load_genome(self) -> RepoGenome:
        """Load genome from database."""
        pass

    @abstractmethod
    def query_nodes(self, filters: Optional[Dict[str, Any]] = None) -> List[tuple]:
        """Query nodes with filters."""
        pass

    @abstractmethod
    def query_edges(
        self,
        from_node: Optional[str] = None,
        to_node: Optional[str] = None,
        edge_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query edges."""
        pass

    @abstractmethod
    def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
        """Get neighboring nodes."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        pass


class SQLiteBackend(GraphBackend):
    """SQLite backend for RepoGenome storage."""

    def __init__(self, db_path: str):
        """
        Initialize SQLite backend.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self):
        """Create database schema."""
        cursor = self.conn.cursor()
        
        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                file TEXT,
                language TEXT,
                visibility TEXT,
                summary TEXT,
                criticality REAL DEFAULT 0.0,
                data TEXT  -- JSON for additional fields
            )
        """)
        
        # Edges table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                type TEXT NOT NULL,
                data TEXT,  -- JSON for additional fields
                FOREIGN KEY (from_node) REFERENCES nodes(id),
                FOREIGN KEY (to_node) REFERENCES nodes(id)
            )
        """)
        
        # Flows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry TEXT NOT NULL,
                path TEXT,  -- JSON array
                side_effects TEXT,  -- JSON array
                confidence REAL,
                data TEXT  -- JSON for additional fields
            )
        """)
        
        # Concepts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,
                nodes TEXT,  -- JSON array
                description TEXT,
                data TEXT  -- JSON for additional fields
            )
        """)
        
        # History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                node_id TEXT PRIMARY KEY,
                churn_score REAL,
                last_major_change TEXT,
                notes TEXT,
                data TEXT,  -- JSON for additional fields
                FOREIGN KEY (node_id) REFERENCES nodes(id)
            )
        """)
        
        # Risk table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk (
                node_id TEXT PRIMARY KEY,
                risk_score REAL,
                reasons TEXT,  -- JSON array
                data TEXT,  -- JSON for additional fields
                FOREIGN KEY (node_id) REFERENCES nodes(id)
            )
        """)
        
        # Contracts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id TEXT PRIMARY KEY,
                depends_on TEXT,  -- JSON array
                breaking_change_risk REAL,
                data TEXT  -- JSON for additional fields
            )
        """)
        
        # Tests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY,
                coverage REAL,
                test_files TEXT,  -- JSON array
                data TEXT  -- JSON for additional fields
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_node)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_node)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type)")
        
        self.conn.commit()

    def save_genome(self, genome: RepoGenome) -> None:
        """Save genome to SQLite database."""
        cursor = self.conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM metadata")
        cursor.execute("DELETE FROM summary")
        cursor.execute("DELETE FROM nodes")
        cursor.execute("DELETE FROM edges")
        cursor.execute("DELETE FROM flows")
        cursor.execute("DELETE FROM concepts")
        cursor.execute("DELETE FROM history")
        cursor.execute("DELETE FROM risk")
        cursor.execute("DELETE FROM contracts")
        cursor.execute("DELETE FROM tests")
        
        # Save metadata
        if genome.metadata:
            metadata_dict = genome.metadata.model_dump()
            for key, value in metadata_dict.items():
                cursor.execute(
                    "INSERT INTO metadata (key, value) VALUES (?, ?)",
                    (key, json.dumps(value, default=str)),
                )
        
        # Save summary
        if genome.summary:
            summary_dict = genome.summary.model_dump()
            for key, value in summary_dict.items():
                cursor.execute(
                    "INSERT INTO summary (key, value) VALUES (?, ?)",
                    (key, json.dumps(value, default=str)),
                )
        
        # Save nodes
        for node_id, node in genome.nodes.items():
            cursor.execute(
                """INSERT INTO nodes (id, type, file, language, visibility, summary, criticality, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node_id,
                    node.type.value,
                    node.file,
                    node.language,
                    node.visibility,
                    node.summary,
                    node.criticality,
                    json.dumps({}, default=str),  # Additional fields can go here
                ),
            )
        
        # Save edges
        for edge in genome.edges:
            cursor.execute(
                """INSERT INTO edges (from_node, to_node, type, data)
                   VALUES (?, ?, ?, ?)""",
                (
                    edge.from_,
                    edge.to,
                    edge.type.value,
                    json.dumps({}, default=str),
                ),
            )
        
        # Save flows
        for flow in genome.flows:
            cursor.execute(
                """INSERT INTO flows (entry, path, side_effects, confidence, data)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    flow.entry,
                    json.dumps(flow.path, default=str),
                    json.dumps(flow.side_effects, default=str),
                    flow.confidence,
                    json.dumps({}, default=str),
                ),
            )
        
        # Save concepts
        for concept_id, concept in genome.concepts.items():
            cursor.execute(
                """INSERT INTO concepts (id, nodes, description, data)
                   VALUES (?, ?, ?, ?)""",
                (
                    concept_id,
                    json.dumps(concept.nodes, default=str),
                    concept.description,
                    json.dumps({}, default=str),
                ),
            )
        
        # Save history
        for node_id, hist in genome.history.items():
            cursor.execute(
                """INSERT INTO history (node_id, churn_score, last_major_change, notes, data)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    node_id,
                    hist.churn_score,
                    hist.last_major_change.isoformat() if hist.last_major_change else None,
                    hist.notes,
                    json.dumps({}, default=str),
                ),
            )
        
        # Save risk
        for node_id, risk_data in genome.risk.items():
            cursor.execute(
                """INSERT INTO risk (node_id, risk_score, reasons, data)
                   VALUES (?, ?, ?, ?)""",
                (
                    node_id,
                    risk_data.risk_score,
                    json.dumps(risk_data.reasons, default=str),
                    json.dumps({}, default=str),
                ),
            )
        
        # Save contracts
        for contract_id, contract in genome.contracts.items():
            cursor.execute(
                """INSERT INTO contracts (id, depends_on, breaking_change_risk, data)
                   VALUES (?, ?, ?, ?)""",
                (
                    contract_id,
                    json.dumps(contract.depends_on, default=str),
                    contract.breaking_change_risk,
                    json.dumps({}, default=str),
                ),
            )
        
        # Save tests
        if genome.tests:
            cursor.execute(
                """INSERT INTO tests (id, coverage, test_files, data)
                   VALUES (?, ?, ?, ?)""",
                (
                    1,
                    genome.tests.coverage,
                    json.dumps(genome.tests.test_files, default=str),
                    json.dumps({}, default=str),
                ),
            )
        
        self.conn.commit()

    def load_genome(self) -> RepoGenome:
        """Load genome from SQLite database."""
        cursor = self.conn.cursor()
        
        # Load metadata
        cursor.execute("SELECT key, value FROM metadata")
        metadata_dict = {}
        for row in cursor.fetchall():
            metadata_dict[row["key"]] = json.loads(row["value"])
        metadata = Metadata(**metadata_dict) if metadata_dict else Metadata()
        
        # Load summary
        cursor.execute("SELECT key, value FROM summary")
        summary_dict = {}
        for row in cursor.fetchall():
            summary_dict[row["key"]] = json.loads(row["value"])
        summary = Summary(**summary_dict) if summary_dict else Summary()
        
        # Load nodes
        cursor.execute("SELECT * FROM nodes")
        nodes = {}
        for row in cursor.fetchall():
            node = Node(
                type=NodeType(row["type"]),
                file=row["file"],
                language=row["language"],
                visibility=row["visibility"],
                summary=row["summary"],
                criticality=row["criticality"] or 0.0,
            )
            nodes[row["id"]] = node
        
        # Load edges
        cursor.execute("SELECT * FROM edges")
        edges = []
        for row in cursor.fetchall():
            edge = Edge(
                from_=row["from_node"],
                to=row["to_node"],
                type=EdgeType(row["type"]),
            )
            edges.append(edge)
        
        # Load flows
        cursor.execute("SELECT * FROM flows")
        flows = []
        for row in cursor.fetchall():
            flow = Flow(
                entry=row["entry"],
                path=json.loads(row["path"]),
                side_effects=json.loads(row["side_effects"]),
                confidence=row["confidence"],
            )
            flows.append(flow)
        
        # Load concepts
        cursor.execute("SELECT * FROM concepts")
        concepts = {}
        for row in cursor.fetchall():
            concept = Concept(
                nodes=json.loads(row["nodes"]),
                description=row["description"],
            )
            concepts[row["id"]] = concept
        
        # Load history
        cursor.execute("SELECT * FROM history")
        history = {}
        for row in cursor.fetchall():
            from datetime import datetime
            hist = History(
                churn_score=row["churn_score"] or 0.0,
                last_major_change=datetime.fromisoformat(row["last_major_change"]) if row["last_major_change"] else None,
                notes=row["notes"],
            )
            history[row["node_id"]] = hist
        
        # Load risk
        cursor.execute("SELECT * FROM risk")
        risk = {}
        for row in cursor.fetchall():
            from repogenome.core.schema import Risk
            risk_data = Risk(
                risk_score=row["risk_score"] or 0.0,
                reasons=json.loads(row["reasons"]),
            )
            risk[row["node_id"]] = risk_data
        
        # Load contracts
        cursor.execute("SELECT * FROM contracts")
        contracts = {}
        for row in cursor.fetchall():
            from repogenome.core.schema import Contract
            contract = Contract(
                depends_on=json.loads(row["depends_on"]),
                breaking_change_risk=row["breaking_change_risk"] or 0.0,
            )
            contracts[row["id"]] = contract
        
        # Load tests
        cursor.execute("SELECT * FROM tests LIMIT 1")
        tests = None
        row = cursor.fetchone()
        if row:
            from repogenome.core.schema import Tests
            tests = Tests(
                coverage=row["coverage"] or 0.0,
                test_files=json.loads(row["test_files"]),
            )
        
        return RepoGenome(
            metadata=metadata,
            summary=summary,
            nodes=nodes,
            edges=edges,
            flows=flows,
            concepts=concepts,
            history=history,
            risk=risk,
            contracts=contracts,
            tests=tests,
        )

    def query_nodes(self, filters: Optional[Dict[str, Any]] = None) -> List[tuple]:
        """Query nodes with filters."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM nodes WHERE 1=1"
        params = []
        
        if filters:
            for key, value in filters.items():
                if "__" in key:
                    field, op = key.split("__", 1)
                    if op == "gt":
                        query += f" AND {field} > ?"
                        params.append(value)
                    elif op == "gte":
                        query += f" AND {field} >= ?"
                        params.append(value)
                    elif op == "lt":
                        query += f" AND {field} < ?"
                        params.append(value)
                    elif op == "lte":
                        query += f" AND {field} <= ?"
                        params.append(value)
                else:
                    query += f" AND {key} = ?"
                    params.append(value)
        
        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            node = Node(
                type=NodeType(row["type"]),
                file=row["file"],
                language=row["language"],
                visibility=row["visibility"],
                summary=row["summary"],
                criticality=row["criticality"] or 0.0,
            )
            results.append((row["id"], node))
        
        return results

    def query_edges(
        self,
        from_node: Optional[str] = None,
        to_node: Optional[str] = None,
        edge_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query edges."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM edges WHERE 1=1"
        params = []
        
        if from_node:
            query += " AND from_node = ?"
            params.append(from_node)
        if to_node:
            query += " AND to_node = ?"
            params.append(to_node)
        if edge_type:
            query += " AND type = ?"
            params.append(edge_type)
        
        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            edge = Edge(
                from_=row["from_node"],
                to=row["to_node"],
                type=EdgeType(row["type"]),
            )
            results.append(edge.model_dump(by_alias=True))
        
        return results

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
        """Get neighboring nodes."""
        cursor = self.conn.cursor()
        neighbors = set()
        
        if direction in ["out", "both"]:
            cursor.execute("SELECT to_node FROM edges WHERE from_node = ?", (node_id,))
            for row in cursor.fetchall():
                neighbors.add(row["to_node"])
        
        if direction in ["in", "both"]:
            cursor.execute("SELECT from_node FROM edges WHERE to_node = ?", (node_id,))
            for row in cursor.fetchall():
                neighbors.add(row["from_node"])
        
        return list(neighbors)

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_backend(backend_type: str, path: str) -> GraphBackend:
    """
    Create a graph backend instance.

    Args:
        backend_type: Backend type ("sqlite" or "neo4j")
        path: Path to database or connection string

    Returns:
        GraphBackend instance
    """
    if backend_type == "sqlite":
        return SQLiteBackend(path)
    elif backend_type == "neo4j":
        # Neo4j support would require neo4j driver
        # For now, raise NotImplementedError
        raise NotImplementedError("Neo4j backend not yet implemented")
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")

