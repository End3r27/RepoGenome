"""Agent contract enforcement for RepoGenome MCP."""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class RepairStrategy(str, Enum):
    """Repair strategies for contract violations."""
    FIELD_RELAXATION = "field_relaxation"
    SCOPE_REDUCTION = "scope_reduction"
    TOKEN_BUDGET_REDUCTION = "token_budget_reduction"
    CONTEXT_EXPANSION = "context_expansion"
    AUTO_SCAN_IF_MISSING = "auto_scan_if_missing"


@dataclass
class RepairResult:
    """Result of a repair attempt."""
    success: bool
    result: Optional[Dict[str, Any]] = None
    suggestions: List[str] = None
    repair_strategy: Optional[RepairStrategy] = None
    modified_params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class ContextDependency:
    """Context dependency declaration."""
    context: str  # e.g., "repogenome@auth-v3"
    fingerprint: Optional[str] = None  # e.g., "sha256:83af..."
    required_fields: List[str] = None  # e.g., ["summary", "flows"]

    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []


@dataclass
class ToolContract:
    """Contract definition for a specific tool."""
    tool_name: str
    requires_genome: bool
    required_params: List[str] = None
    preferred_params: List[str] = None
    optional_params: List[str] = None
    compliance_weights: Dict[str, float] = None
    repair_strategies: List[RepairStrategy] = None
    requires_impact_check: bool = False
    requires_validation: bool = False
    
    def __post_init__(self):
        if self.required_params is None:
            self.required_params = []
        if self.preferred_params is None:
            self.preferred_params = []
        if self.optional_params is None:
            self.optional_params = []
        if self.compliance_weights is None:
            self.compliance_weights = {}
        if self.repair_strategies is None:
            self.repair_strategies = []


class ContextLock:
    """Manages sticky context lock for RepoGenome."""
    
    def __init__(self):
        """Initialize context lock."""
        self._locked = False
        self._lock_reason: Optional[str] = None
        self._lock_timestamp: Optional[float] = None
    
    def lock(self, reason: str = "genome_loaded"):
        """
        Lock context for session duration.
        
        Args:
            reason: Reason for locking
        """
        import time
        self._locked = True
        self._lock_reason = reason
        self._lock_timestamp = time.time()
    
    def unlock(self):
        """Unlock context (explicit reset)."""
        self._locked = False
        self._lock_reason = None
        self._lock_timestamp = None
    
    def is_locked(self) -> bool:
        """Check if context is locked."""
        return self._locked
    
    def get_lock_info(self) -> Dict[str, Any]:
        """Get lock information."""
        return {
            "locked": self._locked,
            "reason": self._lock_reason,
            "timestamp": self._lock_timestamp,
        }


