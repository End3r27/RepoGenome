"""Tests for the CLI."""

import logging
from click.testing import CliRunner
from repogenome.cli.main import generate

def test_generate_with_logging(caplog):
    """Test that the --log argument produces log output."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("test_file.py", "w") as f:
            f.write("print('hello')")

        with caplog.at_level(logging.INFO):
            result = runner.invoke(generate, [".", "--log", "INFO"])
            assert result.exit_code == 0
            assert "Starting genome generation" in caplog.text
