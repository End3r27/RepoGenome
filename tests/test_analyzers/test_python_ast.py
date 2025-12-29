"""Tests for Python AST analyzer."""

from pathlib import Path

import pytest

from repogenome.analyzers.python.ast_analyzer import analyze_python_file


def test_analyze_simple_python_file(tmp_path):
    """Test analyzing a simple Python file."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        """
import os

def hello():
    return "world"

class MyClass:
    pass
"""
    )

    result = analyze_python_file(test_file)

    assert "functions" in result
    assert "classes" in result
    assert "imports" in result

    # Should find the function
    func_names = [f["name"] for f in result["functions"]]
    assert "hello" in func_names

    # Should find the class
    class_names = [c["name"] for c in result["classes"]]
    assert "MyClass" in class_names


def test_analyze_file_with_main_block(tmp_path):
    """Test analyzing file with __main__ block."""
    test_file = tmp_path / "main.py"
    test_file.write_text(
        """
if __name__ == "__main__":
    print("Hello")
"""
    )

    result = analyze_python_file(test_file)

    assert result["entry_points"]
    assert any("main.py" in ep for ep in result["entry_points"])


def test_analyze_invalid_syntax(tmp_path):
    """Test analyzing file with invalid syntax."""
    test_file = tmp_path / "invalid.py"
    test_file.write_text("def invalid syntax here")

    result = analyze_python_file(test_file)

    assert "errors" in result
    assert len(result["errors"]) > 0

