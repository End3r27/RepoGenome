"""Caching system for RepoGenome analysis."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional


class AnalysisCache:
    """Cache for file analysis results."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache.

        Args:
            cache_dir: Cache directory (default: .repogenome/cache)
        """
        if cache_dir is None:
            cache_dir = Path(".repogenome") / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
        except Exception:
            return ""
        return sha256.hexdigest()

    def get_cache_key(self, file_path: Path) -> str:
        """
        Get cache key for a file.

        Args:
            file_path: Path to file

        Returns:
            Cache key string
        """
        file_hash = self.get_file_hash(file_path)
        if not file_hash:
            return ""

        # Use file path (relative) + hash as key
        return f"{file_path.name}_{file_hash[:16]}"

    def get(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result for a file.

        Args:
            file_path: Path to file

        Returns:
            Cached result dict or None if not cached
        """
        cache_key = self.get_cache_key(file_path)
        if not cache_key:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def set(self, file_path: Path, result: Dict[str, Any]) -> None:
        """
        Cache analysis result for a file.

        Args:
            file_path: Path to file
            result: Analysis result dictionary
        """
        cache_key = self.get_cache_key(file_path)
        if not cache_key:
            return

        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all cached files."""
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except Exception:
                    pass

    def invalidate_file(self, file_path: Path) -> None:
        """
        Invalidate cache for a specific file.

        Args:
            file_path: Path to file
        """
        # Find and remove cache files matching this file
        if self.cache_dir.exists():
            file_name = file_path.name
            for cache_file in self.cache_dir.glob(f"{file_name}_*.json"):
                try:
                    cache_file.unlink()
                except Exception:
                    pass

