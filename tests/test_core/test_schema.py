"""Tests for schema module."""

import json
from datetime import datetime

import pytest

from repogenome.core.schema import (
    Edge,
    EdgeType,
    Node,
    NodeType,
    RepoGenome,
    Risk,
)


def test_node_creation():
    """Test creating a Node."""
    node = Node(
        type=NodeType.FUNCTION,
        file="test.py",
        language="Python",
        visibility="public",
        summary="Test function",
        criticality=0.5,
    )

    assert node.type == NodeType.FUNCTION
    assert node.file == "test.py"
    assert node.criticality == 0.5


def test_edge_creation():
    """Test creating an Edge."""
    edge = Edge(from_="test.py.func1", to="test.py.func2", type=EdgeType.CALLS)

    assert edge.from_ == "test.py.func1"
    assert edge.to == "test.py.func2"
    assert edge.type == EdgeType.CALLS


def test_repo_genome_creation():
    """Test creating a RepoGenome."""
    genome = RepoGenome()

    assert genome.metadata is not None
    assert genome.summary is not None
    assert isinstance(genome.nodes, dict)
    assert isinstance(genome.edges, list)


def test_repo_genome_serialization():
    """Test serializing RepoGenome to dict and JSON."""
    genome = RepoGenome()
    genome.nodes["test.node"] = Node(
        type=NodeType.FUNCTION, file="test.py", language="Python"
    )
    genome.edges.append(
        Edge(from_="test.node1", to="test.node2", type=EdgeType.CALLS)
    )

    # Test to_dict
    data = genome.to_dict()
    assert "nodes" in data
    assert "edges" in data
    assert data["nodes"]["test.node"]["type"] == "function"

    # Test JSON serialization
    json_str = json.dumps(data)
    assert '"nodes"' in json_str


def test_repo_genome_from_dict():
    """Test creating RepoGenome from dictionary."""
    data = {
        "metadata": {"repogenome_version": "0.1.0"},
        "nodes": {
            "test.node": {
                "type": "function",
                "file": "test.py",
                "language": "Python",
            }
        },
        "edges": [{"from": "test.node1", "to": "test.node2", "type": "calls"}],
    }

    genome = RepoGenome.from_dict(data)

    assert "test.node" in genome.nodes
    assert len(genome.edges) == 1
    assert genome.edges[0].from_ == "test.node1"


def test_risk_model():
    """Test Risk model."""
    risk = Risk(risk_score=0.8, reasons=["High fan-in", "Low test coverage"])

    assert risk.risk_score == 0.8
    assert len(risk.reasons) == 2


def test_genome_save_load(tmp_path):
    """Test saving and loading genome."""
    genome = RepoGenome()
    genome.nodes["test.node"] = Node(
        type=NodeType.FUNCTION, file="test.py", language="Python"
    )

    file_path = tmp_path / "test_genome.json"
    genome.save(str(file_path))

    assert file_path.exists()

    loaded_genome = RepoGenome.load(str(file_path))
    assert "test.node" in loaded_genome.nodes

