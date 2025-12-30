"""Context contracts for enforcing context requirements."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextContract:
    """Defines and validates context contracts."""

    def __init__(
        self,
        must_include: Optional[List[str]] = None,
        optional: Optional[List[str]] = None,
        forbidden: Optional[List[str]] = None,
    ):
        """
        Initialize context contract.
        
        Args:
            must_include: List of required context elements
            optional: List of optional context elements
            forbidden: List of forbidden context elements
        """
        self.must_include = must_include or []
        self.optional = optional or []
        self.forbidden = forbidden or []

    def validate(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate context against contract.
        
        Args:
            context: Context dictionary to validate
            
        Returns:
            Validation result with violations
        """
        violations = {
            "missing_required": [],
            "forbidden_present": [],
        }
        
        # Check required elements
        for required in self.must_include:
            if not self._has_element(context, required):
                violations["missing_required"].append(required)
        
        # Check forbidden elements
        for forbidden in self.forbidden:
            if self._has_element(context, forbidden):
                violations["forbidden_present"].append(forbidden)
        
        is_valid = (
            len(violations["missing_required"]) == 0 and
            len(violations["forbidden_present"]) == 0
        )
        
        return {
            "valid": is_valid,
            "violations": violations,
        }

    def _has_element(
        self,
        context: Dict[str, Any],
        element: str,
    ) -> bool:
        """Check if context has an element."""
        # Check in different tiers
        for tier in ["tier_0", "tier_1", "tier_2", "tier_3"]:
            if tier in context:
                tier_data = context[tier]
                
                # Check various element types
                if element == "flows" and "flows" in tier_data:
                    return True
                if element == "symbols" and "nodes" in tier_data:
                    return True
                if element == "history" and "history" in tier_data:
                    return True
                if element == "tests" and "tests" in tier_data:
                    return True
                if element == "auth_flow" and self._has_auth_flow(tier_data):
                    return True
                if element == "jwt_validation" and self._has_jwt_validation(tier_data):
                    return True
        
        return False

    def _has_auth_flow(self, tier_data: Dict[str, Any]) -> bool:
        """Check if tier has auth flow."""
        if "flows" in tier_data:
            flows = tier_data["flows"]
            if isinstance(flows, list):
                for flow in flows:
                    if isinstance(flow, dict):
                        path = flow.get("path", [])
                        if any("auth" in str(p).lower() or "login" in str(p).lower() for p in path):
                            return True
        return False

    def _has_jwt_validation(self, tier_data: Dict[str, Any]) -> bool:
        """Check if tier has JWT validation."""
        if "nodes" in tier_data:
            nodes = tier_data["nodes"]
            if isinstance(nodes, dict):
                for node_id in nodes.keys():
                    if "jwt" in node_id.lower() or "token" in node_id.lower():
                        return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert contract to dictionary."""
        return {
            "must_include": self.must_include,
            "optional": self.optional,
            "forbidden": self.forbidden,
        }

