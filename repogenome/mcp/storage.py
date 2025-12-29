"""Genome storage and management for MCP server."""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple

from repogenome.core.schema import RepoGenome
from repogenome.utils.git_utils import get_repo_hash

logger = logging.getLogger(__name__)


class GenomeStorage:
    """Manages RepoGenome storage and loading."""

    def __init__(self, repo_path: Path):
        """
        Initialize genome storage.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = Path(repo_path).resolve()
        self.genome_path = self.repo_path / "repogenome.json"
        self._cached_genome: Optional[RepoGenome] = None
        self._cached_hash: Optional[str] = None
        self._load_error: Optional[str] = None

    def load_genome(self, force_reload: bool = False) -> Optional[RepoGenome]:
        """
        Load genome from file.

        Args:
            force_reload: Force reload even if cached

        Returns:
            RepoGenome instance or None if not found
        """
        if not force_reload and self._cached_genome is not None:
            return self._cached_genome

        if not self.genome_path.exists():
            self._load_error = f"Genome file not found: {self.genome_path}"
            logger.warning(self._load_error)
            return None

        try:
            genome = RepoGenome.load(str(self.genome_path))
            self._cached_genome = genome
            self._cached_hash = genome.metadata.repo_hash
            self._load_error = None
            return genome
        except json.JSONDecodeError as e:
            self._load_error = f"Invalid JSON in genome file: {str(e)}"
            logger.error(self._load_error, exc_info=True)
            return None
        except Exception as e:
            self._load_error = f"Failed to load genome: {type(e).__name__}: {str(e)}"
            logger.error(self._load_error, exc_info=True)
            return None

    def save_genome(self, genome: RepoGenome) -> bool:
        """
        Save genome to file.

        Args:
            genome: RepoGenome instance to save

        Returns:
            True if successful
        """
        try:
            genome.save(str(self.genome_path))
            self._cached_genome = genome
            self._cached_hash = genome.metadata.repo_hash
            return True
        except Exception:
            return False

    def is_stale(self) -> bool:
        """
        Check if genome is stale (repo hash mismatch).

        Returns:
            True if genome is stale or missing
        """
        genome = self.load_genome()
        if genome is None:
            return True

        current_hash = get_repo_hash(self.repo_path)
        return current_hash is not None and current_hash != genome.metadata.repo_hash

    def is_genome_file_present(self) -> bool:
        """
        Check if genome file exists (regardless of validity).

        Returns:
            True if genome file exists
        """
        return self.genome_path.exists()

    def get_load_error(self) -> Optional[str]:
        """
        Get the last error that occurred during genome loading.

        Returns:
            Error message or None if no error
        """
        return self._load_error

    def get_genome_status(self) -> Tuple[Optional[RepoGenome], bool, Optional[str]]:
        """
        Get genome with status information.

        Returns:
            Tuple of (genome, is_stale, error_message)
        """
        genome = self.load_genome()
        if genome is None:
            return None, True, self._load_error

        current_hash = get_repo_hash(self.repo_path)
        is_stale = current_hash is not None and current_hash != genome.metadata.repo_hash
        return genome, is_stale, None

    def get_summary(self) -> Optional[dict]:
        """
        Get summary section only.

        Returns:
            Summary dict with optional staleness metadata, or None if genome can't be loaded
        """
        genome, is_stale, error = self.get_genome_status()
        if genome is None:
            return None

        summary = genome.summary.model_dump()
        if is_stale:
            summary["_metadata"] = {
                "stale": True,
                "warning": "Genome is stale (repo hash mismatch). Run repogenome.scan to regenerate.",
            }
        return summary

    def get_diff(self, previous_genome_path: Optional[Path] = None) -> Optional[dict]:
        """
        Get diff between current and previous genome.

        Args:
            previous_genome_path: Path to previous genome (None = use genome_diff)

        Returns:
            Diff dict or None
        """
        genome, is_stale, error = self.get_genome_status()
        if genome is None:
            return None

        # Use genome_diff if available
        if genome.genome_diff:
            diff = genome.genome_diff.model_dump()
            if is_stale:
                diff["_metadata"] = {
                    "stale": True,
                    "warning": "Genome is stale. Diff may be inaccurate.",
                }
            return diff

        # Otherwise try to load previous genome
        if previous_genome_path and previous_genome_path.exists():
            try:
                from repogenome.utils.json_diff import compute_genome_diff

                old_genome = RepoGenome.load(str(previous_genome_path))
                diff = compute_genome_diff(
                    old_genome.to_dict(), genome.to_dict()
                )
                if is_stale:
                    diff["_metadata"] = {
                        "stale": True,
                        "warning": "Genome is stale. Diff may be inaccurate.",
                    }
                return diff
            except Exception as e:
                logger.warning(f"Failed to compute diff: {e}")

        return None