class ContractCompliance:
    """Graded compliance scoring for contracts."""
    
    def __init__(
        self,
        required: List[str] = None,
        preferred: List[str] = None,
        optional: List[str] = None,
        preferred_weight: float = 0.65,
        optional_weight: float = 0.2,
    ):
        """
        Initialize compliance scoring.
        
        Args:
            required: Required fields (must be present)
            preferred: Preferred fields (weighted scoring)
            optional: Optional fields (bonus points)
            preferred_weight: Weight for preferred fields (0.5-0.8)
            optional_weight: Weight for optional fields (0.1-0.3)
        """
        self.required = required or []
        self.preferred = preferred or []
        self.optional = optional or []
        self.preferred_weight = max(0.5, min(0.8, preferred_weight))
        self.optional_weight = max(0.1, min(0.3, optional_weight))
    
    def score(self, available_fields: Set[str]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate compliance score.
        
        Args:
            available_fields: Set of available field names
            
        Returns:
            Tuple of (score, details)
        """
        details = {
            "required": {},
            "preferred": {},
            "optional": {},
        }
        
        # Check required fields (score = 0 if any missing)
        required_score = 1.0
        for field in self.required:
            present = field in available_fields
            details["required"][field] = present
            if not present:
                required_score = 0.0
        
        if required_score == 0.0:
            return 0.0, details
        
        # Score preferred fields
        preferred_score = 0.0
        if self.preferred:
            present_count = sum(1 for f in self.preferred if f in available_fields)
            preferred_score = (present_count / len(self.preferred)) * self.preferred_weight
            for field in self.preferred:
                details["preferred"][field] = field in available_fields
        
        # Score optional fields (bonus)
        optional_score = 0.0
        if self.optional:
            present_count = sum(1 for f in self.optional if f in available_fields)
            optional_score = (present_count / len(self.optional)) * self.optional_weight
            for field in self.optional:
                details["optional"][field] = field in available_fields
        
        # Total score: required (base) + preferred + optional
        total_score = required_score + preferred_score + optional_score
        # Normalize to 0-1 range
        max_possible = 1.0 + self.preferred_weight + self.optional_weight
        normalized_score = min(1.0, total_score / max_possible)
        
        details["score"] = normalized_score
        details["breakdown"] = {
            "required": required_score,
            "preferred": preferred_score,
            "optional": optional_score,
        }
        
        return normalized_score, details


class ContractRepair:
    """Handles repair strategies for contract violations."""
    
    def __init__(self, max_attempts: int = 2, auto_repair: bool = True):
        """
        Initialize repair handler.
        
        Args:
            max_attempts: Maximum repair attempts
            auto_repair: Whether to auto-repair simple cases
        """
        self.max_attempts = max_attempts
        self.auto_repair = auto_repair
        self.repair_history: List[Dict[str, Any]] = []
    
    def attempt_repair(
        self,
        error: Dict[str, Any],
        original_params: Dict[str, Any],
        attempt: int = 1,
    ) -> RepairResult:
        """
        Attempt to repair a contract violation.
        
        Args:
            error: Error dictionary
            original_params: Original parameters that caused the error
            attempt: Current attempt number
            
        Returns:
            RepairResult with success status and suggestions
        """
        if attempt > self.max_attempts:
            return RepairResult(
                success=False,
                suggestions=["Max repair attempts reached. Manual intervention required."],
            )
        
        error_reason = error.get("reason", "").lower()
        error_type = error.get("error", "").lower()
        
        # Track repair attempt
        repair_record = {
            "attempt": attempt,
            "error_reason": error_reason,
            "error_type": error_type,
            "timestamp": __import__("time").time(),
        }
        
        # Strategy 1: Genome not loaded -> suggest scan
        if "genome not loaded" in error_type or "genome not available" in error_type:
            repair_record["strategy"] = RepairStrategy.AUTO_SCAN_IF_MISSING
            self.repair_history.append(repair_record)
            return RepairResult(
                success=False,  # Can't auto-repair, needs user action
                suggestions=[
                    "Run repogenome.scan to generate genome",
                    "Or load repogenome://current resource",
                ],
                repair_strategy=RepairStrategy.AUTO_SCAN_IF_MISSING,
            )
        
        # Strategy 2: Contract violation -> field relaxation
        if "contract violation" in error_type or "contract" in error_reason:
            # Try field relaxation
            if self.auto_repair and "fields" in original_params:
                modified = original_params.copy()
                # Drop optional fields, keep only essential
                if isinstance(modified.get("fields"), list):
                    essential_fields = ["id", "type", "file", "summary"]
                    modified["fields"] = [f for f in modified["fields"] if f in essential_fields]
                    repair_record["strategy"] = RepairStrategy.FIELD_RELAXATION
                    repair_record["modified_params"] = modified
                    self.repair_history.append(repair_record)
                    return RepairResult(
                        success=True,
                        modified_params=modified,
                        repair_strategy=RepairStrategy.FIELD_RELAXATION,
                        suggestions=["Relaxed field requirements, retrying with essential fields only"],
                    )
            
            repair_record["strategy"] = RepairStrategy.FIELD_RELAXATION
            self.repair_history.append(repair_record)
            return RepairResult(
                success=False,
                suggestions=[
                    "Try reducing field requirements",
                    "Use fields=['id', 'type', 'file'] for minimal context",
                    "Or use ids_only=true for discovery phase",
                ],
                repair_strategy=RepairStrategy.FIELD_RELAXATION,
            )
        
        # Strategy 3: Scope reduction (brief -> standard -> detailed)
        if "scope" in original_params or "variant" in original_params or "mode" in original_params:
            current_scope = original_params.get("scope") or original_params.get("variant") or original_params.get("mode", "detailed")
            if current_scope in ["detailed", "standard"]:
                modified = original_params.copy()
                if "scope" in modified:
                    modified["scope"] = "structure"
                elif "variant" in modified:
                    modified["variant"] = "brief"
                elif "mode" in modified:
                    modified["mode"] = "brief"
                
                repair_record["strategy"] = RepairStrategy.SCOPE_REDUCTION
                repair_record["modified_params"] = modified
                self.repair_history.append(repair_record)
                return RepairResult(
                    success=True,
                    modified_params=modified,
                    repair_strategy=RepairStrategy.SCOPE_REDUCTION,
                    suggestions=["Reduced scope to minimal mode, retrying"],
                )
        
        # Strategy 4: Token budget reduction
        if "token" in error_reason or "too large" in error_reason or "size" in error_reason:
            modified = original_params.copy()
            if "max_summary_length" not in modified:
                modified["max_summary_length"] = 100
            elif modified.get("max_summary_length", 200) > 50:
                modified["max_summary_length"] = max(50, modified["max_summary_length"] // 2)
            
            repair_record["strategy"] = RepairStrategy.TOKEN_BUDGET_REDUCTION
            repair_record["modified_params"] = modified
            self.repair_history.append(repair_record)
            return RepairResult(
                success=True,
                modified_params=modified,
                repair_strategy=RepairStrategy.TOKEN_BUDGET_REDUCTION,
                suggestions=["Reduced token budget, retrying"],
            )
        
        # No specific repair strategy found
        repair_record["strategy"] = None
        self.repair_history.append(repair_record)
        return RepairResult(
            success=False,
            suggestions=[
                "Review error details and adjust parameters",
                "Try using minimal context modes (brief, ids_only)",
                "Check if genome is loaded and valid",
            ],
        )
    
    def get_repair_suggestions(self, error: Dict[str, Any]) -> List[str]:
        """
        Get repair suggestions for an error.
        
        Args:
            error: Error dictionary
            
        Returns:
            List of repair suggestions
        """
        result = self.attempt_repair(error, {}, attempt=1)
        return result.suggestions


@dataclass
class ToolContract:
    """Contract definition for a specific tool."""
    tool_name: str
    requires_genome: bool
    required_params: List[str] = None
    preferred_params: List[str] = None
    optional_params: List[str] = None
    compliance_weights: Dict[str, float] = None
    repair_strategies: List[RepairStrategy] = None
    requires_impact_check: bool = False
    requires_validation: bool = False
    
    def __post_init__(self):
        if self.required_params is None:
            self.required_params = []
        if self.preferred_params is None:
            self.preferred_params = []
        if self.optional_params is None:
            self.optional_params = []
        if self.compliance_weights is None:
            self.compliance_weights = {}
        if self.repair_strategies is None:
            self.repair_strategies = []


class AgentContract:
    """Enforces RepoGenome agent contract rules."""

    def __init__(
        self,
        enable_repair_loops: bool = True,
        max_repair_attempts: int = 2,
        contract_score_threshold: float = 0.6,
        enable_context_lock: bool = True,
        auto_repair_simple_cases: bool = True,
    ):
        """
        Initialize contract enforcement.
        
        Args:
            enable_repair_loops: Enable repair loops
            max_repair_attempts: Maximum repair attempts
            contract_score_threshold: Minimum compliance score (0.0-1.0)
            enable_context_lock: Enable sticky context lock
            auto_repair_simple_cases: Auto-repair simple cases
        """
        self.genome_loaded = False
        self.citations: List[str] = []
        self.edits_made = False
        self.impact_checked = False
        self.last_validation: Optional[Dict[str, Any]] = None
        
        # New enforcement features
        self.enable_repair_loops = enable_repair_loops
        self.contract_score_threshold = contract_score_threshold
        self.enable_context_lock = enable_context_lock
        self.context_lock = ContextLock() if enable_context_lock else None
        self.repair_handler = ContractRepair(
            max_attempts=max_repair_attempts,
            auto_repair=auto_repair_simple_cases,
        )
        self.dependencies: List[ContextDependency] = []
        
        # Default contract compliance
        self.default_compliance = ContractCompliance(
            required=["summary"],
            preferred=["flows", "symbols"],
            optional=["history", "metrics"],
        )
        
        # Tool contract definitions
        self._tool_contracts: Dict[str, ToolContract] = {}
        self._initialize_tool_contracts()

    def check_genome_loaded(self) -> bool:
        """
        Check if genome has been loaded.

        Returns:
            True if genome was loaded
        """
        return self.genome_loaded

    def mark_genome_loaded(self):
        """Mark that genome has been loaded."""
        self.genome_loaded = True
        if self.context_lock:
            self.context_lock.lock(reason="genome_loaded")

    def add_citation(self, node_id: str, reason: str = ""):
        """
        Add a citation for RepoGenome usage.

        Args:
            node_id: Node ID being cited
            reason: Reason for citation
        """
        citation = f"{node_id}"
        if reason:
            citation += f": {reason}"
        self.citations.append(citation)

    def get_citations(self) -> List[str]:
        """
        Get all citations.

        Returns:
            List of citation strings
        """
        return self.citations.copy()

    def mark_edit(self):
        """Mark that an edit has been made."""
        self.edits_made = True

    def check_impact_before_edit(self) -> bool:
        """
        Check if impact was analyzed before edit.

        Returns:
            True if impact was checked
        """
        return self.impact_checked

    def mark_impact_checked(self):
        """Mark that impact was checked."""
        self.impact_checked = True

    def validate_before_action(self, action: str) -> Dict[str, Any]:
        """
        Validate contract before allowing action.

        Args:
            action: Action being attempted

        Returns:
            Validation result with allowed flag
        """
        violations = []

        # Rule 1: Genome must be loaded
        if not self.genome_loaded and action not in ["scan", "validate"]:
            violations.append(
                "Genome not loaded. Load repogenome://current before acting."
            )

        # Rule 2: Impact must be checked before edits
        if self.edits_made and not self.impact_checked:
            violations.append(
                "Impact not checked. Use repogenome.impact before edits."
            )

        # Rule 3: Validation must pass
        if self.last_validation and not self.last_validation.get("valid"):
            violations.append(
                f"Validation failed: {self.last_validation.get('error')}. "
                "Fix issues before proceeding."
            )

        if violations:
            return {
                "allowed": False,
                "violations": violations,
                "action": "Fix contract violations before proceeding",
            }

        return {"allowed": True}

    def update_validation_result(self, result: Dict[str, Any]):
        """
        Update last validation result.

        Args:
            result: Validation result from repogenome.validate
        """
        self.last_validation = result

    def reset_edit_state(self):
        """Reset edit tracking (called after successful update)."""
        self.edits_made = False
        self.impact_checked = False

    def get_contract_status(self) -> Dict[str, Any]:
        """
        Get current contract status.

        Returns:
            Status dict
        """
        status = {
            "genome_loaded": self.genome_loaded,
            "citations_count": len(self.citations),
            "edits_made": self.edits_made,
            "impact_checked": self.impact_checked,
            "validation_passed": self.last_validation.get("valid")
            if self.last_validation
            else None,
            "citations": self.citations[-10:],  # Last 10 citations
        }
        
        # Add new enforcement features
        if self.context_lock:
            status["context_locked"] = self.context_lock.is_locked()
            status["context_lock_info"] = self.context_lock.get_lock_info()
        
        status["repair_loops_enabled"] = self.enable_repair_loops
        status["contract_score_threshold"] = self.contract_score_threshold
        status["dependencies_count"] = len(self.dependencies)
        status["repair_attempts"] = len(self.repair_handler.repair_history)
        
        return status

    def check_compliance(
        self,
        available_fields: Set[str],
        compliance: Optional[ContractCompliance] = None,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Check contract compliance with graded scoring.
        
        Args:
            available_fields: Set of available field names
            compliance: Optional compliance definition (uses default if None)
            
        Returns:
            Tuple of (passed, score, details)
        """
        comp = compliance or self.default_compliance
        score, details = comp.score(available_fields)
        passed = score >= self.contract_score_threshold
        return passed, score, details
    
    def add_dependency(self, dependency: ContextDependency):
        """
        Add a context dependency.
        
        Args:
            dependency: Context dependency to add
        """
        self.dependencies.append(dependency)
    
    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Check if all dependencies are satisfied.
        
        Returns:
            Tuple of (all_satisfied, missing_deps)
        """
        missing = []
        for dep in self.dependencies:
            # Check if context is loaded (basic check)
            if not self.genome_loaded:
                missing.append(f"Context not loaded: {dep.context}")
                continue
            
            # Check required fields (would need genome access for full check)
            # For now, just check if genome is loaded
            pass
        
        return len(missing) == 0, missing
    
    def is_context_locked(self) -> bool:
        """
        Check if context is locked.
        
        Returns:
            True if context is locked
        """
        if not self.enable_context_lock or not self.context_lock:
            return False
        return self.context_lock.is_locked()
    
    def reset_context_lock(self):
        """Reset context lock (explicit unlock)."""
        if self.context_lock:
            self.context_lock.unlock()
    
    def attempt_repair(
        self,
        error: Dict[str, Any],
        original_params: Dict[str, Any],
        attempt: int = 1,
        tool_name: Optional[str] = None,
    ) -> RepairResult:
        """
        Attempt to repair a contract violation.
        
        Args:
            error: Error dictionary
            original_params: Original parameters
            attempt: Current attempt number
            tool_name: Optional tool name for tool-specific repairs
            
        Returns:
            RepairResult
        """
        if not self.enable_repair_loops:
            return RepairResult(
                success=False,
                suggestions=["Repair loops disabled. Fix contract violation manually."],
            )
        
        # Get tool-specific repair strategies if tool name provided
        tool_contract = None
        if tool_name:
            tool_contract = self.get_tool_contract(tool_name)
        
        # Attempt general repair
        repair_result = self.repair_handler.attempt_repair(error, original_params, attempt)
        
        # Enhance with tool-specific strategies if available
        if tool_contract and tool_contract.repair_strategies:
            tool_suggestions = []
            for strategy in tool_contract.repair_strategies:
                if strategy == RepairStrategy.FIELD_RELAXATION and "fields" in original_params:
                    tool_suggestions.append("Use minimal fields: ['id', 'type', 'file'] or ids_only=true")
                elif strategy == RepairStrategy.SCOPE_REDUCTION:
                    if "variant" in original_params:
                        tool_suggestions.append("Use variant='brief' instead of 'detailed'")
                    elif "mode" in original_params:
                        tool_suggestions.append("Use mode='brief' instead of 'detailed'")
                elif strategy == RepairStrategy.TOKEN_BUDGET_REDUCTION:
                    if "max_summary_length" in original_params:
                        tool_suggestions.append("Reduce max_summary_length to 100 or less")
                    elif "limit" in original_params:
                        tool_suggestions.append("Reduce limit parameter")
                elif strategy == RepairStrategy.CONTEXT_EXPANSION:
                    tool_suggestions.append("Refine goal or expand scope constraints")
                elif strategy == RepairStrategy.AUTO_SCAN_IF_MISSING:
                    tool_suggestions.append("Run repogenome.scan to generate genome")
            
            # Combine suggestions
            repair_result.suggestions = tool_suggestions + repair_result.suggestions
        
        return repair_result
    
    def get_repair_suggestions(self, error: Dict[str, Any]) -> List[str]:
        """
        Get repair suggestions for an error.
        
        Args:
            error: Error dictionary
            
        Returns:
            List of repair suggestions
        """
        return self.repair_handler.get_repair_suggestions(error)
    
    def _initialize_tool_contracts(self):
        """Initialize contract definitions for all MCP tools."""
        # Genome Management Tools (can work without genome)
        self._tool_contracts["repogenome.scan"] = ToolContract(
            tool_name="repogenome.scan",
            requires_genome=False,
            required_params=[],
            preferred_params=["scope", "incremental"],
            optional_params=[],
            repair_strategies=[RepairStrategy.AUTO_SCAN_IF_MISSING],
        )
        
        self._tool_contracts["repogenome.validate"] = ToolContract(
            tool_name="repogenome.validate",
            requires_genome=False,
            required_params=[],
            preferred_params=[],
            optional_params=[],
            repair_strategies=[RepairStrategy.AUTO_SCAN_IF_MISSING],
        )
        
        # Query Tools (require genome, benefit from field selection)
        self._tool_contracts["repogenome.query"] = ToolContract(
            tool_name="repogenome.query",
            requires_genome=True,
            required_params=["query"],
            preferred_params=["fields", "ids_only", "max_summary_length"],
            optional_params=["format", "page", "page_size", "filters"],
            repair_strategies=[
                RepairStrategy.FIELD_RELAXATION,
                RepairStrategy.TOKEN_BUDGET_REDUCTION,
            ],
            compliance_weights={"fields": 0.3, "ids_only": 0.2, "max_summary_length": 0.2},
        )
        
        self._tool_contracts["repogenome.search"] = ToolContract(
            tool_name="repogenome.search",
            requires_genome=True,
            required_params=[],
            preferred_params=["query", "limit"],
            optional_params=["node_type", "language", "file_pattern"],
            repair_strategies=[RepairStrategy.TOKEN_BUDGET_REDUCTION],
            compliance_weights={"limit": 0.3},
        )
        
        self._tool_contracts["repogenome.filter"] = ToolContract(
            tool_name="repogenome.filter",
            requires_genome=True,
            required_params=["filters"],
            preferred_params=["limit", "fields"],
            optional_params=[],
            repair_strategies=[
                RepairStrategy.FIELD_RELAXATION,
                RepairStrategy.TOKEN_BUDGET_REDUCTION,
            ],
            compliance_weights={"limit": 0.3, "fields": 0.2},
        )
        
        self._tool_contracts["repogenome.get_node"] = ToolContract(
            tool_name="repogenome.get_node",
            requires_genome=True,
            required_params=["node_id"],
            preferred_params=["fields", "max_depth"],
            optional_params=["include_edges", "edge_types"],
            repair_strategies=[
                RepairStrategy.FIELD_RELAXATION,
                RepairStrategy.SCOPE_REDUCTION,
            ],
            compliance_weights={"fields": 0.3, "max_depth": 0.2},
        )
        
        self._tool_contracts["repogenome.dependencies"] = ToolContract(
            tool_name="repogenome.dependencies",
            requires_genome=True,
            required_params=["node_id"],
            preferred_params=["depth", "direction"],
            optional_params=[],
            repair_strategies=[RepairStrategy.SCOPE_REDUCTION],
            compliance_weights={"depth": 0.4},
        )
        
        self._tool_contracts["repogenome.find_path"] = ToolContract(
            tool_name="repogenome.find_path",
            requires_genome=True,
            required_params=["from_node", "to_node"],
            preferred_params=["max_depth", "edge_types"],
            optional_params=[],
            repair_strategies=[RepairStrategy.SCOPE_REDUCTION],
            compliance_weights={"max_depth": 0.4},
        )
        
        self._tool_contracts["repogenome.compare"] = ToolContract(
            tool_name="repogenome.compare",
            requires_genome=True,
            required_params=["node_id1"],
            preferred_params=["node_id2", "compare_with_previous"],
            optional_params=[],
            repair_strategies=[RepairStrategy.FIELD_RELAXATION],
        )
        
        # Context Tools (require genome, have token budgets)
        self._tool_contracts["repogenome.current"] = ToolContract(
            tool_name="repogenome.current",
            requires_genome=True,
            required_params=[],
            preferred_params=["fields", "variant"],
            optional_params=[],
            repair_strategies=[
                RepairStrategy.FIELD_RELAXATION,
                RepairStrategy.SCOPE_REDUCTION,
                RepairStrategy.TOKEN_BUDGET_REDUCTION,
            ],
            compliance_weights={"fields": 0.4, "variant": 0.3},
        )
        
        self._tool_contracts["repogenome.summary"] = ToolContract(
            tool_name="repogenome.summary",
            requires_genome=True,
            required_params=[],
            preferred_params=["fields", "mode"],
            optional_params=[],
            repair_strategies=[
                RepairStrategy.FIELD_RELAXATION,
                RepairStrategy.SCOPE_REDUCTION,
            ],
            compliance_weights={"fields": 0.4, "mode": 0.3},
        )
        
        self._tool_contracts["repogenome.build_context"] = ToolContract(
            tool_name="repogenome.build_context",
            requires_genome=True,
            required_params=["goal"],
            preferred_params=["scope", "constraints"],
            optional_params=[],
            repair_strategies=[
                RepairStrategy.CONTEXT_EXPANSION,
                RepairStrategy.TOKEN_BUDGET_REDUCTION,
            ],
            compliance_weights={"goal": 0.5, "constraints": 0.2},
        )
        
        self._tool_contracts["repogenome.explain_context"] = ToolContract(
            tool_name="repogenome.explain_context",
            requires_genome=True,
            required_params=["goal"],
            preferred_params=["context"],
            optional_params=[],
            repair_strategies=[RepairStrategy.CONTEXT_EXPANSION],
        )
        
        self._tool_contracts["repogenome.get_context_skeleton"] = ToolContract(
            tool_name="repogenome.get_context_skeleton",
            requires_genome=True,
            required_params=["goal"],
            preferred_params=[],
            optional_params=[],
            repair_strategies=[RepairStrategy.CONTEXT_EXPANSION],
        )
        
        self._tool_contracts["repogenome.set_context_session"] = ToolContract(
            tool_name="repogenome.set_context_session",
            requires_genome=True,
            required_params=["session_id", "goal"],
            preferred_params=["context"],
            optional_params=[],
            repair_strategies=[RepairStrategy.CONTEXT_EXPANSION],
        )
        
        self._tool_contracts["repogenome.get_context_feedback"] = ToolContract(
            tool_name="repogenome.get_context_feedback",
            requires_genome=True,
            required_params=["context_id"],
            preferred_params=[],
            optional_params=[],
            repair_strategies=[],
        )
        
        # Analysis Tools (require genome)
        self._tool_contracts["repogenome.stats"] = ToolContract(
            tool_name="repogenome.stats",
            requires_genome=True,
            required_params=[],
            preferred_params=[],
            optional_params=[],
            repair_strategies=[RepairStrategy.AUTO_SCAN_IF_MISSING],
        )
        
        self._tool_contracts["repogenome.diff"] = ToolContract(
            tool_name="repogenome.diff",
            requires_genome=True,
            required_params=[],
            preferred_params=[],
            optional_params=[],
            repair_strategies=[RepairStrategy.AUTO_SCAN_IF_MISSING],
        )
        
        self._tool_contracts["repogenome.impact"] = ToolContract(
            tool_name="repogenome.impact",
            requires_genome=True,
            required_params=["affected_nodes"],
            preferred_params=["operation"],
            optional_params=[],
            repair_strategies=[],
        )
        
        # Modification Tools (require genome + impact check)
        self._tool_contracts["repogenome.update"] = ToolContract(
            tool_name="repogenome.update",
            requires_genome=True,
            required_params=[],
            preferred_params=["reason"],
            optional_params=["added_nodes", "removed_nodes", "updated_edges"],
            requires_impact_check=True,
            repair_strategies=[],
        )
        
        # Export Tools (require genome)
        self._tool_contracts["repogenome.export"] = ToolContract(
            tool_name="repogenome.export",
            requires_genome=True,
            required_params=[],
            preferred_params=["format"],
            optional_params=["output_path"],
            repair_strategies=[RepairStrategy.AUTO_SCAN_IF_MISSING],
        )
        
        # Batch Tools (require genome, have size limits)
        self._tool_contracts["repogenome.batch"] = ToolContract(
            tool_name="repogenome.batch",
            requires_genome=True,
            required_params=["operation", "node_ids"],
            preferred_params=["fields", "include_edges", "direction", "depth"],
            optional_params=[],
            repair_strategies=[
                RepairStrategy.FIELD_RELAXATION,
                RepairStrategy.TOKEN_BUDGET_REDUCTION,
            ],
            compliance_weights={"node_ids": 0.4},  # Size matters
        )
    
    def get_tool_contract(self, tool_name: str) -> Optional[ToolContract]:
        """
        Get contract definition for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            ToolContract or None if not found
        """
        return self._tool_contracts.get(tool_name)
    
    def check_tool_compliance(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Check compliance for a specific tool call.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            
        Returns:
            Tuple of (passed, score, details)
        """
        contract = self.get_tool_contract(tool_name)
        if not contract:
            # Unknown tool - allow by default but warn
            return True, 1.0, {"warning": "Unknown tool, no contract defined"}
        
        details = {
            "tool": tool_name,
            "required_params": {},
            "preferred_params": {},
            "optional_params": {},
        }
        
        # Check required parameters
        required_score = 1.0
        for param in contract.required_params:
            present = param in args and args[param] is not None
            details["required_params"][param] = present
            if not present:
                required_score = 0.0
        
        if required_score == 0.0:
            return False, 0.0, details
        
        # Score preferred parameters
        preferred_score = 0.0
        if contract.preferred_params:
            present_count = sum(
                1 for p in contract.preferred_params
                if p in args and args[p] is not None
            )
            weight = contract.compliance_weights.get("preferred", 0.65)
            preferred_score = (present_count / len(contract.preferred_params)) * weight
            
            for param in contract.preferred_params:
                details["preferred_params"][param] = (
                    param in args and args[param] is not None
                )
        
        # Score optional parameters (bonus)
        optional_score = 0.0
        if contract.optional_params:
            present_count = sum(
                1 for p in contract.optional_params
                if p in args and args[p] is not None
            )
            weight = contract.compliance_weights.get("optional", 0.2)
            optional_score = (present_count / len(contract.optional_params)) * weight
            
            for param in contract.optional_params:
                details["optional_params"][param] = (
                    param in args and args[param] is not None
                )
        
        # Apply tool-specific weights
        weighted_score = required_score
        for param, weight in contract.compliance_weights.items():
            if param in args and args[param] is not None:
                weighted_score += weight
        
        # Add preferred and optional scores
        total_score = min(1.0, weighted_score + preferred_score + optional_score)
        
        details["score"] = total_score
        details["breakdown"] = {
            "required": required_score,
            "preferred": preferred_score,
            "optional": optional_score,
            "weighted": weighted_score,
        }
        
        passed = total_score >= self.contract_score_threshold
        return passed, total_score, details
    
    def enforce_contract_middleware(
        self, tool_name: str, args: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Middleware to enforce contract before tool execution.
        Enhanced with tool-specific contracts, compliance scoring, and repair loops.

        Args:
            tool_name: Name of tool being called
            args: Tool arguments

        Returns:
            Error dict if contract violated (repairable), None if allowed
        """
        # Get tool contract
        contract = self.get_tool_contract(tool_name)
        
        # If no contract, allow (unknown tool)
        if not contract:
            return None
        
        # Check context lock - if locked, be more lenient
        context_locked = self.is_context_locked()
        
        # Check if genome required and loaded
        if contract.requires_genome and not self.genome_loaded:
            repair_result = self.attempt_repair(
                {"error": "Contract violation: Genome not loaded", "reason": "genome_not_loaded"},
                args,
                tool_name=tool_name,
            )
            return {
                "status": "repairable_error",
                "error": f"Contract violation: {tool_name} requires genome to be loaded",
                "reason": "genome_not_loaded",
                "action": "Load repogenome://current resource first or run repogenome.scan",
                "suggested_fix": "repogenome.scan",
                "repair_strategies": repair_result.suggestions,
                "retry_allowed": True,
                "next_action_constraint": "repogenome_mcp",
                "required_tool": "repogenome.scan",
                "blocked_tools": ["read_file", "grep", "codebase_search"],
            }
        
        # Check impact requirement
        if contract.requires_impact_check and not self.impact_checked:
            repair_result = self.attempt_repair(
                {"error": "Contract violation: Impact not checked", "reason": "impact_not_checked"},
                args,
                tool_name=tool_name,
            )
            return {
                "status": "repairable_error",
                "error": f"Contract violation: {tool_name} requires impact check",
                "reason": "impact_not_checked",
                "action": "Call repogenome.impact before this operation",
                "suggested_fix": "repogenome.impact",
                "repair_strategies": repair_result.suggestions,
                "retry_allowed": True,
                "next_action_constraint": "repogenome_mcp",
                "required_tool": "repogenome.impact",
            }
        
        # Check validation requirement
        if contract.requires_validation:
            if self.last_validation and not self.last_validation.get("valid"):
                if context_locked:
                    # If context is locked, allow with warning
                    return None
                repair_result = self.attempt_repair(
                    {"error": "Contract violation: Validation failed", "reason": "validation_failed"},
                    args,
                    tool_name=tool_name,
                )
                return {
                    "status": "repairable_error",
                    "error": f"Contract violation: {tool_name} requires valid genome",
                    "reason": "validation_failed",
                    "details": self.last_validation.get("error"),
                    "action": "Run repogenome.validate and fix issues",
                    "suggested_fix": "repogenome.validate",
                    "repair_strategies": repair_result.suggestions,
                    "retry_allowed": True,
                }
        
        # Check tool-specific compliance
        passed, score, details = self.check_tool_compliance(tool_name, args)
        
        if not passed:
            # Compliance score too low - attempt repair
            repair_result = self.attempt_repair(
                {
                    "error": f"Contract violation: Low compliance score ({score:.2f})",
                    "reason": "compliance_failed",
                    "tool": tool_name,
                },
                args,
                tool_name=tool_name,
            )
            
            # Get tool-specific repair strategies
            tool_repair_strategies = []
            if contract.repair_strategies:
                for strategy in contract.repair_strategies:
                    if strategy == RepairStrategy.FIELD_RELAXATION:
                        tool_repair_strategies.append("Reduce field requirements or use ids_only=true")
                    elif strategy == RepairStrategy.SCOPE_REDUCTION:
                        tool_repair_strategies.append("Use brief/standard mode instead of detailed")
                    elif strategy == RepairStrategy.TOKEN_BUDGET_REDUCTION:
                        tool_repair_strategies.append("Reduce max_summary_length or limit parameter")
                    elif strategy == RepairStrategy.CONTEXT_EXPANSION:
                        tool_repair_strategies.append("Refine goal or expand scope")
                    elif strategy == RepairStrategy.AUTO_SCAN_IF_MISSING:
                        tool_repair_strategies.append("Run repogenome.scan to generate genome")
            
            # Combine with general repair suggestions
            all_suggestions = tool_repair_strategies + repair_result.suggestions
            
            return {
                "status": "repairable_error",
                "error": f"Contract violation: Low compliance score for {tool_name}",
                "reason": "compliance_failed",
                "contract_score": score,
                "details": details,
                "action": "Improve parameter completeness or use repair strategies",
                "repair_strategies": all_suggestions,
                "retry_allowed": True,
                "next_action_constraint": "repogenome_mcp",
            }
        
        # All checks passed
        return None

