"""Feature-aware context routing for zero-waste context."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FeatureRouter:
    """Routes context assembly based on feature type."""

    def __init__(self):
        """Initialize feature router."""
        # Feature profiles define what context each feature needs
        self.feature_profiles = {
            "refactor": {
                "required": ["flows", "symbols", "tests", "dependencies"],
                "optional": ["history", "risk"],
                "exclude": ["ui", "legacy"],
            },
            "debug": {
                "required": ["history", "data_flow", "error_handling"],
                "optional": ["tests", "risk", "logs"],
                "exclude": ["ui"],
            },
            "document": {
                "required": ["intent", "public_api", "summary"],
                "optional": ["examples", "usage"],
                "exclude": ["implementation_details"],
            },
            "test": {
                "required": ["flows", "symbols", "contracts"],
                "optional": ["coverage", "edge_cases"],
                "exclude": ["ui"],
            },
            "add_feature": {
                "required": ["flows", "symbols", "contracts", "entry_points"],
                "optional": ["similar_features", "patterns"],
                "exclude": ["legacy"],
            },
            "understand": {
                "required": ["summary", "flows", "concepts"],
                "optional": ["history", "architecture"],
                "exclude": [],
            },
        }

    def detect_feature(self, goal: str) -> str:
        """
        Detect feature type from goal.
        
        Args:
            goal: Task goal
            
        Returns:
            Feature type string
        """
        goal_lower = goal.lower()
        
        # Check each feature type
        for feature, profile in self.feature_profiles.items():
            keywords = {
                "refactor": ["refactor", "restructure", "reorganize"],
                "debug": ["debug", "fix", "error", "bug"],
                "document": ["document", "doc", "comment"],
                "test": ["test", "spec", "coverage"],
                "add_feature": ["add", "implement", "create", "new"],
                "understand": ["understand", "explain", "how"],
            }
            
            if feature in keywords:
                if any(kw in goal_lower for kw in keywords[feature]):
                    return feature
        
        # Default to "understand"
        return "understand"

    def get_profile(self, feature: str) -> Dict[str, Any]:
        """
        Get context profile for a feature.
        
        Args:
            feature: Feature type
            
        Returns:
            Profile dictionary
        """
        return self.feature_profiles.get(feature, {
            "required": ["summary", "symbols"],
            "optional": ["flows"],
            "exclude": [],
        })

    def route(
        self,
        goal: str,
    ) -> Dict[str, Any]:
        """
        Route goal to appropriate context profile.
        
        Args:
            goal: Task goal
            
        Returns:
            Routing result with feature and profile
        """
        feature = self.detect_feature(goal)
        profile = self.get_profile(feature)
        
        return {
            "feature": feature,
            "profile": profile,
            "goal": goal,
        }

