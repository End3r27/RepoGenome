"""Memory stratification for short/mid/long-term context layers."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryStratifier:
    """Manages memory layers for context assembly."""

    def __init__(self):
        """Initialize memory stratifier."""
        self.layers = {
            "short_term": {
                "scope": "current_task",
                "ttl": 3600,  # 1 hour
                "max_items": 50,
            },
            "mid_term": {
                "scope": "feature_level",
                "ttl": 86400,  # 24 hours
                "max_items": 200,
            },
            "long_term": {
                "scope": "repo_identity",
                "ttl": None,  # Permanent
                "max_items": 1000,
            },
        }

    def select_layer(
        self,
        context_type: str,
        task_scope: str = "current_task",
    ) -> str:
        """
        Select appropriate memory layer.
        
        Args:
            context_type: Type of context (task, feature, repo)
            task_scope: Task scope
            
        Returns:
            Layer name (short_term, mid_term, long_term)
        """
        if context_type == "current_task" or task_scope == "current_task":
            return "short_term"
        elif context_type == "feature_level" or task_scope == "feature":
            return "mid_term"
        else:
            return "long_term"

    def get_layer_config(self, layer: str) -> Dict[str, Any]:
        """
        Get configuration for a memory layer.
        
        Args:
            layer: Layer name
            
        Returns:
            Layer configuration
        """
        return self.layers.get(layer, self.layers["short_term"])

    def should_load(
        self,
        layer: str,
        item_id: str,
        last_accessed: Optional[float] = None,
    ) -> bool:
        """
        Determine if an item should be loaded from a layer.
        
        Args:
            layer: Layer name
            item_id: Item identifier
            last_accessed: Last access timestamp (optional)
            
        Returns:
            True if item should be loaded
        """
        config = self.get_layer_config(layer)
        
        # Check TTL
        if config["ttl"] and last_accessed:
            import time
            age = time.time() - last_accessed
            if age > config["ttl"]:
                return False
        
        return True

