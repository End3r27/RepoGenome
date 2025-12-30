"""Context trust levels for prioritizing high-confidence facts."""

import logging
from typing import Any, Dict, Optional

from repogenome.core.schema import Node, RepoGenome

logger = logging.getLogger(__name__)


class TrustScorer:
    """Scores context reliability/confidence."""

    def __init__(self, genome: RepoGenome):
        """
        Initialize trust scorer.
        
        Args:
            genome: RepoGenome instance
        """
        self.genome = genome

    def score_confidence(
        self,
        node_id: str,
        source: str = "static_analysis",
    ) -> float:
        """
        Score confidence level for a node.
        
        Args:
            node_id: Node ID
            source: Source type (static_analysis, inferred, agent_reported)
            
        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence by source
        base_confidence = {
            "static_analysis": 0.95,
            "inferred": 0.63,
            "agent_reported": 0.72,
        }.get(source, 0.5)
        
        if node_id not in self.genome.nodes:
            return base_confidence * 0.5  # Lower confidence if node not found
        
        node = self.genome.nodes[node_id]
        
        # Adjust based on node characteristics
        adjustments = 0.0
        
        # Higher confidence if node has summary
        if node.summary:
            adjustments += 0.05
        
        # Higher confidence if node has high criticality
        if node.criticality > 0.7:
            adjustments += 0.05
        
        # Lower confidence if node is inferred (no file)
        if not node.file:
            adjustments -= 0.1
        
        return min(1.0, max(0.0, base_confidence + adjustments))

    def score_context_chunk(
        self,
        chunk: Dict[str, Any],
        source: str = "static_analysis",
    ) -> Dict[str, float]:
        """
        Score confidence for a context chunk.
        
        Args:
            chunk: Context chunk dictionary
            source: Source type
            
        Returns:
            Dictionary with confidence scores
        """
        confidence = {
            "static_analysis": 0.95,
            "inferred": 0.63,
            "agent_reported": 0.72,
        }.get(source, 0.5)
        
        # If chunk has node_id, use node-specific scoring
        if "node_id" in chunk:
            confidence = self.score_confidence(chunk["node_id"], source)
        
        return {
            "confidence": confidence,
            "source": source,
        }

