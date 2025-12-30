"""Question-aware context assembly - extracts implicit needs from queries."""

import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class QuestionAnalyzer:
    """Analyzes questions to extract implicit context needs."""

    def __init__(self):
        """Initialize question analyzer."""
        # Intent patterns
        self.intent_patterns = {
            "refactor": [
                r"refactor",
                r"restructure",
                r"reorganize",
                r"improve.*code",
                r"clean.*up",
                r"optimize",
            ],
            "debug": [
                r"debug",
                r"fix.*bug",
                r"error",
                r"issue",
                r"problem",
                r"broken",
                r"not.*working",
            ],
            "document": [
                r"document",
                r"add.*comment",
                r"explain",
                r"describe",
                r"write.*doc",
            ],
            "test": [
                r"test",
                r"unit.*test",
                r"coverage",
                r"spec",
            ],
            "add_feature": [
                r"add",
                r"implement",
                r"create",
                r"new.*feature",
                r"build",
            ],
            "understand": [
                r"understand",
                r"how.*work",
                r"what.*do",
                r"explain",
                r"analyze",
            ],
        }
        
        # Context type mappings
        self.context_mappings = {
            "refactor": {
                "required": ["flows", "symbols", "tests", "dependencies"],
                "optional": ["history", "risk"],
            },
            "debug": {
                "required": ["flows", "history", "data_flow"],
                "optional": ["tests", "risk"],
            },
            "document": {
                "required": ["intent", "public_api", "summary"],
                "optional": ["examples", "usage"],
            },
            "test": {
                "required": ["flows", "symbols", "contracts"],
                "optional": ["coverage", "edge_cases"],
            },
            "add_feature": {
                "required": ["flows", "symbols", "contracts", "entry_points"],
                "optional": ["similar_features", "patterns"],
            },
            "understand": {
                "required": ["summary", "flows", "concepts"],
                "optional": ["history", "architecture"],
            },
        }

    def analyze(self, question: str) -> Dict[str, Any]:
        """
        Analyze a question to extract implicit needs.
        
        Args:
            question: Question/query string
            
        Returns:
            Dictionary with:
            - intents: List of detected intents
            - required_context: List of required context types
            - optional_context: List of optional context types
            - domains: List of domain keywords extracted
        """
        question_lower = question.lower()
        
        # Detect intents
        intents = self._detect_intents(question_lower)
        
        # Extract domains
        domains = self._extract_domains(question)
        
        # Determine required and optional context
        required_context: Set[str] = set()
        optional_context: Set[str] = set()
        
        for intent in intents:
            if intent in self.context_mappings:
                mapping = self.context_mappings[intent]
                required_context.update(mapping.get("required", []))
                optional_context.update(mapping.get("optional", []))
        
        # If no intents detected, use default
        if not intents:
            required_context = {"summary", "symbols"}
            optional_context = {"flows"}
        
        return {
            "intents": intents,
            "required_context": list(required_context),
            "optional_context": list(optional_context),
            "domains": domains,
            "original_question": question,
        }

    def _detect_intents(self, question_lower: str) -> List[str]:
        """Detect intents from question."""
        detected = []
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower, re.IGNORECASE):
                    detected.append(intent)
                    break  # Only add each intent once
        
        return detected

    def _extract_domains(self, question: str) -> List[str]:
        """Extract domain keywords from question."""
        # Common domain keywords
        domain_keywords = {
            "auth": ["auth", "authentication", "login", "session", "token"],
            "security": ["security", "secure", "crypto", "encryption", "hash"],
            "api": ["api", "endpoint", "route", "rest", "graphql"],
            "database": ["database", "db", "sql", "query", "table"],
            "user": ["user", "users", "account", "profile"],
            "payment": ["payment", "billing", "invoice", "transaction"],
            "file": ["file", "files", "upload", "download", "storage"],
            "email": ["email", "mail", "send", "notification"],
        }
        
        question_lower = question.lower()
        domains = []
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                domains.append(domain)
        
        return domains

    def rewrite_question(self, question: str) -> Dict[str, Any]:
        """
        Rewrite question to extract explicit needs.
        
        Args:
            question: Original question
            
        Returns:
            Dictionary with rewritten question and extracted needs
        """
        analysis = self.analyze(question)
        
        # Build explicit needs list
        needs = []
        
        if "refactor" in analysis["intents"]:
            needs.extend([
                "entry points for the affected code",
                "session lifecycle and state management",
                "side effects and dependencies",
                "test coverage and test cases",
            ])
        
        if "debug" in analysis["intents"]:
            needs.extend([
                "error handling paths",
                "data flow and state changes",
                "recent changes (history)",
                "related test cases",
            ])
        
        if "add_feature" in analysis["intents"]:
            needs.extend([
                "similar existing features",
                "API contracts and interfaces",
                "entry points and routing",
                "test patterns",
            ])
        
        # If no specific needs, use generic
        if not needs:
            needs = [
                "relevant code structure",
                "dependencies and relationships",
                "usage patterns",
            ]
        
        return {
            "original": question,
            "rewritten": f"Context needed: {', '.join(needs)}",
            "needs": needs,
            "analysis": analysis,
        }

