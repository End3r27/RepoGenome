"""Persistent context cache for goal-driven context assembly."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from repogenome.core.schema import RepoGenome

logger: logging.Logger = logging.getLogger(__name__)


class ContextCache:
    """Manages persistent caching of assembled contexts."""

    def __init__(self, cache_dir: Path):
        """
        Initialize context cache.

        Args:
            cache_dir: Directory for cache files (e.g., .cache/context)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_key(self, goal: str, constraints: Dict[str, Any]) -> str:
        """
        Generate deterministic cache key from goal and constraints.

        Args:
            goal: Task goal/intent
            constraints: Constraint dictionary

        Returns:
            Cache key string (hash-based)
        """
        # Create deterministic key from goal + sorted constraints
        key_data = {
            "goal": goal,
            "constraints": dict(sorted(constraints.items())) if constraints else {},
        }
        key_json = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        
        # Generate hash for filename
        hash_obj = hashlib.sha256(key_json.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:16]  # Use first 16 chars for filename
        
        # Also include goal name (sanitized) for readability
        goal_sanitized = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in goal.lower())[:30]
        
        return f"{goal_sanitized}_{hash_hex}.ctx.json"

    def get_cache_path(self, goal: str, constraints: Dict[str, Any]) -> Path:
        """
        Get cache file path for goal and constraints.

        Args:
            goal: Task goal/intent
            constraints: Constraint dictionary

        Returns:
            Path to cache file
        """
        cache_key = self.get_cache_key(goal, constraints)
        return self.cache_dir / cache_key

    def load_cached(
        self, goal: str, constraints: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Load cached context if available and valid.

        Args:
            goal: Task goal/intent
            constraints: Constraint dictionary

        Returns:
            Cached context dictionary or None if not found/invalid
        """
        cache_path = self.get_cache_path(goal, constraints)
        
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            
            # Validate that cache structure is correct
            if not isinstance(cached_data, dict) or "context" not in cached_data:
                logger.warning(f"Invalid cache file format: {cache_path}")
                return None
            
            return cached_data
        except Exception as e:
            logger.warning(f"Failed to load cache file {cache_path}: {e}")
            return None

    def save_cached(
        self,
        context: Dict[str, Any],
        goal: str,
        constraints: Dict[str, Any],
        genome: Optional[RepoGenome] = None,
    ) -> bool:
        """
        Save context to cache.

        Args:
            context: Context dictionary to cache
            goal: Task goal/intent
            constraints: Constraint dictionary
            genome: Optional RepoGenome instance for validation

        Returns:
            True if successful
        """
        cache_path = self.get_cache_path(goal, constraints)
        
        try:
            cached_data = {
                "context": context,
                "metadata": {
                    "goal": goal,
                    "constraints": constraints,
                    "genome_version": genome.metadata.repogenome_version if genome else None,
                    "genome_hash": genome.metadata.repo_hash if genome else None,
                },
            }
            
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save cache file {cache_path}: {e}")
            return False

    def is_valid(
        self, cached_context: Dict[str, Any], current_genome: RepoGenome
    ) -> bool:
        """
        Check if cached context is still valid for current genome.

        Args:
            cached_context: Cached context data (from load_cached)
            current_genome: Current RepoGenome instance

        Returns:
            True if cache is still valid
        """
        if not isinstance(cached_context, dict):
            return False
        
        metadata = cached_context.get("metadata", {})
        
        # Check genome version matches
        cached_version = metadata.get("genome_version")
        if cached_version and cached_version != current_genome.metadata.repogenome_version:
            return False
        
        # Check genome hash matches (more strict)
        cached_hash = metadata.get("genome_hash")
        if cached_hash and cached_hash != current_genome.metadata.repo_hash:
            return False
        
        return True

    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache files.

        Args:
            pattern: Optional pattern to match (e.g., "refactor_*")

        Returns:
            Number of files cleared
        """
        import fnmatch
        
        cleared = 0
        for cache_file in self.cache_dir.glob("*.ctx.json"):
            if pattern is None or fnmatch.fnmatch(cache_file.name, pattern):
                try:
                    cache_file.unlink()
                    cleared += 1
                except Exception as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")
        
        return cleared

