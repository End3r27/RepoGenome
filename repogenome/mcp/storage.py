"""Genome storage and management for MCP server."""

import json
from pathlib import Path
from typing import Optional

from repogenome.core.schema import RepoGenome
from repogenome.utils.git_utils import get_repo_hash


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
            return None

        try:
            genome = RepoGenome.load(str(self.genome_path))
            self._cached_genome = genome
            self._cached_hash = genome.metadata.repo_hash
            return genome
        except Exception:
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

    def get_summary(self) -> Optional[dict]:
        """
        Get summary section only.

        Returns:
            Summary dict or None
        """
        genome = self.load_genome()
        if genome is None:
            return None

        return genome.summary.model_dump()

    def get_diff(self, previous_genome_path: Optional[Path] = None) -> Optional[dict]:
        """
        Get diff between current and previous genome.

        Args:
            previous_genome_path: Path to previous genome (None = use genome_diff)

        Returns:
            Diff dict or None
        """
        genome = self.load_genome()
        if genome is None:
            return None

        # Use genome_diff if available
        if genome.genome_diff:
            return genome.genome_diff.model_dump()

        # Otherwise try to load previous genome
        if previous_genome_path and previous_genome_path.exists():
            try:
                from repogenome.utils.json_diff import compute_genome_diff

                old_genome = RepoGenome.load(str(previous_genome_path))
                diff = compute_genome_diff(
                    old_genome.to_dict(), genome.to_dict()
                )
                return diff
            except Exception:
                pass

        return None

