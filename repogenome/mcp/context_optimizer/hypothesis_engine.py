"""Hypothesis-driven context - proposes explicit assumptions."""

import logging
from typing import Any, Dict, List, Optional

from repogenome.core.schema import RepoGenome

logger = logging.getLogger(__name__)


class HypothesisEngine:
    """Generates explicit assumptions from context analysis."""

    def __init__(self, genome: RepoGenome):
        """
        Initialize hypothesis engine.
        
        Args:
            genome: RepoGenome instance
        """
        self.genome = genome

    def generate_hypotheses(
        self,
        goal: str,
        context: Dict[str, Any],
    ) -> List[str]:
        """
        Generate hypotheses/assumptions from context.
        
        Args:
            goal: Task goal
            context: Context dictionary
            
        Returns:
            List of hypothesis strings
        """
        hypotheses = []
        
        # Analyze context for patterns
        if "tier_1" in context:
            tier_1 = context["tier_1"]
            
            # Check for authentication patterns
            if self._has_auth_patterns(tier_1):
                hypotheses.append("Auth is stateless")
                hypotheses.append("JWT expiry is critical")
            
            # Check for database patterns
            if self._has_db_patterns(tier_1):
                hypotheses.append("Database connections are pooled")
                hypotheses.append("Transactions are used for critical operations")
        
        # Analyze flows
        if "tier_1" in context and "flows" in context["tier_1"]:
            flows = context["tier_1"]["flows"]
            if flows:
                # Check if flows are synchronous
                hypotheses.append("Execution flows are synchronous")
        
        # Analyze nodes for patterns
        if "tier_2" in context and "nodes" in context["tier_2"]:
            nodes = context["tier_2"]["nodes"]
            
            # Check for error handling patterns
            if self._has_error_handling(nodes):
                hypotheses.append("Error handling is centralized")
            
            # Check for async patterns
            if self._has_async_patterns(nodes):
                hypotheses.append("Async/await patterns are used")
        
        return hypotheses

    def _has_auth_patterns(self, tier_1: Dict[str, Any]) -> bool:
        """Check if context has authentication patterns."""
        if "core_domains" in tier_1:
            domains = tier_1["core_domains"]
            auth_keywords = ["auth", "authentication", "login", "session"]
            return any(any(kw in str(d).lower() for kw in auth_keywords) for d in domains)
        return False

    def _has_db_patterns(self, tier_1: Dict[str, Any]) -> bool:
        """Check if context has database patterns."""
        if "core_domains" in tier_1:
            domains = tier_1["core_domains"]
            db_keywords = ["database", "db", "sql", "data"]
            return any(any(kw in str(d).lower() for kw in db_keywords) for d in domains)
        return False

    def _has_error_handling(self, nodes: Dict[str, Any]) -> bool:
        """Check if nodes show error handling patterns."""
        # Look for error-related node names
        error_keywords = ["error", "exception", "catch", "handle"]
        for node_id in nodes.keys():
            if any(kw in node_id.lower() for kw in error_keywords):
                return True
        return False

    def _has_async_patterns(self, nodes: Dict[str, Any]) -> bool:
        """Check if nodes show async patterns."""
        async_keywords = ["async", "await", "promise", "future"]
        for node_id in nodes.keys():
            if any(kw in node_id.lower() for kw in async_keywords):
                return True
        return False

