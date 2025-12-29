"""Tests for security analysis subsystem."""

import tempfile
from pathlib import Path

import pytest

from repogenome.subsystems.security import SecurityAnalyzer


@pytest.fixture
def temp_repo():
    """Create a temporary repository with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create a file with a secret (for testing)
        secret_file = repo_path / "config.py"
        secret_file.write_text('api_key = "sk_test_FAKE_TEST_KEY_NOT_REAL_12345678901234567890"\n')
        
        # Create a file with vulnerability
        vuln_file = repo_path / "app.py"
        vuln_file.write_text('result = eval(user_input)\n')
        
        # Create a file with permission issue
        perm_file = repo_path / "setup.sh"
        perm_file.write_text('chmod 777 /tmp/file\n')
        
        yield repo_path


def test_security_analyzer_detects_secrets(temp_repo):
    """Test that security analyzer detects secrets."""
    analyzer = SecurityAnalyzer()
    
    # Create minimal genome data
    existing_genome = {
        "nodes": {
            "config.py": {
                "type": "file",
                "file": "config.py",
            }
        }
    }
    
    result = analyzer.analyze(temp_repo, existing_genome)
    
    assert "security" in result
    # Should detect the API key in config.py
    security_findings = result["security"]
    assert len(security_findings) > 0


def test_security_analyzer_detects_vulnerabilities(temp_repo):
    """Test that security analyzer detects vulnerabilities."""
    analyzer = SecurityAnalyzer()
    
    existing_genome = {
        "nodes": {
            "app.py": {
                "type": "file",
                "file": "app.py",
            }
        }
    }
    
    result = analyzer.analyze(temp_repo, existing_genome)
    
    assert "security" in result
    security_findings = result["security"]
    
    # Should detect eval usage
    found_vuln = False
    for file_id, findings in security_findings.items():
        for finding in findings.get("findings", []):
            if finding.get("type") == "vulnerability" and "eval" in finding.get("category", "").lower():
                found_vuln = True
                break
    
    assert found_vuln


def test_security_analyzer_detects_permissions(temp_repo):
    """Test that security analyzer detects permission issues."""
    analyzer = SecurityAnalyzer()
    
    existing_genome = {
        "nodes": {
            "setup.sh": {
                "type": "file",
                "file": "setup.sh",
            }
        }
    }
    
    result = analyzer.analyze(temp_repo, existing_genome)
    
    assert "security" in result
    security_findings = result["security"]
    
    # Should detect chmod 777
    found_perm = False
    for file_id, findings in security_findings.items():
        for finding in findings.get("findings", []):
            if finding.get("type") == "permission":
                found_perm = True
                break
    
    assert found_perm

