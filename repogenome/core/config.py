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
        compact_fields: bool = False,
        minify_json: bool = False,
        max_summary_length: Optional[int] = 200,
        exclude_defaults: bool = False,
        enable_compression: bool = False,
        default_summary_mode: str = "standard",
        default_query_fields: Optional[List[str]] = None,
        error_verbosity: str = "standard",
        default_token_budget: int = 2000,
        enable_context_cache: bool = True,
        context_cache_dir: Optional[Path] = None,
        enable_self_healing: bool = False,
        genome_format: str = "single",
        enable_repair_loops: bool = True,
        max_repair_attempts: int = 2,
        contract_score_threshold: float = 0.6,
        enable_context_lock: bool = True,
        auto_repair_simple_cases: bool = True,
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
            compact_fields: Use compact field names in output
            minify_json: Minify JSON output (no indentation)
            max_summary_length: Maximum length for summaries (None = no limit)
            exclude_defaults: Exclude fields with default values
            enable_compression: Use gzip compression for output
            default_summary_mode: Default summary mode (brief, standard, detailed)
            default_query_fields: Default fields for queries (None = all fields)
            error_verbosity: Error verbosity level (minimal, standard, verbose)
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
        self.compact_fields = compact_fields
        self.minify_json = minify_json
        self.max_summary_length = max_summary_length
        self.exclude_defaults = exclude_defaults
        self.enable_compression = enable_compression
        self.default_summary_mode = default_summary_mode
        self.default_query_fields = default_query_fields
        self.error_verbosity = error_verbosity
        self.default_token_budget = default_token_budget
        self.enable_context_cache = enable_context_cache
        self.context_cache_dir = context_cache_dir or Path(".cache/context")
        self.enable_self_healing = enable_self_healing
        self.genome_format = genome_format
        self.enable_repair_loops = enable_repair_loops
        self.max_repair_attempts = max_repair_attempts
        self.contract_score_threshold = contract_score_threshold
        self.enable_context_lock = enable_context_lock
        self.auto_repair_simple_cases = auto_repair_simple_cases

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
            compact_fields=config_data.get("compact_fields", False),
            minify_json=config_data.get("minify_json", False),
            max_summary_length=config_data.get("max_summary_length", 200),
            exclude_defaults=config_data.get("exclude_defaults", False),
            enable_compression=config_data.get("enable_compression", False),
            default_summary_mode=config_data.get("default_summary_mode", "standard"),
            default_query_fields=config_data.get("default_query_fields"),
            error_verbosity=config_data.get("error_verbosity", "standard"),
            default_token_budget=config_data.get("default_token_budget", 2000),
            enable_context_cache=config_data.get("enable_context_cache", True),
            context_cache_dir=Path(config_data["context_cache_dir"]) if config_data.get("context_cache_dir") else None,
            enable_self_healing=config_data.get("enable_self_healing", False),
            genome_format=config_data.get("genome_format", "single"),
            enable_repair_loops=config_data.get("enable_repair_loops", True),
            max_repair_attempts=config_data.get("max_repair_attempts", 2),
            contract_score_threshold=config_data.get("contract_score_threshold", 0.6),
            enable_context_lock=config_data.get("enable_context_lock", True),
            auto_repair_simple_cases=config_data.get("auto_repair_simple_cases", True),
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
            "compact_fields": self.compact_fields,
            "minify_json": self.minify_json,
            "max_summary_length": self.max_summary_length,
            "exclude_defaults": self.exclude_defaults,
            "enable_compression": self.enable_compression,
            "default_token_budget": self.default_token_budget,
            "enable_context_cache": self.enable_context_cache,
            "genome_format": self.genome_format,
            "enable_repair_loops": self.enable_repair_loops,
            "max_repair_attempts": self.max_repair_attempts,
            "contract_score_threshold": self.contract_score_threshold,
            "enable_context_lock": self.enable_context_lock,
            "auto_repair_simple_cases": self.auto_repair_simple_cases,
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

# Output compression options
compact_fields = false
minify_json = false
max_summary_length = 200
exclude_defaults = false
enable_compression = false

# Context reduction options
default_summary_mode = "standard"  # brief, standard, or detailed
# default_query_fields = ["id", "type", "file"]  # None = all fields
error_verbosity = "standard"  # minimal, standard, or verbose
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(config_content)

