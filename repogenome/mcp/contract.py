"""Agent contract enforcement for RepoGenome MCP."""

from typing import Any, Dict, List, Optional, Set


class AgentContract:
    """Enforces RepoGenome agent contract rules."""

    def __init__(self):
        """Initialize contract enforcement."""
        self.genome_loaded = False
        self.citations: List[str] = []
        self.edits_made = False
        self.impact_checked = False
        self.last_validation: Optional[Dict[str, Any]] = None

    def check_genome_loaded(self) -> bool:
        """
        Check if genome has been loaded.

        Returns:
            True if genome was loaded
        """
        return self.genome_loaded

    def mark_genome_loaded(self):
        """Mark that genome has been loaded."""
        self.genome_loaded = True

    def add_citation(self, node_id: str, reason: str = ""):
        """
        Add a citation for RepoGenome usage.

        Args:
            node_id: Node ID being cited
            reason: Reason for citation
        """
        citation = f"{node_id}"
        if reason:
            citation += f": {reason}"
        self.citations.append(citation)

    def get_citations(self) -> List[str]:
        """
        Get all citations.

        Returns:
            List of citation strings
        """
        return self.citations.copy()

    def mark_edit(self):
        """Mark that an edit has been made."""
        self.edits_made = True

    def check_impact_before_edit(self) -> bool:
        """
        Check if impact was analyzed before edit.

        Returns:
            True if impact was checked
        """
        return self.impact_checked

    def mark_impact_checked(self):
        """Mark that impact was checked."""
        self.impact_checked = True

    def validate_before_action(self, action: str) -> Dict[str, Any]:
        """
        Validate contract before allowing action.

        Args:
            action: Action being attempted

        Returns:
            Validation result with allowed flag
        """
        violations = []

        # Rule 1: Genome must be loaded
        if not self.genome_loaded and action not in ["scan", "validate"]:
            violations.append(
                "Genome not loaded. Load repogenome://current before acting."
            )

        # Rule 2: Impact must be checked before edits
        if self.edits_made and not self.impact_checked:
            violations.append(
                "Impact not checked. Use repogenome.impact before edits."
            )

        # Rule 3: Validation must pass
        if self.last_validation and not self.last_validation.get("valid"):
            violations.append(
                f"Validation failed: {self.last_validation.get('error')}. "
                "Fix issues before proceeding."
            )

        if violations:
            return {
                "allowed": False,
                "violations": violations,
                "action": "Fix contract violations before proceeding",
            }

        return {"allowed": True}

    def update_validation_result(self, result: Dict[str, Any]):
        """
        Update last validation result.

        Args:
            result: Validation result from repogenome.validate
        """
        self.last_validation = result

    def reset_edit_state(self):
        """Reset edit tracking (called after successful update)."""
        self.edits_made = False
        self.impact_checked = False

    def get_contract_status(self) -> Dict[str, Any]:
        """
        Get current contract status.

        Returns:
            Status dict
        """
        return {
            "genome_loaded": self.genome_loaded,
            "citations_count": len(self.citations),
            "edits_made": self.edits_made,
            "impact_checked": self.impact_checked,
            "validation_passed": self.last_validation.get("valid")
            if self.last_validation
            else None,
            "citations": self.citations[-10:],  # Last 10 citations
        }

    def enforce_contract_middleware(
        self, tool_name: str, args: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Middleware to enforce contract before tool execution.

        Args:
            tool_name: Name of tool being called
            args: Tool arguments

        Returns:
            Error dict if contract violated, None if allowed
        """
        # Allow scan and validate without genome loaded
        if tool_name in ["repogenome.scan", "repogenome.validate"]:
            return None

        # Check if genome loaded
        if not self.genome_loaded:
            return {
                "error": "Contract violation: Genome not loaded",
                "action": "Load repogenome://current resource first",
            }

        # Check impact before update
        if tool_name == "repogenome.update" and not self.impact_checked:
            return {
                "error": "Contract violation: Impact not checked",
                "action": "Call repogenome.impact before repogenome.update",
            }

        # Check validation
        if self.last_validation and not self.last_validation.get("valid"):
            return {
                "error": "Contract violation: Validation failed",
                "details": self.last_validation.get("error"),
                "action": "Run repogenome.validate and fix issues",
            }

        return None

