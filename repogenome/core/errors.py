"""Error formatting utilities for context reduction."""

from typing import Any, Dict, Optional


class ErrorVerbosity:
    """Error verbosity levels."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    VERBOSE = "verbose"


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