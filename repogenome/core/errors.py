"""Error handling utilities for RepoGenome."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RepoGenomeError(Exception):
    """Base exception for RepoGenome errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize RepoGenome error.

        Args:
            message: Error message
            context: Optional context dictionary with additional error information
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Return formatted error message with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class AnalysisError(RepoGenomeError):
    """Error during code analysis."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize analysis error.

        Args:
            message: Error message
            file_path: Optional file path where error occurred
            cause: Optional underlying exception
            context: Optional context dictionary with additional error information
        """
        error_context = context or {}
        if file_path:
            error_context["file_path"] = file_path
        if cause:
            error_context["cause_type"] = type(cause).__name__
            error_context["cause_message"] = str(cause)
        
        super().__init__(message, error_context)
        self.file_path = file_path
        self.cause = cause

    def get_recovery_suggestion(self) -> str:
        """
        Get suggestion for recovering from this error.

        Returns:
            Recovery suggestion string
        """
        if self.file_path:
            return f"Check file: {self.file_path}. Verify file encoding and syntax."
        if self.cause:
            cause_type = type(self.cause).__name__
            if "ImportError" in cause_type or "ModuleNotFoundError" in cause_type:
                return "Install missing dependencies or check import paths."
            if "SyntaxError" in cause_type or "ParseError" in cause_type:
                return "Check file syntax and fix parsing errors."
        return "Review error context and retry operation."


class ConfigError(RepoGenomeError):
    """Error in configuration."""

    pass


def collect_errors(func):
    """
    Decorator to collect errors instead of raising immediately.

    Usage:
        @collect_errors
        def analyze_file(file_path):
            # If errors occur, they're collected and returned
            pass
    """
    errors: List[AnalysisError] = []

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            errors.append(AnalysisError(str(e), cause=e))
            return None

    wrapper.errors = errors
    return wrapper


def handle_analysis_error(
    error: Exception,
    file_path: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    log_error: bool = True,
) -> Dict[str, Any]:
    """
    Handle an analysis error gracefully with context-aware messages.

    Args:
        error: Exception that occurred
        file_path: Optional file path
        context: Optional context dictionary
        log_error: Whether to log the error

    Returns:
        Dictionary with error information and recovery suggestions
    """
    error_info = {
        "error": str(error),
        "file": file_path,
        "type": type(error).__name__,
        "context": context or {},
    }

    # Add recovery suggestion based on error type
    error_type = type(error).__name__
    if "ImportError" in error_type or "ModuleNotFoundError" in error_type:
        error_info["recovery"] = "Install missing dependencies or check import paths."
    elif "SyntaxError" in error_type or "ParseError" in error_type:
        error_info["recovery"] = "Check file syntax and fix parsing errors."
    elif "PermissionError" in error_type:
        error_info["recovery"] = "Check file permissions and access rights."
    elif "FileNotFoundError" in error_type:
        error_info["recovery"] = "Verify file path exists and is accessible."
    else:
        error_info["recovery"] = "Review error context and retry operation."

    # Log error if requested
    if log_error:
        logger.error(
            f"Analysis error in {file_path or 'unknown file'}: {error}",
            exc_info=True,
            extra={"context": context},
        )

    return error_info


def create_error_recovery_strategy(error: Exception) -> Dict[str, Any]:
    """
    Create a recovery strategy for an error.

    Args:
        error: Exception that occurred

    Returns:
        Dictionary with recovery strategy
    """
    error_type = type(error).__name__
    strategy = {
        "error_type": error_type,
        "can_retry": False,
        "suggested_actions": [],
    }

    if "Network" in error_type or "Connection" in error_type:
        strategy["can_retry"] = True
        strategy["suggested_actions"] = [
            "Check network connectivity",
            "Verify service availability",
            "Retry after a delay",
        ]
    elif "Permission" in error_type:
        strategy["suggested_actions"] = [
            "Check file permissions",
            "Verify user has required access",
            "Run with appropriate privileges",
        ]
    elif "Syntax" in error_type or "Parse" in error_type:
        strategy["suggested_actions"] = [
            "Review file syntax",
            "Check for missing dependencies",
            "Validate file encoding",
        ]
    else:
        strategy["suggested_actions"] = [
            "Review error message",
            "Check error context",
            "Consult documentation",
        ]

    return strategy

