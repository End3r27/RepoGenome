"""Context relevance scoring for intelligent context selection."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from repogenome.core.schema import Node, RepoGenome

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Scores context chunks by relevance, freshness, and risk."""

    def __init__(self, genome: RepoGenome):
        """
        Initialize relevance scorer.
        
        Args:
            genome: RepoGenome instance
        """
        self.genome = genome

    def score_node(
        self,
        node_id: str,
        goal: str,
        query_terms: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Score a node for relevance to a goal.
        
        Args:
            node_id: Node ID to score
            goal: Goal/query string
            query_terms: Optional pre-extracted query terms
            
        Returns:
            Dictionary with relevance, freshness, risk scores
        """
        if node_id not in self.genome.nodes:
            return {"relevance": 0.0, "freshness": 0.0, "risk": 0.0}
        
        node = self.genome.nodes[node_id]
        
        # Extract query terms if not provided
        if query_terms is None:
            query_terms = self._extract_terms(goal)
        
        # Calculate relevance (semantic similarity)
        relevance = self._calculate_relevance(node, node_id, query_terms)
        
        # Calculate freshness (recency)
        freshness = self._calculate_freshness(node_id)
        
        # Calculate risk (criticality)
        risk = self._calculate_risk(node_id)
        
        return {
            "relevance": relevance,
            "freshness": freshness,
            "risk": risk,
        }

    def _extract_terms(self, text: str) -> List[str]:
        """Extract meaningful terms from text."""
        import re
        
        # Split on whitespace and punctuation
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "should", "could", "may", "might", "must", "can", "this",
            "that", "these", "those", "it", "its", "they", "them", "their",
        }
        
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _calculate_relevance(
        self,
        node: Node,
        node_id: str,
        query_terms: List[str],
    ) -> float:
        """Calculate relevance score based on semantic similarity."""
        score = 0.0
        max_score = 0.0
        
        # Check node ID
        node_id_lower = node_id.lower()
        for term in query_terms:
            if term in node_id_lower:
                score += 2.0
                max_score += 2.0
        
        # Check summary
        if node.summary:
            summary_lower = node.summary.lower()
            for term in query_terms:
                if term in summary_lower:
                    score += 1.0
                    max_score += 1.0
        
        # Check file path
        if node.file:
            file_lower = node.file.lower()
            for term in query_terms:
                if term in file_lower:
                    score += 0.5
                    max_score += 0.5
        
        # Normalize to 0-1
        if max_score > 0:
            return min(1.0, score / max_score)
        return 0.0

    def _calculate_freshness(self, node_id: str) -> float:
        """Calculate freshness score based on recency."""
        # Check history for churn score
        if node_id in self.genome.history:
            history = self.genome.history[node_id]
            # Higher churn = more recent changes = higher freshness
            return history.churn_score
        
        # Default: assume not fresh
        return 0.0

    def _calculate_risk(self, node_id: str) -> float:
        """Calculate risk score based on criticality and risk assessment."""
        # Get risk score if available
        if node_id in self.genome.risk:
            return self.genome.risk[node_id].risk_score
        
        # Fall back to criticality
        if node_id in self.genome.nodes:
            return self.genome.nodes[node_id].criticality
        
        return 0.0

    def score_nodes(
        self,
        node_ids: List[str],
        goal: str,
    ) -> Dict[str, Dict[str, float]]:
        """
        Score multiple nodes.
        
        Args:
            node_ids: List of node IDs to score
            goal: Goal/query string
            
        Returns:
            Dictionary mapping node_id -> score_dict
        """
        query_terms = self._extract_terms(goal)
        scores = {}
        
        for node_id in node_ids:
            scores[node_id] = self.score_node(node_id, goal, query_terms)
        
        return scores

    def rank_nodes(
        self,
        node_ids: List[str],
        goal: str,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[tuple]:
        """
        Rank nodes by combined score.
        
        Args:
            node_ids: List of node IDs to rank
            goal: Goal/query string
            weights: Optional weights for relevance, freshness, risk (default: equal)
            
        Returns:
            List of (node_id, combined_score) tuples, sorted by score descending
        """
        if weights is None:
            weights = {"relevance": 0.5, "freshness": 0.3, "risk": 0.2}
        
        scores = self.score_nodes(node_ids, goal)
        
        ranked = []
        for node_id, score_dict in scores.items():
            combined = (
                score_dict["relevance"] * weights.get("relevance", 0.5) +
                score_dict["freshness"] * weights.get("freshness", 0.3) +
                score_dict["risk"] * weights.get("risk", 0.2)
            )
            ranked.append((node_id, combined))
        
        # Sort by combined score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked

