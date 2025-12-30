"""Context versioning and diffing for debuggable AI behavior."""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextVersioner:
    """Manages context versioning and diffing."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize context versioner.
        
        Args:
            cache_dir: Optional cache directory for storing versions
        """
        self.cache_dir = cache_dir or Path(".cache/context_versions")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_version(
        self,
        goal: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Generate version tag for context.
        
        Args:
            goal: Task goal
            context: Context dictionary
            
        Returns:
            Version string (e.g., "auth-refactor@v3")
        """
        # Extract base name from goal
        base_name = self._extract_base_name(goal)
        
        # Find existing versions
        existing_versions = self._list_versions(base_name)
        
        # Generate next version number
        version_num = len(existing_versions) + 1
        
        return f"{base_name}@v{version_num}"

    def _extract_base_name(self, goal: str) -> str:
        """Extract base name from goal."""
        # Sanitize goal to create base name
        base = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in goal.lower())
        # Limit length
        base = base[:30]
        # Remove trailing dashes
        base = base.rstrip("-")
        return base or "context"

    def _list_versions(self, base_name: str) -> List[str]:
        """List existing versions for a base name."""
        versions = []
        pattern = f"{base_name}@v*.json"
        
        for version_file in self.cache_dir.glob(pattern):
            # Extract version from filename
            name = version_file.stem
            if "@v" in name:
                versions.append(name)
        
        return sorted(versions)

    def save_version(
        self,
        version: str,
        context: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Save versioned context.
        
        Args:
            version: Version string
            context: Context dictionary
            metadata: Optional metadata
            
        Returns:
            Path to saved version file
        """
        version_file = self.cache_dir / f"{version}.json"
        
        data = {
            "version": version,
            "context": context,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return version_file

    def load_version(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Load versioned context.
        
        Args:
            version: Version string
            
        Returns:
            Context data or None if not found
        """
        version_file = self.cache_dir / f"{version}.json"
        
        if not version_file.exists():
            return None
        
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load version {version}: {e}")
            return None

    def diff_versions(
        self,
        version1: str,
        version2: str,
    ) -> Dict[str, Any]:
        """
        Calculate diff between two versions.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            Dictionary with diff information
        """
        v1_data = self.load_version(version1)
        v2_data = self.load_version(version2)
        
        if not v1_data or not v2_data:
            return {"error": "One or both versions not found"}
        
        v1_context = v1_data.get("context", {})
        v2_context = v2_data.get("context", {})
        
        diff = {
            "from_version": version1,
            "to_version": version2,
            "added": [],
            "removed": [],
            "modified": [],
        }
        
        # Compare tier_2 nodes (most important)
        v1_nodes = set(v1_context.get("tier_2", {}).get("nodes", {}).keys())
        v2_nodes = set(v2_context.get("tier_2", {}).get("nodes", {}).keys())
        
        diff["added"] = list(v2_nodes - v1_nodes)
        diff["removed"] = list(v1_nodes - v2_nodes)
        diff["modified"] = list(v1_nodes & v2_nodes)  # Could be more sophisticated
        
        return diff

