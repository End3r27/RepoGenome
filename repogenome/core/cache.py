"""Caching system for RepoGenome analysis."""

import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Optional

from repogenome.core.errors import handle_analysis_error


class AnalysisCache:
    """Cache for file analysis results with intelligent invalidation."""

    def __init__(self, cache_dir: Optional[Path] = None, max_size_mb: int = 100):
        """
        Initialize cache.

        Args:
            cache_dir: Cache directory (default: .repogenome/cache)
            max_size_mb: Maximum cache size in MB (default: 100)
        """
        if cache_dir is None:
            cache_dir = Path(".repogenome") / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "size_bytes": 0,
        }
        self._access_times: Dict[str, float] = {}

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
            self._stats["misses"] += 1
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            self._stats["misses"] += 1
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                result = json.load(f)
                self._stats["hits"] += 1
                self._access_times[cache_key] = time.time()
                return result
        except Exception:
            self._stats["misses"] += 1
            return None

    def set(self, file_path: Path, result: Dict[str, Any]) -> None:
        """
        Cache analysis result for a file with size management.

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
            
            # Update statistics
            self._stats["sets"] += 1
            self._access_times[cache_key] = time.time()
            file_size = cache_file.stat().st_size
            self._stats["size_bytes"] += file_size
            
            # Check if cache size limit exceeded
            if self._stats["size_bytes"] > self.max_size_bytes:
                self._evict_oldest()
        except Exception as e:
            handle_analysis_error(e, file_path=str(cache_file), log_error=False)

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
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    self._stats["invalidations"] += 1
                    self._stats["size_bytes"] = max(0, self._stats["size_bytes"] - file_size)
                    # Remove from access times
                    cache_key = cache_file.stem
                    self._access_times.pop(cache_key, None)
                except Exception:
                    pass

    def _evict_oldest(self) -> None:
        """Evict oldest cache entries when size limit is exceeded."""
        if not self._access_times:
            return
        
        # Sort by access time (oldest first)
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])
        
        # Evict until under limit
        while self._stats["size_bytes"] > self.max_size_bytes * 0.9 and sorted_keys:
            cache_key, _ = sorted_keys.pop(0)
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                try:
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    self._stats["size_bytes"] = max(0, self._stats["size_bytes"] - file_size)
                    self._access_times.pop(cache_key, None)
                except Exception:
                    pass

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            **self._stats,
            "hit_rate_percent": hit_rate,
            "size_mb": self._stats["size_bytes"] / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "cached_files": len(self._access_times),
        }

    def invalidate_pattern(self, pattern: str) -> None:
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: File name pattern (supports wildcards)
        """
        import fnmatch
        
        if not self.cache_dir.exists():
            return
        
        for cache_file in self.cache_dir.glob("*.json"):
            if fnmatch.fnmatch(cache_file.name, pattern):
                try:
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    self._stats["invalidations"] += 1
                    self._stats["size_bytes"] = max(0, self._stats["size_bytes"] - file_size)
                    cache_key = cache_file.stem
                    self._access_times.pop(cache_key, None)
                except Exception:
                    pass

