"""Self-optimizing context feedback loop."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextFeedbackLoop:
    """Tracks and learns from context usage feedback."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize feedback loop and load existing feedback.
        
        Args:
            storage_dir: Optional storage directory for feedback data
        """
        self.storage_dir = storage_dir or Path(".cache/context_feedback")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.feedback_data: Dict[str, Any] = {}
        self._load_feedback()

    def record_feedback(
        self,
        context_id: str,
        used: Optional[List[str]] = None,
        ignored: Optional[List[str]] = None,
        missing: Optional[List[str]] = None,
    ):
        """
        Record feedback for a context.
        
        Args:
            context_id: Context identifier
            used: List of context elements that were used
            ignored: List of context elements that were ignored
            missing: List of context elements that were missing
        """
        feedback = {
            "used": used or [],
            "ignored": ignored or [],
            "missing": missing or [],
            "timestamp": self._get_timestamp(),
        }
        
        self.feedback_data[context_id] = feedback
        self._save_feedback()

    def get_feedback(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Get feedback for a context.
        
        Args:
            context_id: Context identifier
            
        Returns:
            Feedback dictionary or None
        """
        return self.feedback_data.get(context_id)

    def learn_patterns(self) -> Dict[str, Any]:
        """
        Learn patterns from accumulated feedback.
        
        Returns:
            Learned patterns dictionary
        """
        patterns = {
            "commonly_used": {},
            "commonly_ignored": {},
            "commonly_missing": {},
        }
        
        # Aggregate feedback
        for context_id, feedback in self.feedback_data.items():
            for element in feedback.get("used", []):
                patterns["commonly_used"][element] = patterns["commonly_used"].get(element, 0) + 1
            
            for element in feedback.get("ignored", []):
                patterns["commonly_ignored"][element] = patterns["commonly_ignored"].get(element, 0) + 1
            
            for element in feedback.get("missing", []):
                patterns["commonly_missing"][element] = patterns["commonly_missing"].get(element, 0) + 1
        
        return patterns

    def adjust_context_assembly(
        self,
        goal: str,
        base_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Adjust context assembly based on learned patterns.
        
        Args:
            goal: Task goal
            base_context: Base context dictionary
            
        Returns:
            Adjusted context dictionary
        """
        patterns = self.learn_patterns()
        
        # Prioritize commonly used elements
        commonly_used = patterns.get("commonly_used", {})
        
        # Deprioritize commonly ignored elements
        commonly_ignored = patterns.get("commonly_ignored", {})
        
        # Add commonly missing elements
        commonly_missing = patterns.get("commonly_missing", {})
        
        # Adjust context (simplified - could be more sophisticated)
        adjusted = base_context.copy()
        
        # Mark elements with usage hints
        if "metadata" not in adjusted:
            adjusted["metadata"] = {}
        
        adjusted["metadata"]["usage_hints"] = {
            "prioritize": list(commonly_used.keys())[:5],
            "deprioritize": list(commonly_ignored.keys())[:5],
            "consider_adding": list(commonly_missing.keys())[:5],
        }
        
        return adjusted

    def _save_feedback(self):
        """Save feedback to disk."""
        feedback_file = self.storage_dir / "feedback.json"
        
        try:
            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump(self.feedback_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")

    def _load_feedback(self):
        """Load feedback from disk."""
        feedback_file = self.storage_dir / "feedback.json"
        
        if not feedback_file.exists():
            return
        
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                self.feedback_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load feedback: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

