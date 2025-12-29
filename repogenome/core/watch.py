"""
Watch mode for auto-regenerating RepoGenome on file changes.
"""

import time
from pathlib import Path
from typing import Callable, Optional, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class GenomeWatcher(FileSystemEventHandler):
    """File system watcher for RepoGenome auto-regeneration."""

    def __init__(
        self,
        repo_path: Path,
        callback: Callable[[Set[str]], None],
        ignore_patterns: Optional[Set[str]] = None,
        debounce_seconds: float = 2.0,
    ):
        """
        Initialize watcher.

        Args:
            repo_path: Repository root path
            callback: Function to call when files change (receives set of changed file paths)
            ignore_patterns: Patterns to ignore (e.g., {".git", "__pycache__"})
            debounce_seconds: Seconds to wait before triggering callback (debounce)
        """
        self.repo_path = Path(repo_path).resolve()
        self.callback = callback
        self.ignore_patterns = ignore_patterns or {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            ".eggs",
            "*.egg-info",
            "repogenome.json",
            "repogenome.json.gz",
        }
        self.debounce_seconds = debounce_seconds
        self.changed_files: Set[str] = set()
        self.last_event_time = 0.0
        self.debounce_timer: Optional[float] = None

    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True
        return False

    def on_any_event(self, event: FileSystemEvent):
        """Handle any file system event."""
        if event.is_directory:
            return

        src_path = Path(event.src_path)
        
        # Ignore if path should be ignored
        if self.should_ignore(src_path):
            return

        # Get relative path
        try:
            rel_path = src_path.relative_to(self.repo_path)
        except ValueError:
            # Path is outside repo
            return

        # Track changed file
        self.changed_files.add(str(rel_path))
        self.last_event_time = time.time()

        # Schedule debounced callback
        if self.debounce_timer is None:
            self._schedule_callback()

    def _schedule_callback(self):
        """Schedule debounced callback."""
        def trigger():
            time.sleep(self.debounce_seconds)
            # Check if enough time has passed since last event
            if time.time() - self.last_event_time >= self.debounce_seconds:
                if self.changed_files:
                    files_to_process = self.changed_files.copy()
                    self.changed_files.clear()
                    self.debounce_timer = None
                    self.callback(files_to_process)

        import threading
        thread = threading.Thread(target=trigger, daemon=True)
        thread.start()
        self.debounce_timer = time.time()


def watch_and_regenerate(
    repo_path: Path,
    output_path: Path,
    generator_factory: Callable[[], any],
    debounce_seconds: float = 2.0,
    ignore_patterns: Optional[Set[str]] = None,
) -> None:
    """
    Watch repository and auto-regenerate genome on changes.

    Args:
        repo_path: Repository root path
        output_path: Output genome file path
        generator_factory: Function that returns a RepoGenomeGenerator instance
        debounce_seconds: Seconds to wait before regenerating (debounce)
        ignore_patterns: Additional patterns to ignore
    """
    if not WATCHDOG_AVAILABLE:
        raise ImportError(
            "watchdog package is required for watch mode. Install with: pip install watchdog"
        )

    def on_changes(changed_files: Set[str]):
        """Handle file changes."""
        print(f"Detected changes in {len(changed_files)} files. Regenerating genome...")
        try:
            generator = generator_factory()
            genome = generator.generate(incremental=True)
            genome.save(str(output_path))
            print(f"Genome regenerated: {output_path}")
        except Exception as e:
            print(f"Error regenerating genome: {e}")

    watcher = GenomeWatcher(
        repo_path,
        on_changes,
        ignore_patterns=ignore_patterns,
        debounce_seconds=debounce_seconds,
    )

    observer = Observer()
    observer.schedule(watcher, str(repo_path), recursive=True)
    observer.start()

    print(f"Watching {repo_path} for changes...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching.")

    observer.join()

