"""Git utility functions for repository analysis."""

import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import git
except ImportError:
    git = None


def get_repo_hash(repo_path: Path, timeout: float = 5.0) -> Optional[str]:
    """
    Get the current git commit hash.

    Args:
        repo_path: Path to repository root
        timeout: Timeout in seconds for GitPython operations (default: 5.0)

    Returns:
        Commit hash or None if not a git repo
    """
    # On macOS, skip GitPython to avoid hanging issues with git cat-file
    # Also check for environment variable override
    use_gitpython = os.environ.get("REPOGENOME_USE_GITPYTHON", "").lower() == "true"
    if sys.platform == "darwin" and not use_gitpython:
        return _get_repo_hash_subprocess(repo_path)

    if git is None:
        return _get_repo_hash_subprocess(repo_path)

    # Try GitPython with timeout
    try:
        result = _get_repo_hash_gitpython_with_timeout(repo_path, timeout)
        if result is not None:
            return result
    except Exception:
        pass

    # Fallback to subprocess
    return _get_repo_hash_subprocess(repo_path)


def _get_repo_hash_gitpython_with_timeout(
    repo_path: Path, timeout: float
) -> Optional[str]:
    """
    Get repo hash using GitPython with a timeout mechanism.

    Args:
        repo_path: Path to repository root
        timeout: Timeout in seconds

    Returns:
        Commit hash or None if timeout/error occurs
    """
    result_container = {"value": None, "exception": None}

    def gitpython_operation():
        """Execute GitPython operation in a separate thread."""
        try:
            repo = git.Repo(repo_path)
            result_container["value"] = repo.head.commit.hexsha[:12]
        except Exception as e:
            result_container["exception"] = e

    thread = threading.Thread(target=gitpython_operation, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Operation timed out
        return None

    if result_container["exception"]:
        raise result_container["exception"]

    return result_container["value"]


def _get_repo_hash_subprocess(repo_path: Path) -> Optional[str]:
    """Fallback to subprocess for git operations."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:12]
    except Exception:
        return None


def get_changed_files(
    repo_path: Path, since: Optional[str] = None
) -> List[str]:
    """
    Get list of changed files since a reference point.

    Args:
        repo_path: Path to repository root
        since: Git reference (commit hash, branch, tag) or None for all changes

    Returns:
        List of relative file paths
    """
    try:
        if since:
            result = subprocess.run(
                ["git", "diff", "--name-only", since],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
        return [
            f.strip()
            for f in result.stdout.strip().split("\n")
            if f.strip()
        ]
    except Exception:
        return []


def get_file_history(
    repo_path: Path, file_path: str, limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get git history for a specific file.

    Args:
        repo_path: Path to repository root
        file_path: Relative path to file
        limit: Maximum number of commits to return

    Returns:
        List of commit dictionaries with keys: hash, date, message, changes
    """
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"-{limit}",
                "--pretty=format:%H|%ai|%s",
                "--numstat",
                file_path,
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        commits = []
        lines = result.stdout.strip().split("\n")
        i = 0
        while i < len(lines):
            if "|" in lines[i]:
                parts = lines[i].split("|", 2)
                if len(parts) >= 3:
                    commit_hash = parts[0]
                    date_str = parts[1]
                    message = parts[2]

                    # Parse numstat lines
                    additions = 0
                    deletions = 0
                    i += 1
                    while i < len(lines) and lines[i] and "\t" in lines[i]:
                        stats = lines[i].split("\t")
                        if len(stats) >= 2:
                            try:
                                additions += int(stats[0]) if stats[0] != "-" else 0
                                deletions += int(stats[1]) if stats[1] != "-" else 0
                            except ValueError:
                                pass
                        i += 1

                    commits.append(
                        {
                            "hash": commit_hash[:12],
                            "date": date_str,
                            "message": message,
                            "additions": additions,
                            "deletions": deletions,
                            "changes": additions + deletions,
                        }
                    )
                    continue
            i += 1

        return commits
    except Exception:
        return []


def calculate_churn_score(
    repo_path: Path, file_path: str, days: int = 365
) -> float:
    """
    Calculate churn score for a file (0.0 to 1.0).

    Higher score means more frequent changes.

    Args:
        repo_path: Path to repository root
        file_path: Relative path to file
        days: Time window for analysis

    Returns:
        Churn score between 0.0 and 1.0
    """
    history = get_file_history(repo_path, file_path, limit=1000)

    if not history:
        return 0.0

    # Count commits in time window
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    recent_commits = 0

    for commit in history:
        try:
            commit_date = datetime.fromisoformat(commit["date"].replace(" ", "T"))
            if commit_date.timestamp() > cutoff_date:
                recent_commits += 1
        except Exception:
            continue

    # Normalize to 0-1 (log scale to handle wide ranges)
    # 0 commits = 0.0, 10+ commits = 1.0
    import math

    if recent_commits == 0:
        return 0.0
    return min(1.0, math.log(recent_commits + 1) / math.log(11))


def get_last_major_change(
    repo_path: Path, file_path: str
) -> Optional[str]:
    """
    Find the date of the last major change (>50% of file changed).

    Args:
        repo_path: Path to repository root
        file_path: Relative path to file

    Returns:
        ISO date string or None
    """
    try:
        # Get current file size (line count approximation)
        full_path = repo_path / file_path
        if not full_path.exists():
            return None

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            current_lines = len(f.readlines())

        if current_lines == 0:
            return None

        history = get_file_history(repo_path, file_path, limit=100)

        for commit in history:
            changes = commit.get("changes", 0)
            if changes > (current_lines * 0.5):
                return commit["date"].split()[0]  # Return date part only

        return None
    except Exception:
        return None

