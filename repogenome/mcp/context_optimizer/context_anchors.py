"""Latent context anchors for abstract concept references."""

import hashlib
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextAnchor:
    """Manages context anchors for abstract concepts."""

    def __init__(self):
        """Initialize context anchor manager."""
        self.anchors: Dict[str, Dict[str, Any]] = {}

    def create_anchor(
        self,
        concept: str,
        node_ids: List[str],
        description: Optional[str] = None,
    ) -> str:
        """
        Create an anchor for an abstract concept.
        
        Args:
            concept: Concept name (e.g., "AUTH_SESSION_LIFECYCLE")
            node_ids: List of related node IDs
            description: Optional description
            
        Returns:
            Anchor ID
        """
        anchor_id = f"ANCHOR_{concept.upper()}"
        
        self.anchors[anchor_id] = {
            "concept": concept,
            "node_ids": node_ids,
            "description": description,
            "hash": self._hash_anchor(node_ids),
        }
        
        return anchor_id

    def get_anchor(self, anchor_id: str) -> Optional[Dict[str, Any]]:
        """
        Get anchor information.
        
        Args:
            anchor_id: Anchor ID
            
        Returns:
            Anchor dictionary or None
        """
        return self.anchors.get(anchor_id)

    def resolve_anchor(self, anchor_id: str) -> List[str]:
        """
        Resolve anchor to node IDs.
        
        Args:
            anchor_id: Anchor ID
            
        Returns:
            List of node IDs
        """
        anchor = self.get_anchor(anchor_id)
        if anchor:
            return anchor.get("node_ids", [])
        return []

    def find_anchors(self, concept: str) -> List[str]:
        """
        Find anchors matching a concept.
        
        Args:
            concept: Concept name
            
        Returns:
            List of matching anchor IDs
        """
        concept_lower = concept.lower()
        matching = []
        
        for anchor_id, anchor_data in self.anchors.items():
            anchor_concept = anchor_data.get("concept", "").lower()
            if concept_lower in anchor_concept or anchor_concept in concept_lower:
                matching.append(anchor_id)
        
        return matching

    def _hash_anchor(self, node_ids: List[str]) -> str:
        """Generate hash for anchor."""
        hash_input = "|".join(sorted(node_ids))
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:16]

