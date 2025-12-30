"""Context skeletons for staged context delivery."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextSkeleton:
    """Generates context skeletons for fast first response."""

    def __init__(self):
        """Initialize context skeleton generator."""

    def build_skeleton(
        self,
        goal: str,
        repo_intent: Optional[str] = None,
        core_flow: Optional[List[str]] = None,
        key_symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build Stage 1 skeleton context.
        
        Args:
            goal: Task goal
            repo_intent: Repository intent/description
            core_flow: List of core flow paths
            key_symbols: List of key symbol/node IDs
            
        Returns:
            Stage 1 skeleton dictionary
        """
        return {
            "stage": 1,
            "repo_intent": repo_intent or "Repository context",
            "core_flow": core_flow or [],
            "key_symbols": key_symbols or [],
            "goal": goal,
        }

    def build_full(
        self,
        skeleton: Dict[str, Any],
        code: Optional[Dict[str, Any]] = None,
        history: Optional[Dict[str, Any]] = None,
        edge_cases: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build Stage 2 full context from skeleton.
        
        Args:
            skeleton: Stage 1 skeleton
            code: Full code details
            history: Historical data
            edge_cases: Edge case information
            
        Returns:
            Stage 2 full context dictionary
        """
        return {
            "stage": 2,
            **skeleton,
            "code": code or {},
            "history": history or {},
            "edge_cases": edge_cases or [],
        }

