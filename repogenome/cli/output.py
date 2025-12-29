"""CLI output formatting utilities."""

import sys
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


def create_progress_bar() -> Progress:
    """Create a progress bar for long-running operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=Console(file=sys.stderr),
    )


def print_success(message: str, console: Optional[Console] = None) -> None:
    """Print a success message."""
    if console is None:
        console = Console()
    console.print(f"[green]OK[/green] {message}")


def print_error(message: str, console: Optional[Console] = None) -> None:
    """Print an error message."""
    if console is None:
        console = Console()
    console.print(f"[red]ERROR[/red] {message}")


def print_warning(message: str, console: Optional[Console] = None) -> None:
    """Print a warning message."""
    if console is None:
        console = Console()
    console.print(f"[yellow]WARNING[/yellow] {message}")


def print_info(message: str, console: Optional[Console] = None) -> None:
    """Print an info message."""
    if console is None:
        console = Console()
    console.print(f"[blue]INFO[/blue] {message}")


def format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

