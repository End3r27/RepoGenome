"""Error handling utilities for RepoGenome."""

from typing import Any, Dict, List, Optional


class RepoGenomeError(Exception):
    """Base exception for RepoGenome errors."""

    pass


class AnalysisError(RepoGenomeError):
    """Error during code analysis."""

    def __init__(self, message: str, file_path: Optional[str] = None, cause: Optional[Exception] = None):
        """
        Initialize analysis error.

        Args:
            message: Error message
            file_path: Optional file path where error occurred
            cause: Optional underlying exception
        """
        super().__init__(message)
        self.file_path = file_path
        self.cause = cause


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


def handle_analysis_error(error: Exception, file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle an analysis error gracefully.

    Args:
        error: Exception that occurred
        file_path: Optional file path

    Returns:
        Dictionary with error information
    """
    return {
        "error": str(error),
        "file": file_path,
        "type": type(error).__name__,
    }

