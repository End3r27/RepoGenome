"""Error formatting utilities for context reduction."""

from typing import Any, Dict, Optional, List
from enum import Enum


class ErrorVerbosity:
    """Error verbosity levels."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    VERBOSE = "verbose"


class ErrorStatus(str, Enum):
    """Error status types."""
    REPAIRABLE_ERROR = "repairable_error"
    FATAL_ERROR = "fatal_error"
    ERROR = "error"  # Legacy, prefer repairable_error


class ErrorFormatter:
    """Formats errors based on verbosity level."""

    def __init__(self, verbosity: str = ErrorVerbosity.STANDARD):
        """
        Initialize error formatter.

        Args:
            verbosity: Error verbosity level (minimal, standard, verbose)
        """
        self.verbosity = verbosity

    def format_error(
        self,
        error: str,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> Dict[str, Any]:
        """
        Format an error based on verbosity level.

        Args:
            error: Error message
            action: Suggested action to resolve error
            details: Additional error details
            exception: Exception object (for verbose mode)

        Returns:
            Formatted error dictionary
        """
        if self.verbosity == ErrorVerbosity.MINIMAL:
            return {"error": error}

        if self.verbosity == ErrorVerbosity.VERBOSE:
            result: Dict[str, Any] = {
                "error": error,
            }
            if action:
                result["action"] = action
            if details:
                result["details"] = details
            if exception:
                import traceback

                result["exception"] = {
                    "type": type(exception).__name__,
                    "message": str(exception),
                    "traceback": traceback.format_exc(),
                }
            return result

        # Standard (default)
        result = {"error": error}
        if action:
            result["action"] = action
        if details and self.verbosity == ErrorVerbosity.VERBOSE:
            result["details"] = details

        return result

    @staticmethod
    def format_error_simple(
        error: str,
        action: Optional[str] = None,
        verbosity: str = ErrorVerbosity.STANDARD,
    ) -> Dict[str, Any]:
        """
        Format a simple error (convenience method).

        Args:
            error: Error message
            action: Suggested action
            verbosity: Error verbosity level

        Returns:
            Formatted error dictionary
        """
        formatter = ErrorFormatter(verbosity)
        return formatter.format_error(error, action)


def format_error(
    error: str,
    action: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    exception: Optional[Exception] = None,
    verbosity: str = ErrorVerbosity.STANDARD,
) -> Dict[str, Any]:
    """
    Format an error (module-level convenience function).

    Args:
        error: Error message
        action: Suggested action
        details: Additional details
        exception: Exception object
        verbosity: Error verbosity level

    Returns:
        Formatted error dictionary
    """
    formatter = ErrorFormatter(verbosity)
    return formatter.format_error(error, action, details, exception)


def handle_analysis_error(
    exception: Exception,
    file_path: Optional[str] = None,
    log_error: bool = True,
) -> Dict[str, Any]:
    """
    Handle an analysis error by formatting it and optionally logging.

    Args:
        exception: The exception that occurred
        file_path: Optional path to the file being analyzed (can be passed positionally or as keyword)
        log_error: Whether to log the error (default: True)

    Returns:
        Error information dictionary
    """
    import logging

    error_message = str(exception)
    error_info: Dict[str, Any] = {
        "error": error_message,
        "type": type(exception).__name__,
    }

    if file_path:
        error_info["file_path"] = file_path

    if log_error:
        logger = logging.getLogger(__name__)
        log_msg = f"Analysis error: {error_message}"
        if file_path:
            log_msg += f" (file: {file_path})"
        logger.warning(log_msg)

    return error_info


class RepairableError:
    """Repairable error formatting with repair guidance."""
    
    @staticmethod
    def create(
        error: str,
        reason: str,
        action: Optional[str] = None,
        suggested_fix: Optional[str] = None,
        repair_strategies: Optional[List[str]] = None,
        retry_allowed: bool = True,
        contract_score: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        next_action_constraint: Optional[str] = None,
        required_tool: Optional[str] = None,
        blocked_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a repairable error response.
        
        Args:
            error: Error message
            reason: Error reason/category
            action: Suggested action
            suggested_fix: Specific fix to try
            repair_strategies: List of repair strategies
            retry_allowed: Whether retry is allowed
            contract_score: Compliance score if applicable
            details: Additional error details
            next_action_constraint: Constraint on next action
            required_tool: Required tool to use next
            blocked_tools: Tools that should be blocked
            
        Returns:
            Repairable error dictionary
        """
        result: Dict[str, Any] = {
            "status": ErrorStatus.REPAIRABLE_ERROR.value,
            "error": error,
            "reason": reason,
            "retry_allowed": retry_allowed,
        }
        
        if action:
            result["action"] = action
        if suggested_fix:
            result["suggested_fix"] = suggested_fix
        if repair_strategies:
            result["repair_strategies"] = repair_strategies
        if contract_score is not None:
            result["contract_score"] = contract_score
        if details:
            result["details"] = details
        if next_action_constraint:
            result["next_action_constraint"] = next_action_constraint
        if required_tool:
            result["required_tool"] = required_tool
        if blocked_tools:
            result["blocked_tools"] = blocked_tools
        
        return result
    
    @staticmethod
    def create_fatal(
        error: str,
        reason: str,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a fatal (non-repairable) error response.
        
        Args:
            error: Error message
            reason: Error reason
            action: Suggested action
            details: Additional details
            
        Returns:
            Fatal error dictionary
        """
        result: Dict[str, Any] = {
            "status": ErrorStatus.FATAL_ERROR.value,
            "error": error,
            "reason": reason,
            "retry_allowed": False,
        }
        
        if action:
            result["action"] = action
        if details:
            result["details"] = details
        
        return result
    
    @staticmethod
    def get_repair_guidance(error: Dict[str, Any]) -> List[str]:
        """
        Extract repair guidance from an error.
        
        Args:
            error: Error dictionary
            
        Returns:
            List of repair guidance strings
        """
        guidance = []
        
        if error.get("status") == ErrorStatus.REPAIRABLE_ERROR.value:
            if error.get("suggested_fix"):
                guidance.append(f"Try: {error['suggested_fix']}")
            
            if error.get("repair_strategies"):
                guidance.extend(error["repair_strategies"])
            
            if error.get("action"):
                guidance.append(f"Action: {error['action']}")
        
        return guidance if guidance else ["Review error details and adjust approach"]


def format_repairable_error(
    error: str,
    reason: str,
    action: Optional[str] = None,
    suggested_fix: Optional[str] = None,
    repair_strategies: Optional[List[str]] = None,
    retry_allowed: bool = True,
    contract_score: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
    next_action_constraint: Optional[str] = None,
    required_tool: Optional[str] = None,
    blocked_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Format a repairable error (convenience function).
    
    Args:
        error: Error message
        reason: Error reason
        action: Suggested action
        suggested_fix: Specific fix
        repair_strategies: Repair strategies
        retry_allowed: Whether retry allowed
        contract_score: Compliance score
        details: Additional details
        next_action_constraint: Next action constraint
        required_tool: Required tool
        blocked_tools: Blocked tools
        
    Returns:
        Repairable error dictionary
    """
    return RepairableError.create(
        error=error,
        reason=reason,
        action=action,
        suggested_fix=suggested_fix,
        repair_strategies=repair_strategies,
        retry_allowed=retry_allowed,
        contract_score=contract_score,
        details=details,
        next_action_constraint=next_action_constraint,
        required_tool=required_tool,
        blocked_tools=blocked_tools,
    )


def format_fatal_error(
    error: str,
    reason: str,
    action: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format a fatal error (convenience function).
    
    Args:
        error: Error message
        reason: Error reason
        action: Suggested action
        details: Additional details
        
    Returns:
        Fatal error dictionary
    """
    return RepairableError.create_fatal(
        error=error,
        reason=reason,
        action=action,
        details=details,
    )