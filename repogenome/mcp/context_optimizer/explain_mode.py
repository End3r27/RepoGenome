"""Explain-My-Context mode for debugging agent behavior."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextExplainer:
    """Generates human-readable explanations for context selection."""

    def __init__(self):
        """Initialize context explainer."""

    def explain(
        self,
        context: Dict[str, Any],
        goal: str,
        included_nodes: Optional[List[str]] = None,
        excluded_nodes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate explanation for context selection.
        
        Args:
            context: Context dictionary
            goal: Task goal
            included_nodes: Optional list of included node IDs
            excluded_nodes: Optional list of excluded node IDs
            
        Returns:
            Explanation dictionary
        """
        explanation = {
            "goal": goal,
            "included": [],
            "excluded": [],
            "reasoning": [],
        }
        
        # Explain included items
        if included_nodes:
            for node_id in included_nodes[:10]:  # Limit to top 10
                reason = self._explain_inclusion(node_id, goal, context)
                explanation["included"].append({
                    "node_id": node_id,
                    "reason": reason,
                })
        
        # Explain excluded items
        if excluded_nodes:
            for node_id in excluded_nodes[:10]:  # Limit to top 10
                reason = self._explain_exclusion(node_id, goal, context)
                explanation["excluded"].append({
                    "node_id": node_id,
                    "reason": reason,
                })
        
        # Add overall reasoning
        explanation["reasoning"] = self._generate_reasoning(context, goal)
        
        return explanation

    def _explain_inclusion(
        self,
        node_id: str,
        goal: str,
        context: Dict[str, Any],
    ) -> str:
        """Explain why a node was included."""
        goal_lower = goal.lower()
        node_lower = node_id.lower()
        
        # Check if node matches goal keywords
        if any(word in node_lower for word in goal_lower.split() if len(word) > 3):
            return f"Node matches goal keywords: {goal}"
        
        # Check if node is in entry points
        if "tier_0" in context:
            entry_points = context["tier_0"].get("entry_points", [])
            if node_id in entry_points:
                return "Node is an entry point"
        
        # Check if node is in core domains
        if "tier_1" in context:
            core_domains = context["tier_1"].get("core_domains", [])
            for domain in core_domains:
                if domain.lower() in node_lower:
                    return f"Node is in core domain: {domain}"
        
        return "Node is relevant to the goal"

    def _explain_exclusion(
        self,
        node_id: str,
        goal: str,
        context: Dict[str, Any],
    ) -> str:
        """Explain why a node was excluded."""
        node_lower = node_id.lower()
        
        # Check for common exclusion reasons
        if "legacy" in node_lower:
            return "Node is in legacy code (out of scope)"
        
        if "ui" in node_lower or "frontend" in node_lower:
            return "Node is UI-related (out of scope for backend tasks)"
        
        if "test" in node_lower and "test" not in goal.lower():
            return "Node is test code (not needed for this task)"
        
        return "Node has low relevance to the goal"

    def _generate_reasoning(
        self,
        context: Dict[str, Any],
        goal: str,
    ) -> List[str]:
        """Generate overall reasoning for context selection."""
        reasoning = []
        
        # Analyze context structure
        if "tier_0" in context:
            reasoning.append("Included repository summary for high-level understanding")
        
        if "tier_1" in context:
            if "flows" in context["tier_1"]:
                reasoning.append("Included execution flows to understand runtime behavior")
            if "core_domains" in context["tier_1"]:
                reasoning.append("Included core domains relevant to the goal")
        
        if "tier_2" in context:
            if "nodes" in context["tier_2"]:
                node_count = len(context["tier_2"]["nodes"])
                reasoning.append(f"Included {node_count} relevant code symbols")
        
        if "tier_3" in context:
            reasoning.append("Included historical data for context")
        
        # Check metadata for optimization hints
        if "metadata" in context:
            metadata = context["metadata"]
            if "warnings" in metadata:
                reasoning.append(f"Applied optimizations: {len(metadata['warnings'])} adjustments made")
        
        return reasoning

    def format_explanation(self, explanation: Dict[str, Any]) -> str:
        """
        Format explanation as human-readable text.
        
        Args:
            explanation: Explanation dictionary
            
        Returns:
            Formatted explanation string
        """
        lines = [
            f"Context Explanation for: {explanation['goal']}",
            "",
            "Included:",
        ]
        
        for item in explanation.get("included", [])[:5]:
            lines.append(f"  - {item['node_id']}: {item['reason']}")
        
        if len(explanation.get("included", [])) > 5:
            lines.append(f"  ... and {len(explanation['included']) - 5} more")
        
        lines.append("")
        lines.append("Excluded:")
        
        for item in explanation.get("excluded", [])[:5]:
            lines.append(f"  - {item['node_id']}: {item['reason']}")
        
        if len(explanation.get("excluded", [])) > 5:
            lines.append(f"  ... and {len(explanation['excluded']) - 5} more")
        
        lines.append("")
        lines.append("Reasoning:")
        for reason in explanation.get("reasoning", []):
            lines.append(f"  - {reason}")
        
        return "\n".join(lines)

