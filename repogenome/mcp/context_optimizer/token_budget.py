"""Adaptive token budgeting for intelligent context trimming."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AdaptiveTokenBudget:
    """Manages dynamic token budget allocation."""

    def __init__(
        self,
        max_tokens: int = 2000,
        reserved_for_code: int = 400,
    ):
        """
        Initialize adaptive token budget.
        
        Args:
            max_tokens: Maximum total tokens
            reserved_for_code: Tokens reserved for code snippets
        """
        self.max_tokens = max_tokens
        self.reserved_for_code = reserved_for_code
        self.used_tokens = 0

    def allocate(
        self,
        tier: str,
        priority: float = 0.5,
    ) -> int:
        """
        Allocate tokens for a tier.
        
        Args:
            tier: Tier name (tier_0, tier_1, tier_2, tier_3)
            priority: Priority level (0.0-1.0)
            
        Returns:
            Allocated token budget
        """
        # Base allocation by tier
        base_allocation = {
            "tier_0": 200,  # High priority - summary
            "tier_1": 400,  # Medium priority - architecture
            "tier_2": 1000,  # High priority - code
            "tier_3": 400,  # Low priority - history
        }.get(tier, 200)
        
        # Adjust by priority
        allocated = int(base_allocation * priority)
        
        # Ensure we don't exceed max
        available = self.max_tokens - self.used_tokens - self.reserved_for_code
        allocated = min(allocated, available)
        
        return max(0, allocated)

    def track_usage(self, tokens: int):
        """
        Track token usage.
        
        Args:
            tokens: Number of tokens used
        """
        self.used_tokens += tokens

    def get_status(self) -> Dict[str, Any]:
        """
        Get current budget status.
        
        Returns:
            Status dictionary
        """
        return {
            "max": self.max_tokens,
            "used": self.used_tokens,
            "reserved_for_code": self.reserved_for_code,
            "available": self.max_tokens - self.used_tokens - self.reserved_for_code,
        }

    def can_fit(self, estimated_tokens: int) -> bool:
        """
        Check if estimated tokens can fit in budget.
        
        Args:
            estimated_tokens: Estimated token count
            
        Returns:
            True if tokens can fit
        """
        available = self.max_tokens - self.used_tokens - self.reserved_for_code
        return estimated_tokens <= available

