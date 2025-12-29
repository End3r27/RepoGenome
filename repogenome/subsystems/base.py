"""
Base class for RepoGenome analysis subsystems.

All subsystems must inherit from this base class and implement the required methods.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class Subsystem(ABC):
    """
    Base class for all RepoGenome analysis subsystems.

    Subsystems analyze repositories from different perspectives and contribute
    to the unified RepoGenome structure.
    """

    def __init__(self, name: str):
        """
        Initialize subsystem.

        Args:
            name: Unique name of the subsystem
        """
        self.name = name
        self.required_analyzers: List[str] = []

    @abstractmethod
    def analyze(
        self, 
        repo_path: Path, 
        existing_genome: Optional[Dict[str, Any]] = None,
        progress: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze the repository and return subsystem-specific data.

        Args:
            repo_path: Path to the repository root
            existing_genome: Optional existing genome for incremental updates
            progress: Optional progress bar for tracking

        Returns:
            Dictionary containing subsystem data to merge into genome
        """
        pass

    def update_incremental(
        self,
        repo_path: Path,
        old_genome: Dict[str, Any],
        changed_files: List[str],
    ) -> Dict[str, Any]:
        """
        Perform incremental update for changed files.

        Default implementation falls back to full analysis.
        Subsystems can override for optimization.

        Args:
            repo_path: Path to the repository root
            old_genome: Previous genome state
            changed_files: List of file paths that changed

        Returns:
            Dictionary containing updated subsystem data
        """
        return self.analyze(repo_path, old_genome)

    def get_dependencies(self) -> List[str]:
        """
        Get list of other subsystems this subsystem depends on.

        Returns:
            List of subsystem names
        """
        return []

    def is_required(self) -> bool:
        """
        Check if this subsystem is required for basic genome generation.

        Returns:
            True if required, False if optional
        """
        return True

