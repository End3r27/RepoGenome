"""Context Assembler for goal-driven context selection from RepoGenome."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from repogenome.core.schema import RepoGenome
from repogenome.mcp.context_optimizer import (
    AdaptiveTokenBudget,
    ContextAnchor,
    ContextContract,
    ContextExplainer,
    ContextFeedbackLoop,
    ContextSkeleton,
    ContextVersioner,
    EntropyMinimizer,
    FailureRecovery,
    FeatureRouter,
    HypothesisEngine,
    MemoryStratifier,
    NegativeContext,
    QuestionAnalyzer,
    RedundancyEliminator,
    RelevanceScorer,
    SemanticFolder,
    SessionMemory,
    TrustScorer,
)
from repogenome.utils.fingerprint import generate_fingerprint
from repogenome.utils.token_estimator import estimate_context_tokens, truncate_to_budget

logger: logging.Logger = logging.getLogger(__name__)


class Scope:
    """Scope information for context selection."""

    def __init__(
        self,
        domains: List[str],
        include_flows: bool = True,
        include_history: bool = False,
        prefer_recent: bool = False,
        include_contracts: bool = False,
    ):
        """
        Initialize scope.

        Args:
            domains: List of domain/scope names (e.g., ["auth", "security"])
            include_flows: Whether to include execution flows
            include_history: Whether to include historical data
            prefer_recent: Prefer recently changed files
            include_contracts: Whether to include contract information
        """
        self.domains = domains
        self.include_flows = include_flows
        self.include_history = include_history
        self.prefer_recent = prefer_recent
        self.include_contracts = include_contracts


class ContextAssembler:
    """Assembles context from RepoGenome based on goals and constraints."""

    def __init__(
        self,
        genome: RepoGenome,
        enable_optimizations: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize context assembler.

        Args:
            genome: RepoGenome instance
            enable_optimizations: Enable advanced optimizations (default: True)
            cache_dir: Optional cache directory for optimizations
        """
        self.genome = genome
        self.enable_optimizations = enable_optimizations
        self.cache_dir = cache_dir or Path(".cache/context")
        
        # Initialize optimizers
        if enable_optimizations:
            self.semantic_folder = SemanticFolder()
            self.redundancy_eliminator = RedundancyEliminator(genome)
            self.relevance_scorer = RelevanceScorer(genome)
            self.question_analyzer = QuestionAnalyzer()
            self.context_skeleton = ContextSkeleton()
            self.hypothesis_engine = HypothesisEngine(genome)
            self.negative_context = NegativeContext()
            self.context_versioner = ContextVersioner(cache_dir)
            self.feature_router = FeatureRouter()
            self.trust_scorer = TrustScorer(genome)
            self.token_budget = AdaptiveTokenBudget()
            self.feedback_loop = ContextFeedbackLoop(cache_dir)
            self.memory_stratifier = MemoryStratifier()
            self.context_anchor = ContextAnchor()
            self.failure_recovery = FailureRecovery()
            self.context_explainer = ContextExplainer()
            self.entropy_minimizer = EntropyMinimizer()
            self.session_memory = SessionMemory(cache_dir)

    def build(
        self, goal: str, constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build context from RepoGenome based on goal and constraints.

        Args:
            goal: Task goal/intent (e.g., "refactor authentication flow")
            constraints: Optional constraints (maxTokens, preferRecent, etc.)

        Returns:
            Context dictionary with tiered structure
        """
        if constraints is None:
            constraints = {}

        # Question-aware analysis
        if self.enable_optimizations:
            question_analysis = self.question_analyzer.analyze(goal)
            rewritten = self.question_analyzer.rewrite_question(goal)
            goal = rewritten.get("rewritten", goal)
        else:
            question_analysis = None

        # Feature routing
        if self.enable_optimizations:
            routing = self.feature_router.route(goal)
            feature_profile = routing.get("profile", {})
        else:
            routing = None
            feature_profile = {}

        # Resolve scope from goal (enhanced with question analysis)
        scope = self._resolve_scope(goal, constraints, question_analysis)

        # Get max tokens from constraints (default: 2000)
        max_tokens = constraints.get("maxTokens", 2000)
        self.token_budget = AdaptiveTokenBudget(max_tokens=max_tokens)

        # Build tiered context
        context: Dict[str, Any] = {
            "tier_0": self._build_tier_0(),
            "tier_1": self._build_tier_1(scope),
            "tier_2": self._build_tier_2(scope, max_tokens),
            "tier_3": self._build_tier_3(scope),
        }

        # Apply negative context (exclusions)
        if self.enable_optimizations:
            exclusions = self.negative_context.determine_exclusions(goal, scope.domains)
            if exclusions:
                # Filter nodes based on exclusions
                if "tier_2" in context and "nodes" in context["tier_2"]:
                    node_ids = list(context["tier_2"]["nodes"].keys())
                    filtered_ids = self.negative_context.filter_nodes(node_ids, exclusions)
                    context["tier_2"]["nodes"] = {
                        nid: context["tier_2"]["nodes"][nid]
                        for nid in filtered_ids
                    }

        # Apply semantic folding to reduce tokens
        if self.enable_optimizations and "tier_2" in context and "nodes" in context["tier_2"]:
            nodes = context["tier_2"]["nodes"]
            folded_nodes = {}
            for node_id, node_data in nodes.items():
                if isinstance(node_data, dict) and node_id in self.genome.nodes:
                    node = self.genome.nodes[node_id]
                    semantic = self.semantic_folder.fold_node(node, node_id)
                    # Merge semantic summary into node data
                    node_data["semantic"] = semantic
                    folded_nodes[node_id] = node_data
                else:
                    folded_nodes[node_id] = node_data
            context["tier_2"]["nodes"] = folded_nodes

        # Eliminate redundancy
        if self.enable_optimizations and "tier_2" in context and "nodes" in context["tier_2"]:
            node_ids = list(context["tier_2"]["nodes"].keys())
            dedup_result = self.redundancy_eliminator.eliminate_redundancy(node_ids)
            # Keep only unique nodes
            unique_nodes = dedup_result["unique_nodes"]
            context["tier_2"]["nodes"] = {
                nid: context["tier_2"]["nodes"][nid]
                for nid in unique_nodes
            }
            if dedup_result["duplicate_groups"]:
                context["metadata"] = context.get("metadata", {})
                context["metadata"]["duplicate_groups"] = dedup_result["duplicate_groups"]

        # Score relevance and sort
        if self.enable_optimizations and "tier_2" in context and "nodes" in context["tier_2"]:
            node_ids = list(context["tier_2"]["nodes"].keys())
            scores = self.relevance_scorer.score_nodes(node_ids, goal)
            ranked = self.relevance_scorer.rank_nodes(node_ids, goal)
            
            # Reorder nodes by relevance
            sorted_nodes = {}
            for node_id, _ in ranked:
                if node_id in context["tier_2"]["nodes"]:
                    node_data = context["tier_2"]["nodes"][node_id]
                    # Add scores to node data
                    if isinstance(node_data, dict):
                        node_data["context_score"] = scores[node_id]
                        # Add trust score
                        node_data["confidence"] = self.trust_scorer.score_confidence(node_id)
                    sorted_nodes[node_id] = node_data
            context["tier_2"]["nodes"] = sorted_nodes

        # Enforce token budget (enhanced)
        context, warnings = self._enforce_token_budget(context, max_tokens)

        # Minimize entropy
        if self.enable_optimizations:
            entropy = self.entropy_minimizer.calculate_entropy(context)
            if self.entropy_minimizer.needs_clarification(context):
                context = self.entropy_minimizer.reduce_entropy(context)
                context["metadata"] = context.get("metadata", {})
                context["metadata"]["entropy"] = entropy

        # Generate hypotheses
        if self.enable_optimizations:
            hypotheses = self.hypothesis_engine.generate_hypotheses(goal, context)
            if hypotheses:
                context["assumptions"] = hypotheses

        # Add metadata
        context["metadata"] = context.get("metadata", {})
        context["metadata"].update({
            "goal": goal,
            "scope": scope.domains,
            "tokens_budget": max_tokens,
            "tokens_used": estimate_context_tokens(context)["total"],
            "warnings": warnings,
        })

        # Add out_of_scope exclusions
        if self.enable_optimizations:
            exclusions = self.negative_context.determine_exclusions(goal, scope.domains)
            if exclusions:
                context["out_of_scope"] = exclusions

        # Version context
        if self.enable_optimizations:
            version = self.context_versioner.generate_version(goal, context)
            context["context_version"] = version
            self.context_versioner.save_version(version, context, {"goal": goal})

        # Add fingerprint
        context["context_fingerprint"] = generate_fingerprint(context)

        return context

    def _resolve_scope(
        self,
        goal: str,
        constraints: Dict[str, Any],
        question_analysis: Optional[Dict[str, Any]] = None,
    ) -> Scope:
        """
        Resolve scope from goal string.

        Args:
            goal: Task goal/intent
            constraints: Constraint dictionary
            question_analysis: Optional question analysis result

        Returns:
            Scope object
        """
        goal_lower = goal.lower()
        
        # Use question analysis if available
        if question_analysis and self.enable_optimizations:
            domains = question_analysis.get("domains", [])
            required_context = question_analysis.get("required_context", [])
            
            include_flows = "flows" in required_context
            include_history = "history" in required_context
            include_contracts = "contracts" in required_context or "public_api" in required_context
            prefer_recent = "recent" in goal_lower or "recent" in str(required_context).lower()
            
            return Scope(
                domains=domains,
                include_flows=include_flows,
                include_history=include_history,
                prefer_recent=prefer_recent,
                include_contracts=include_contracts,
            )

        # Default scope
        domains: List[str] = []
        include_flows = True
        include_history = False
        prefer_recent = constraints.get("preferRecent", False)
        include_contracts = False

        # Pattern matching for common goals
        if "refactor" in goal_lower or "refactoring" in goal_lower:
            # Extract domain from goal (e.g., "refactor authentication" -> ["auth"])
            domains = self._extract_domains_from_goal(goal)
            include_flows = True
            include_history = True
            prefer_recent = True

        elif "add" in goal_lower or "implement" in goal_lower or "feature" in goal_lower:
            domains = self._extract_domains_from_goal(goal)
            include_flows = True
            include_contracts = True

        elif "fix" in goal_lower or "bug" in goal_lower:
            domains = self._extract_domains_from_goal(goal)
            include_flows = True
            include_history = True
            prefer_recent = True

        elif "understand" in goal_lower or "architecture" in goal_lower:
            # No specific domain, include all core domains
            domains = self.genome.summary.core_domains
            include_flows = False
            include_history = False

        else:
            # Try to extract domains from goal
            domains = self._extract_domains_from_goal(goal)

        # Override with explicit scope if provided
        if "scope" in constraints:
            explicit_scope = constraints["scope"]
            if isinstance(explicit_scope, list):
                domains = explicit_scope

        return Scope(
            domains=domains,
            include_flows=include_flows,
            include_history=include_history,
            prefer_recent=prefer_recent,
            include_contracts=include_contracts,
        )

    def _extract_domains_from_goal(self, goal: str) -> List[str]:
        """
        Extract domain names from goal string.

        Args:
            goal: Goal string

        Returns:
            List of domain names
        """
        domains: List[str] = []
        goal_lower = goal.lower()

        # Common domain keywords
        domain_keywords = {
            "auth": ["authentication", "auth", "login", "session"],
            "security": ["security", "secure", "crypto", "encryption"],
            "api": ["api", "endpoint", "route", "rest"],
            "database": ["database", "db", "sql", "query"],
            "user": ["user", "users", "account", "profile"],
            "payment": ["payment", "billing", "invoice", "transaction"],
        }

        # Check core domains from genome
        for core_domain in self.genome.summary.core_domains:
            if core_domain.lower() in goal_lower:
                domains.append(core_domain.lower())

        # Check keyword mappings
        for domain, keywords in domain_keywords.items():
            if any(keyword in goal_lower for keyword in keywords):
                if domain not in domains:
                    domains.append(domain)

        return domains

    def _build_tier_0(self) -> Dict[str, Any]:
        """
        Build Tier 0: High-level repo intent.

        Returns:
            Tier 0 context dictionary
        """
        return {
            "summary": self.genome.summary.model_dump(),
            "entry_points": self.genome.summary.entry_points,
        }

    def _build_tier_1(self, scope: Scope) -> Dict[str, Any]:
        """
        Build Tier 1: Relevant architecture & flows.

        Args:
            scope: Scope object

        Returns:
            Tier 1 context dictionary
        """
        tier_1: Dict[str, Any] = {
            "core_domains": [
                d for d in self.genome.summary.core_domains if not scope.domains or d.lower() in [s.lower() for s in scope.domains]
            ],
        }

        if scope.include_flows:
            # Select relevant flows
            relevant_flows = self._select_flows(scope, limit=10)
            tier_1["flows"] = [flow.model_dump(mode="json") for flow in relevant_flows]

        return tier_1

    def _build_tier_2(self, scope: Scope, budget: int) -> Dict[str, Any]:
        """
        Build Tier 2: Exact symbols & code snippets.

        Args:
            scope: Scope object
            budget: Token budget

        Returns:
            Tier 2 context dictionary
        """
        # Select relevant symbols
        symbol_ids = self._select_symbols(scope, budget=budget)

        # Get nodes and edges
        nodes: Dict[str, Any] = {}
        edges: List[Dict[str, Any]] = []

        for node_id in symbol_ids:
            if node_id in self.genome.nodes:
                node = self.genome.nodes[node_id]
                nodes[node_id] = node.model_dump(mode="json")

                # Get related edges
                for edge in self.genome.edges:
                    if edge.from_ == node_id or edge.to == node_id:
                        edge_dict = edge.model_dump(mode="json", by_alias=True)
                        if edge_dict not in edges:
                            edges.append(edge_dict)

        tier_2: Dict[str, Any] = {
            "nodes": nodes,
            "edges": edges,
        }

        if scope.include_contracts:
            # Include relevant contracts
            relevant_contracts = {
                node_id: contract.model_dump(mode="json")
                for node_id, contract in self.genome.contracts.items()
                if node_id in symbol_ids
            }
            tier_2["contracts"] = relevant_contracts

        return tier_2

    def _build_tier_3(self, scope: Scope) -> Dict[str, Any]:
        """
        Build Tier 3: Historical / optional info.

        Args:
            scope: Scope object

        Returns:
            Tier 3 context dictionary
        """
        tier_3: Dict[str, Any] = {}

        if scope.include_history:
            # Select relevant history
            relevant_history = self._select_history(scope)
            tier_3["history"] = {
                k: v.model_dump(mode="json") for k, v in relevant_history.items()
            }

            # Include risk scores for selected nodes
            relevant_risk = {
                node_id: risk.model_dump(mode="json")
                for node_id, risk in self.genome.risk.items()
                if node_id in relevant_history
            }
            tier_3["risk"] = relevant_risk

        return tier_3

    def _select_symbols(self, scope: Scope, budget: int) -> List[str]:
        """
        Select relevant symbol/node IDs based on scope.

        Args:
            scope: Scope object
            budget: Token budget (approximate)

        Returns:
            List of node IDs
        """
        selected: Set[str] = set()

        # If no specific domains, return entry points
        if not scope.domains:
            selected.update(self.genome.summary.entry_points)
            return list(selected)[:50]  # Limit to 50

        # Find nodes matching domains
        for domain in scope.domains:
            domain_lower = domain.lower()

            # Check concepts/intents
            for concept_id, concept in self.genome.concepts.items():
                if domain_lower in concept_id.lower():
                    selected.update(concept.nodes)

            # Check node IDs and files
            for node_id, node in self.genome.nodes.items():
                if domain_lower in node_id.lower():
                    selected.add(node_id)
                if node.file and domain_lower in node.file.lower():
                    selected.add(node_id)

        # If prefer_recent, prioritize recently changed files
        if scope.prefer_recent:
            recent_nodes = []
            other_nodes = []

            for node_id in selected:
                if node_id in self.genome.history:
                    churn = self.genome.history[node_id].churn_score
                    if churn > 0.5:
                        recent_nodes.append(node_id)
                    else:
                        other_nodes.append(node_id)
                else:
                    other_nodes.append(node_id)

            selected = list(recent_nodes) + list(other_nodes)
        else:
            selected = list(selected)

        # Limit based on budget (rough estimate: ~50 tokens per node)
        max_nodes = max(10, budget // 50)
        return selected[:max_nodes]

    def _select_flows(self, scope: Scope, limit: int = 10) -> List:
        """
        Select relevant flows based on scope.

        Args:
            scope: Scope object
            limit: Maximum number of flows

        Returns:
            List of Flow objects
        """
        if not scope.domains:
            # Return flows from entry points
            entry_flows = [
                flow
                for flow in self.genome.flows
                if flow.entry in self.genome.summary.entry_points
            ]
            return entry_flows[:limit]

        # Find flows involving selected nodes
        selected_flows = []
        domain_nodes = set()

        # Get nodes matching domains
        for domain in scope.domains:
            domain_lower = domain.lower()
            for node_id in self.genome.nodes:
                if domain_lower in node_id.lower():
                    domain_nodes.add(node_id)

        # Find flows containing domain nodes
        for flow in self.genome.flows:
            if any(node_id in flow.path for node_id in domain_nodes):
                selected_flows.append(flow)

        return selected_flows[:limit]

    def _select_history(self, scope: Scope) -> Dict[str, Any]:
        """
        Select relevant history based on scope.

        Args:
            scope: Scope object

        Returns:
            Dictionary of history entries
        """
        if not scope.domains:
            return {}

        selected: Dict[str, Any] = {}

        # Find history for nodes matching domains
        for domain in scope.domains:
            domain_lower = domain.lower()

            for node_id, history in self.genome.history.items():
                if domain_lower in node_id.lower():
                    selected[node_id] = history

                # Also check if node file matches
                if node_id in self.genome.nodes:
                    node = self.genome.nodes[node_id]
                    if node.file and domain_lower in node.file.lower():
                        selected[node_id] = history

        return selected

    def _enforce_token_budget(
        self, context: Dict[str, Any], max_tokens: int
    ) -> tuple:
        """
        Enforce token budget by truncating/reducing content.

        Args:
            context: Context dictionary
            max_tokens: Maximum token budget

        Returns:
            Tuple of (adjusted_context, warnings)
        """
        warnings: List[str] = []
        token_counts = estimate_context_tokens(context)
        total_tokens = token_counts.get("total", 0)

        if total_tokens <= max_tokens:
            return context, warnings

        warnings.append(
            f"Context exceeds token budget: {total_tokens} > {max_tokens}. Truncating..."
        )

        # Priority: Tier 0 > Tier 1 > Tier 2 > Tier 3
        # Reduce from lowest priority tiers first

        excess_tokens = total_tokens - max_tokens

        # Reduce Tier 3 first (historical/optional info)
        if "tier_3" in context and excess_tokens > 0:
            tier_3_tokens = token_counts.get("tier_3", 0)
            reduction = min(excess_tokens, tier_3_tokens)
            if reduction > 0:
                # Remove some history entries
                if "history" in context["tier_3"]:
                    history = context["tier_3"]["history"]
                    # Keep only top entries (by churn score)
                    if isinstance(history, dict) and len(history) > 5:
                        sorted_items = sorted(
                            history.items(),
                            key=lambda x: (
                                x[1].get("churn_score", 0) if isinstance(x[1], dict) else 0
                            ),
                            reverse=True,
                        )
                        context["tier_3"]["history"] = dict(sorted_items[:5])
                excess_tokens -= reduction

        # Reduce Tier 2 (symbols) if still over budget
        if "tier_2" in context and excess_tokens > 0:
            tier_2_tokens = token_counts.get("tier_2", 0)
            reduction = min(excess_tokens, tier_2_tokens // 2)  # Reduce by half at most
            
            if reduction > 0 and "nodes" in context["tier_2"]:
                nodes = context["tier_2"]["nodes"]
                if isinstance(nodes, dict) and len(nodes) > 10:
                    # Keep only top nodes (by criticality or importance)
                    sorted_items = sorted(
                        nodes.items(),
                        key=lambda x: (
                            x[1].get("criticality", 0) if isinstance(x[1], dict) else 0
                        ),
                        reverse=True,
                    )
                    max_nodes = max(10, len(sorted_items) - reduction // 50)
                    context["tier_2"]["nodes"] = dict(sorted_items[:max_nodes])
                
                # Also truncate summaries in nodes
                for node_data in context["tier_2"]["nodes"].values():
                    if isinstance(node_data, dict) and "summary" in node_data:
                        summary = node_data["summary"]
                        if isinstance(summary, str) and len(summary) > 100:
                            node_data["summary"] = truncate_to_budget(summary, 100)

        # Reduce Tier 1 (flows) if still over budget
        if "tier_1" in context and excess_tokens > 0:
            tier_1_tokens = token_counts.get("tier_1", 0)
            if "flows" in context["tier_1"] and isinstance(context["tier_1"]["flows"], list):
                flows = context["tier_1"]["flows"]
                if len(flows) > 5:
                    context["tier_1"]["flows"] = flows[:5]

        return context, warnings

