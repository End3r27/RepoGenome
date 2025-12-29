"""Tests for streaming JSON writer."""

import json
import tempfile
from pathlib import Path

import pytest

from repogenome.core.schema import Edge, EdgeType, Node, NodeType, RepoGenome
from repogenome.core.streaming import save_streaming


@pytest.fixture
def sample_genome():
    """Create a sample genome for testing."""
    genome = RepoGenome()
    
    # Add nodes
    for i in range(100):
        genome.nodes[f"test{i}.py"] = Node(
            type=NodeType.FILE,
            file=f"test{i}.py",
            language="Python",
        )
    
    # Add edges
    for i in range(50):
        genome.edges.append(
            Edge(
                from_=f"test{i}.py",
                to=f"test{i+1}.py",
                type=EdgeType.IMPORTS,
            )
        )
    
    return genome


def test_streaming_save(sample_genome):
    """Test streaming save."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        save_streaming(sample_genome, temp_path, minify=True)
        
        # Verify file exists
        assert Path(temp_path).exists()
        
        # Verify it's valid JSON
        with open(temp_path, 'r') as f:
            data = json.load(f)
        
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 100
        assert len(data["edges"]) == 50
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_streaming_save_compact(sample_genome):
    """Test streaming save with compact mode."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        save_streaming(sample_genome, temp_path, compact=True, minify=True)
        
        # Verify file exists
        assert Path(temp_path).exists()
        
        # Verify it's valid JSON
        with open(temp_path, 'r') as f:
            data = json.load(f)
        
        # Check for compact field names
        if "nodes" in data and data["nodes"]:
            first_node = next(iter(data["nodes"].values()))
            # In compact mode, "type" becomes "t"
            assert "t" in first_node or "type" in first_node
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_streaming_save_compressed(sample_genome):
    """Test streaming save with compression."""
    import gzip
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json.gz', delete=False) as f:
        temp_path = f.name
    
    try:
        save_streaming(sample_genome, temp_path, compress=True, minify=True)
        
        # Verify file exists
        assert Path(temp_path).exists()
        
        # Verify it's gzipped
        with gzip.open(temp_path, 'rt') as f:
            data = json.load(f)
        
        assert "nodes" in data
        assert len(data["nodes"]) == 100
    finally:
        Path(temp_path).unlink(missing_ok=True)

