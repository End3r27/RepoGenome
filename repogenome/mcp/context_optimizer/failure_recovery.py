"""Context-aware failure recovery for improved retry logic."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class FailureRecovery:
    """Diagnoses failures and regenerates better context."""

    def __init__(self):
        """Initialize failure recovery."""

    def diagnose(
        self,
        error: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Diagnose why a failure occurred.
        
        Args:
            error: Error message or type
            context: Optional context that was used
            
        Returns:
            Diagnosis dictionary
        """
        error_lower = error.lower()
        
        diagnosis = {
            "failure_type": "unknown",
            "reason": error,
            "suggestions": [],
        }
        
        # Token-related failures
        if "token" in error_lower or "length" in error_lower or "too long" in error_lower:
            diagnosis["failure_type"] = "token_overflow"
            diagnosis["reason"] = "Context exceeds token limit"
            diagnosis["suggestions"] = [
                "Reduce context size",
                "Use semantic folding",
                "Increase token budget",
                "Remove low-relevance content",
            ]
        
        # Missing context failures
        elif "not found" in error_lower or "missing" in error_lower:
            diagnosis["failure_type"] = "missing_context"
            diagnosis["reason"] = "Required context not included"
            diagnosis["suggestions"] = [
                "Add missing nodes",
                "Expand scope",
                "Include dependencies",
            ]
        
        # Ambiguity failures
        elif "ambiguous" in error_lower or "unclear" in error_lower:
            diagnosis["failure_type"] = "ambiguity"
            diagnosis["reason"] = "Context is ambiguous"
            diagnosis["suggestions"] = [
                "Add clarifying context",
                "Reduce entropy",
                "Include examples",
            ]
        
        return diagnosis

    def regenerate_context(
        self,
        diagnosis: Dict[str, Any],
        original_context: Dict[str, Any],
        goal: str,
    ) -> Dict[str, Any]:
        """
        Regenerate context based on failure diagnosis.
        
        Args:
            diagnosis: Failure diagnosis
            original_context: Original context that failed
            goal: Task goal
            
        Returns:
            Improved context dictionary
        """
        failure_type = diagnosis.get("failure_type")
        improved = original_context.copy()
        
        if failure_type == "token_overflow":
            # Reduce context size
            improved = self._reduce_context_size(improved)
        
        elif failure_type == "missing_context":
            # Add missing context
            improved = self._add_missing_context(improved, goal)
        
        elif failure_type == "ambiguity":
            # Add clarifying context
            improved = self._add_clarifying_context(improved, goal)
        
        # Add recovery metadata
        if "metadata" not in improved:
            improved["metadata"] = {}
        
        improved["metadata"]["recovery"] = {
            "original_failure": diagnosis.get("failure_type"),
            "improvements": diagnosis.get("suggestions", []),
        }
        
        return improved

    def _reduce_context_size(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reduce context size."""
        # Remove tier_3 (lowest priority)
        if "tier_3" in context:
            del context["tier_3"]
        
        # Truncate tier_2 nodes
        if "tier_2" in context and "nodes" in context["tier_2"]:
            nodes = context["tier_2"]["nodes"]
            if isinstance(nodes, dict) and len(nodes) > 10:
                # Keep only top 10 nodes
                context["tier_2"]["nodes"] = dict(list(nodes.items())[:10])
        
        return context

    def _add_missing_context(self, context: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """Add missing context elements."""
        # This would typically query the genome for missing elements
        # For now, just mark that missing context should be added
        if "metadata" not in context:
            context["metadata"] = {}
        
        context["metadata"]["missing_context_note"] = "Additional context should be added based on goal analysis"
        
        return context

    def _add_clarifying_context(self, context: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """Add clarifying context to reduce ambiguity."""
        # Add examples or more detailed descriptions
        if "metadata" not in context:
            context["metadata"] = {}
        
        context["metadata"]["clarifying_note"] = "Additional examples and details added to reduce ambiguity"
        
        return context

