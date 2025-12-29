"""Tests for advanced query language."""

import pytest

from repogenome.core.advanced_query import AdvancedQuery
from repogenome.core.schema import Edge, EdgeType, Node, NodeType, RepoGenome


@pytest.fixture
def sample_genome():
    """Create a sample genome for testing."""
    genome = RepoGenome()
    
    # Add nodes
    genome.nodes["test.py.func1"] = Node(
        type=NodeType.FUNCTION,
        file="test.py",
        language="Python",
        visibility="public",
        summary="Test function 1",
        criticality=0.9,
    )
    genome.nodes["test.py.func2"] = Node(
        type=NodeType.FUNCTION,
        file="test.py",
        language="Python",
        visibility="private",
        summary="Test function 2",
        criticality=0.5,
    )
    genome.nodes["test.py"] = Node(
        type=NodeType.FILE,
        file="test.py",
        language="Python",
    )
    
    # Add edges
    genome.edges.append(
        Edge(from_="test.py.func1", to="test.py.func2", type=EdgeType.CALLS)
    )
    
    return genome


def test_sql_query_nodes(sample_genome):
    """Test SQL-like node queries."""
    query = AdvancedQuery(sample_genome)
    
    # Query all nodes
    result = query.execute("SELECT * FROM nodes")
    assert result["type"] == "nodes"
    assert len(result["results"]) == 3
    
    # Query with WHERE clause
    result = query.execute("SELECT * FROM nodes WHERE type='function'")
    assert len(result["results"]) == 2
    
    # Query with comparison
    result = query.execute("SELECT * FROM nodes WHERE criticality>0.8")
    assert len(result["results"]) == 1
    assert result["results"][0]["id"] == "test.py.func1"


def test_sql_query_edges(sample_genome):
    """Test SQL-like edge queries."""
    query = AdvancedQuery(sample_genome)
    
    result = query.execute("SELECT * FROM edges")
    assert result["type"] == "edges"
    assert len(result["results"]) == 1


def test_graphql_query(sample_genome):
    """Test GraphQL-style queries."""
    query = AdvancedQuery(sample_genome)
    
    result = query.execute("{ nodes(type: function) { id, file, summary } }")
    assert result["type"] == "nodes"
    assert len(result["results"]) == 2


def test_simple_query(sample_genome):
    """Test simple keyword queries."""
    query = AdvancedQuery(sample_genome)
    
    result = query.execute("function")
    assert result["type"] == "search"
    assert len(result["results"]) > 0


def test_query_with_order_by(sample_genome):
    """Test SQL query with ORDER BY."""
    query = AdvancedQuery(sample_genome)
    
    result = query.execute("SELECT * FROM nodes WHERE type='function' ORDER BY criticality DESC")
    assert len(result["results"]) == 2
    assert result["results"][0]["criticality"] >= result["results"][1]["criticality"]


def test_query_with_limit(sample_genome):
    """Test SQL query with LIMIT."""
    query = AdvancedQuery(sample_genome)
    
    result = query.execute("SELECT * FROM nodes LIMIT 1")
    assert len(result["results"]) == 1

