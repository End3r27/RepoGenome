"""Tests for RepoSpider subsystem."""

from pathlib import Path

import pytest

from repogenome.subsystems.repospider import RepoSpider


def test_repospider_initialization():
    """Test RepoSpider initialization."""
    spider = RepoSpider()
    assert spider.name == "repospider"


def test_repospider_analyze_empty_repo(tmp_path):
    """Test RepoSpider on empty repository."""
    spider = RepoSpider()
    result = spider.analyze(tmp_path)

    assert "nodes" in result
    assert "edges" in result
    assert isinstance(result["nodes"], dict)
    assert isinstance(result["edges"], list)


def test_repospider_analyze_python_file(tmp_path):
    """Test RepoSpider on Python file."""
    # Create a simple Python file
    test_file = tmp_path / "test.py"
    test_file.write_text(
        """
def hello():
    pass

class MyClass:
    def method(self):
        pass
"""
    )

    spider = RepoSpider()
    result = spider.analyze(tmp_path)

    # Should have file node
    assert any("test.py" in node_id for node_id in result["nodes"].keys())


@pytest.mark.skip(reason="Requires full repository structure")
def test_repospider_with_real_codebase():
    """Test RepoSpider with a more complex codebase."""
    pass

