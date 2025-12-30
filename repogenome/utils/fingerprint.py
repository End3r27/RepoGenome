"""Fingerprint generation for context anti-drift detection."""

import hashlib
import json
from typing import Any, Dict


def generate_fingerprint(data: Dict[str, Any]) -> str:
    """
    Generate SHA256 fingerprint for context data.
    
    Args:
        data: Dictionary to fingerprint
        
    Returns:
        SHA256 hash string prefixed with "sha256:"
    """
    # Serialize to JSON with sorted keys for deterministic hashing
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    
    # Generate SHA256 hash
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    
    return f"sha256:{hash_hex}"


def validate_fingerprint(data: Dict[str, Any], expected_fingerprint: str) -> bool:
    """
    Validate that data matches expected fingerprint.
    
    Args:
        data: Dictionary to validate
        expected_fingerprint: Expected fingerprint (with "sha256:" prefix)
        
    Returns:
        True if fingerprint matches
    """
    actual = generate_fingerprint(data)
    return actual == expected_fingerprint


def extract_fingerprint(fingerprint_str: str) -> str:
    """
    Extract hash part from fingerprint string.
    
    Args:
        fingerprint_str: Fingerprint string (e.g., "sha256:abc123...")
        
    Returns:
        Hash part without prefix
    """
    if fingerprint_str.startswith("sha256:"):
        return fingerprint_str[7:]
    return fingerprint_str

