"""Context optimization package for RepoGenome.

This package provides advanced context optimization features including:
- Semantic folding for code compression
- Redundancy elimination
- Relevance scoring
- Question-aware assembly
- And many more optimization techniques
"""

from repogenome.mcp.context_optimizer.semantic_folding import SemanticFolder
from repogenome.mcp.context_optimizer.redundancy_eliminator import RedundancyEliminator
from repogenome.mcp.context_optimizer.relevance_scorer import RelevanceScorer
from repogenome.mcp.context_optimizer.question_analyzer import QuestionAnalyzer
from repogenome.mcp.context_optimizer.context_skeleton import ContextSkeleton
from repogenome.mcp.context_optimizer.hypothesis_engine import HypothesisEngine
from repogenome.mcp.context_optimizer.negative_context import NegativeContext
from repogenome.mcp.context_optimizer.context_versioning import ContextVersioner
from repogenome.mcp.context_optimizer.feature_router import FeatureRouter
from repogenome.mcp.context_optimizer.trust_levels import TrustScorer
from repogenome.mcp.context_optimizer.token_budget import AdaptiveTokenBudget
from repogenome.mcp.context_optimizer.context_contracts import ContextContract
from repogenome.mcp.context_optimizer.feedback_loop import ContextFeedbackLoop
from repogenome.mcp.context_optimizer.memory_stratification import MemoryStratifier
from repogenome.mcp.context_optimizer.context_anchors import ContextAnchor
from repogenome.mcp.context_optimizer.failure_recovery import FailureRecovery
from repogenome.mcp.context_optimizer.explain_mode import ContextExplainer
from repogenome.mcp.context_optimizer.entropy_minimizer import EntropyMinimizer
from repogenome.mcp.context_optimizer.session_memory import SessionMemory

__all__ = [
    "SemanticFolder",
    "RedundancyEliminator",
    "RelevanceScorer",
    "QuestionAnalyzer",
    "ContextSkeleton",
    "HypothesisEngine",
    "NegativeContext",
    "ContextVersioner",
    "FeatureRouter",
    "TrustScorer",
    "AdaptiveTokenBudget",
    "ContextContract",
    "ContextFeedbackLoop",
    "MemoryStratifier",
    "ContextAnchor",
    "FailureRecovery",
    "ContextExplainer",
    "EntropyMinimizer",
    "SessionMemory",
]

