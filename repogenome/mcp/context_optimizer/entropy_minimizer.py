"""Context entropy minimization for reducing ambiguity."""

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EntropyMinimizer:
    """Measures and minimizes context entropy (ambiguity)."""

    def __init__(self):
        """Initialize entropy minimizer."""

    def calculate_entropy(
        self,
        context: Dict[str, Any],
    ) -> float:
        """
        Calculate entropy (ambiguity) of context.
        
        Args:
            context: Context dictionary
            
        Returns:
            Entropy score (0.0-1.0, lower is better)
        """
        # Count unique concepts/domains
        concepts = set()
        
        # Extract from tier_1
        if "tier_1" in context:
            tier_1 = context["tier_1"]
            if "core_domains" in tier_1:
                concepts.update(tier_1["core_domains"])
        
        # Extract from tier_2 nodes
        if "tier_2" in context:
            tier_2 = context["tier_2"]
            if "nodes" in tier_2:
                nodes = tier_2["nodes"]
                for node_id in nodes.keys():
                    # Extract domain from node_id
                    parts = node_id.split(".")
                    if len(parts) > 1:
                        concepts.add(parts[0])
        
        # Calculate entropy based on concept diversity
        if len(concepts) == 0:
            return 1.0  # High entropy if no concepts
        
        if len(concepts) == 1:
            return 0.0  # Low entropy if single concept
        
        # Shannon entropy
        # More concepts = higher entropy (more ambiguity)
        # Normalize to 0-1
        max_entropy = math.log(max(len(concepts), 2))
        entropy = math.log(len(concepts)) / max_entropy if max_entropy > 0 else 0.0
        
        return min(1.0, entropy)

    def reduce_entropy(
        self,
        context: Dict[str, Any],
        target_entropy: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Reduce context entropy by adding clarifying context.
        
        Args:
            context: Context dictionary
            target_entropy: Target entropy level
            
        Returns:
            Improved context dictionary
        """
        current_entropy = self.calculate_entropy(context)
        
        if current_entropy <= target_entropy:
            return context  # Already low entropy
        
        improved = context.copy()
        
        # Add clarifying metadata
        if "metadata" not in improved:
            improved["metadata"] = {}
        
        improved["metadata"]["entropy"] = {
            "original": current_entropy,
            "target": target_entropy,
            "reduced": True,
        }
        
        # Focus on most relevant domain
        if "tier_1" in improved and "core_domains" in improved["tier_1"]:
            domains = improved["tier_1"]["core_domains"]
            if len(domains) > 1:
                # Keep only the most relevant domain
                improved["tier_1"]["core_domains"] = domains[:1]
                improved["metadata"]["entropy"]["action"] = "Focused on primary domain"
        
        return improved

    def needs_clarification(
        self,
        context: Dict[str, Any],
        threshold: float = 0.5,
    ) -> bool:
        """
        Check if context needs clarification.
        
        Args:
            context: Context dictionary
            threshold: Entropy threshold
            
        Returns:
            True if clarification is needed
        """
        entropy = self.calculate_entropy(context)
        return entropy > threshold

