"""
ChronoMap subsystem - Temporal evolution and risk analysis.

Analyzes git history to calculate churn scores and identify fragile files.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from repogenome.core.schema import History
from repogenome.subsystems.base import Subsystem
from repogenome.utils.git_utils import (
    calculate_churn_score,
    get_file_history,
    get_last_major_change,
)


class ChronoMap(Subsystem):
    """Temporal evolution and risk analysis from git history."""

    def __init__(self):
        """Initialize ChronoMap."""
        super().__init__("chronomap")
        self.is_required = False  # Optional if git is not available

    def analyze(
        self, repo_path: Path, existing_genome: Optional[Dict[str, Any]] = None, progress: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze temporal evolution.

        Args:
            repo_path: Path to repository root
            existing_genome: Optional existing genome

        Returns:
            Dictionary with history data
        """
        history: Dict[str, History] = {}

        if not existing_genome:
            return {"history": {}}

        nodes = existing_genome.get("nodes", {})

        # Analyze each file node
        file_nodes = {
            node_id: node_data
            for node_id, node_data in nodes.items()
            if node_data.get("type") == "file"
        }

        for node_id, node_data in file_nodes.items():
            file_path = node_data.get("file")
            if not file_path:
                continue

            full_path = repo_path / file_path
            if not full_path.exists():
                continue

            # Calculate churn score
            churn = calculate_churn_score(repo_path, file_path)

            # Get last major change
            last_major = get_last_major_change(repo_path, file_path)

            # Analyze commit history for notes
            commits = get_file_history(repo_path, file_path, limit=10)
            notes = None
            if commits:
                # Check if there are frequent bug fixes
                bug_keywords = ["fix", "bug", "error", "issue", "patch"]
                bug_commits = [
                    c
                    for c in commits
                    if any(kw in c.get("message", "").lower() for kw in bug_keywords)
                ]
                if len(bug_commits) > len(commits) * 0.5:
                    notes = "Frequent bug fixes"

            history[node_id] = History(
                churn_score=churn,
                last_major_change=last_major,
                notes=notes,
            )

        return {"history": {k: v.model_dump() for k, v in history.items()}}

