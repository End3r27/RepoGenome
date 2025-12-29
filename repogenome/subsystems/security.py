"""
Security analysis subsystem for RepoGenome.

Detects security vulnerabilities, secrets, and permission issues.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from repogenome.core.schema import Node, NodeType
from repogenome.subsystems.base import Subsystem


class SecurityAnalyzer(Subsystem):
    """Security analysis subsystem."""

    def __init__(self):
        """Initialize SecurityAnalyzer."""
        super().__init__("security")
        self.depends_on_subsystems = ["repospider"]
        
        # Common secret patterns
        self.secret_patterns = [
            (r'api[_-]?key["\s:=]+([a-zA-Z0-9_\-]{20,})', "API Key"),
            (r'secret[_-]?key["\s:=]+([a-zA-Z0-9_\-]{20,})', "Secret Key"),
            (r'password["\s:=]+([^\s"\']{8,})', "Password"),
            (r'token["\s:=]+([a-zA-Z0-9_\-]{20,})', "Token"),
            (r'aws[_-]?access[_-]?key[_-]?id["\s:=]+([A-Z0-9]{20})', "AWS Access Key"),
            (r'aws[_-]?secret[_-]?access[_-]?key["\s:=]+([A-Za-z0-9/+=]{40})', "AWS Secret Key"),
            (r'ssh[_-]?private[_-]?key["\s:=]+-----BEGIN', "SSH Private Key"),
            (r'private[_-]?key["\s:=]+-----BEGIN', "Private Key"),
            (r'-----BEGIN RSA PRIVATE KEY-----', "RSA Private Key"),
            (r'-----BEGIN DSA PRIVATE KEY-----', "DSA Private Key"),
            (r'-----BEGIN EC PRIVATE KEY-----', "EC Private Key"),
            (r'-----BEGIN OPENSSH PRIVATE KEY-----', "OpenSSH Private Key"),
            (r'-----BEGIN PGP PRIVATE KEY BLOCK-----', "PGP Private Key"),
            (r'xox[baprs]-[0-9a-zA-Z\-]{10,48}', "Slack Token"),
            (r'sk_live_[0-9a-zA-Z]{24,}', "Stripe Live Key"),
            (r'sk_test_[0-9a-zA-Z]{24,}', "Stripe Test Key"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
            (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token"),
            (r'ghu_[a-zA-Z0-9]{36}', "GitHub User-to-Server Token"),
            (r'ghs_[a-zA-Z0-9]{36}', "GitHub Server-to-Server Token"),
            (r'ghr_[a-zA-Z0-9]{36}', "GitHub Refresh Token"),
        ]
        
        # Vulnerability patterns
        self.vulnerability_patterns = [
            (r'eval\s*\(', "Code Injection (eval)"),
            (r'exec\s*\(', "Code Injection (exec)"),
            (r'__import__\s*\(', "Dynamic Import"),
            (r'pickle\.loads\s*\(', "Unsafe Deserialization (pickle)"),
            (r'yaml\.load\s*\(', "Unsafe YAML Loading"),
            (r'shell\s*=\s*True', "Shell Injection Risk"),
            (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Shell Injection (subprocess)"),
            (r'os\.system\s*\(', "Command Injection (os.system)"),
            (r'SQL.*\+.*["\']', "SQL Injection Risk"),
            (r'\.format\s*\([^)]*\{[^}]*\}', "Format String Injection"),
            (r'urllib\.urlopen\s*\(', "SSRF Risk (urllib)"),
            (r'requests\.get\s*\([^)]*verify\s*=\s*False', "SSL Verification Disabled"),
            (r'verify\s*=\s*False', "SSL Verification Disabled"),
            (r'allow_redirects\s*=\s*True', "Unsafe Redirects"),
        ]
        
        # Permission patterns
        self.permission_patterns = [
            (r'chmod\s+777', "World-Writable Permissions"),
            (r'chmod\s+666', "World-Writable Permissions"),
            (r'os\.chmod\s*\([^,]+,\s*0o777', "World-Writable Permissions"),
            (r'os\.chmod\s*\([^,]+,\s*0o666', "World-Writable Permissions"),
        ]

    def analyze(
        self,
        repo_path: Path,
        existing_genome: Optional[Dict[str, Any]] = None,
        progress: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Analyze repository for security issues.

        Args:
            repo_path: Path to repository root
            existing_genome: Optional existing genome
            progress: Optional progress bar

        Returns:
            Dictionary with security findings
        """
        if not existing_genome:
            return {"security": {}}

        nodes = existing_genome.get("nodes", {})
        security_findings: Dict[str, Dict[str, Any]] = {}

        # Analyze file nodes for security issues
        file_nodes = {
            node_id: node_data
            for node_id, node_data in nodes.items()
            if isinstance(node_data, dict) and node_data.get("type") == "file"
            or (hasattr(node_data, "type") and node_data.type == NodeType.FILE)
        }

        for node_id, node_data in file_nodes.items():
            # Get file path
            if isinstance(node_data, dict):
                file_path_str = node_data.get("file")
            else:
                file_path_str = node_data.file if hasattr(node_data, "file") else None

            if not file_path_str:
                continue

            full_path = repo_path / file_path_str
            if not full_path.exists() or not full_path.is_file():
                continue

            # Skip binary files
            try:
                with open(full_path, "rb") as f:
                    chunk = f.read(512)
                    if b"\x00" in chunk:
                        continue  # Binary file
            except Exception:
                continue

            # Analyze file content
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            findings = []
            
            # Check for secrets
            secrets = self._detect_secrets(content, file_path_str)
            if secrets:
                findings.extend(secrets)
            
            # Check for vulnerabilities
            vulnerabilities = self._detect_vulnerabilities(content, file_path_str)
            if vulnerabilities:
                findings.extend(vulnerabilities)
            
            # Check for permission issues
            permissions = self._detect_permission_issues(content, file_path_str)
            if permissions:
                findings.extend(permissions)
            
            if findings:
                security_findings[node_id] = {
                    "file": file_path_str,
                    "findings": findings,
                    "severity": self._calculate_severity(findings),
                }

        return {"security": security_findings}

    def _detect_secrets(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Detect secrets in file content."""
        findings = []
        
        for pattern, secret_type in self.secret_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                findings.append(
                    {
                        "type": "secret",
                        "category": secret_type,
                        "line": line_num,
                        "severity": "high",
                        "description": f"Potential {secret_type} found",
                    }
                )
        
        return findings

    def _detect_vulnerabilities(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Detect security vulnerabilities in file content."""
        findings = []
        
        for pattern, vuln_type in self.vulnerability_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                severity = "high" if "injection" in vuln_type.lower() else "medium"
                findings.append(
                    {
                        "type": "vulnerability",
                        "category": vuln_type,
                        "line": line_num,
                        "severity": severity,
                        "description": f"Potential {vuln_type}",
                    }
                )
        
        return findings

    def _detect_permission_issues(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Detect permission issues in file content."""
        findings = []
        
        for pattern, issue_type in self.permission_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                findings.append(
                    {
                        "type": "permission",
                        "category": issue_type,
                        "line": line_num,
                        "severity": "medium",
                        "description": f"Potential {issue_type}",
                    }
                )
        
        return findings

    def _calculate_severity(self, findings: List[Dict[str, Any]]) -> str:
        """Calculate overall severity for a file."""
        severities = [f.get("severity", "low") for f in findings]
        if "high" in severities:
            return "high"
        elif "medium" in severities:
            return "medium"
        else:
            return "low"

