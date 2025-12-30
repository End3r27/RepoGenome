"""Negative context - explicit exclusions to reduce hallucinations."""

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class NegativeContext:
    """Manages explicit exclusions to prevent hallucinations."""

    def __init__(self):
        """Initialize negative context manager."""

    def determine_exclusions(
        self,
        goal: str,
        scope: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Determine what should be excluded from context.
        
        Args:
            goal: Task goal
            scope: Optional scope domains
            
        Returns:
            List of exclusion patterns/domains
        """
        exclusions: Set[str] = []
        
        goal_lower = goal.lower()
        
        # If goal mentions specific domain, exclude others
        if "auth" in goal_lower or "authentication" in goal_lower:
            exclusions.update(["billing", "analytics", "reporting"])
        elif "billing" in goal_lower or "payment" in goal_lower:
            exclusions.update(["auth", "analytics", "legacy"])
        elif "analytics" in goal_lower:
            exclusions.update(["billing", "auth", "legacy"])
        
        # Always exclude legacy unless explicitly mentioned
        if "legacy" not in goal_lower:
            exclusions.add("legacy")
        
        # Exclude UI unless explicitly mentioned
        if "ui" not in goal_lower and "frontend" not in goal_lower:
            exclusions.update(["ui", "frontend", "components"])
        
        # If scope is provided, exclude everything not in scope
        if scope:
            all_domains = ["billing", "analytics", "auth", "ui", "backend", "api"]
            for domain in all_domains:
                if domain not in [s.lower() for s in scope]:
                    exclusions.add(domain)
        
        return list(exclusions)

    def filter_nodes(
        self,
        node_ids: List[str],
        exclusions: List[str],
    ) -> List[str]:
        """
        Filter out nodes matching exclusion patterns.
        
        Args:
            node_ids: List of node IDs
            exclusions: List of exclusion patterns
            
        Returns:
            Filtered list of node IDs
        """
        if not exclusions:
            return node_ids
        
        filtered = []
        exclusion_lower = [e.lower() for e in exclusions]
        
        for node_id in node_ids:
            node_id_lower = node_id.lower()
            # Check if node matches any exclusion pattern
            if not any(exc in node_id_lower for exc in exclusion_lower):
                filtered.append(node_id)
        
        return filtered

