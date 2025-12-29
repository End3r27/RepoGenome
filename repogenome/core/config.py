"""Configuration management for RepoGenome."""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli  # Python 3.11+
    except ImportError:
        tomli = None


class RepoGenomeConfig:
    """Configuration for RepoGenome analysis."""

    def __init__(
        self,
        enabled_subsystems: Optional[List[str]] = None,
        disabled_subsystems: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        complexity_threshold: float = 10.0,
        risk_threshold: float = 0.7,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        enable_cache: bool = True,
        parallel_workers: Optional[int] = None,
    ):
        """
        Initialize configuration.

        Args:
            enabled_subsystems: List of subsystem names to enable (None = all)
            disabled_subsystems: List of subsystem names to disable
            ignore_patterns: Glob patterns for files/directories to ignore
            complexity_threshold: Complexity threshold for warnings
            risk_threshold: Risk score threshold for warnings
            max_file_size: Maximum file size to analyze (bytes)
            enable_cache: Whether to enable caching
            parallel_workers: Number of parallel workers (None = auto)
        """
        self.enabled_subsystems = enabled_subsystems
        self.disabled_subsystems = disabled_subsystems or []
        self.ignore_patterns = ignore_patterns or [
            "**/node_modules/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/venv/**",
            "**/dist/**",
            "**/build/**",
            "**/.pytest_cache/**",
        ]
        self.complexity_threshold = complexity_threshold
        self.risk_threshold = risk_threshold
        self.max_file_size = max_file_size
        self.enable_cache = enable_cache
        self.parallel_workers = parallel_workers

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "RepoGenomeConfig":
        """
        Load configuration from file.

        Args:
            config_path: Path to config file (None = search for repogenome.toml)

        Returns:
            RepoGenomeConfig instance
        """
        if config_path is None:
            # Search for repogenome.toml in current directory and parent directories
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                candidate = parent / "repogenome.toml"
                if candidate.exists():
                    config_path = candidate
                    break

        if config_path is None or not config_path.exists():
            return cls()  # Return default config

        if tomli is None:
            raise ImportError(
                "tomli is required to load config files. Install with: pip install tomli"
            )

        try:
            with open(config_path, "rb") as f:
                data = tomli.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {e}")

        # Parse configuration
        config_data = data.get("repogenome", {})

        return cls(
            enabled_subsystems=config_data.get("enabled_subsystems"),
            disabled_subsystems=config_data.get("disabled_subsystems"),
            ignore_patterns=config_data.get("ignore_patterns"),
            complexity_threshold=config_data.get("complexity_threshold", 10.0),
            risk_threshold=config_data.get("risk_threshold", 0.7),
            max_file_size=config_data.get("max_file_size", 10 * 1024 * 1024),
            enable_cache=config_data.get("enable_cache", True),
            parallel_workers=config_data.get("parallel_workers"),
        )

    def should_analyze_file(self, file_path: Path) -> bool:
        """
        Check if a file should be analyzed based on ignore patterns.

        Args:
            file_path: Path to file (relative to repo root)

        Returns:
            True if file should be analyzed
        """
        from fnmatch import fnmatch

        file_str = str(file_path)
        for pattern in self.ignore_patterns:
            if fnmatch(file_str, pattern):
                return False
        return True

    def get_enabled_subsystems(self, all_subsystems: List[str]) -> List[str]:
        """
        Get list of enabled subsystems based on configuration.

        Args:
            all_subsystems: List of all available subsystem names

        Returns:
            List of enabled subsystem names
        """
        if self.enabled_subsystems is not None:
            return [
                s for s in self.enabled_subsystems if s in all_subsystems
            ]

        # If disabled_subsystems is specified, exclude them
        if self.disabled_subsystems:
            return [
                s for s in all_subsystems if s not in self.disabled_subsystems
            ]

        return all_subsystems

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "enabled_subsystems": self.enabled_subsystems,
            "disabled_subsystems": self.disabled_subsystems,
            "ignore_patterns": self.ignore_patterns,
            "complexity_threshold": self.complexity_threshold,
            "risk_threshold": self.risk_threshold,
            "max_file_size": self.max_file_size,
            "enable_cache": self.enable_cache,
            "parallel_workers": self.parallel_workers,
        }


def create_default_config(output_path: Path) -> None:
    """Create a default configuration file."""
    config_content = """# RepoGenome Configuration

[repogenome]
# Enable specific subsystems (comment out to enable all)
# enabled_subsystems = ["repospider", "intentatlas", "chronomap"]

# Disable specific subsystems
# disabled_subsystems = ["testgalaxy"]

# Files and directories to ignore (glob patterns)
ignore_patterns = [
    "**/node_modules/**",
    "**/.git/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/dist/**",
    "**/build/**",
    "**/.pytest_cache/**",
]

# Analysis thresholds
complexity_threshold = 10.0
risk_threshold = 0.7

# Maximum file size to analyze (bytes)
max_file_size = 10485760  # 10MB

# Enable caching
enable_cache = true

# Number of parallel workers (None = auto-detect)
# parallel_workers = 4
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(config_content)

