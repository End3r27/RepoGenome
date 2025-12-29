"""Repository metadata extraction."""

import subprocess
from pathlib import Path
from typing import Dict, List, Set

from repogenome.core.schema import Metadata


def detect_languages(repo_path: Path) -> List[str]:
    """
    Detect programming languages in the repository.

    Args:
        repo_path: Path to repository root

    Returns:
        List of detected language names
    """
    languages: Set[str] = set()

    # Common file extensions mapping
    extensions = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".jsx": "JavaScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".scala": "Scala",
        ".md": "Markdown",
        ".markdown": "Markdown",
        ".rst": "reStructuredText",
        ".txt": "Text",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
        ".xml": "XML",
        ".html": "HTML",
        ".css": "CSS",
        ".sh": "Shell",
        ".bash": "Bash",
        ".zsh": "Zsh",
        ".ps1": "PowerShell",
        ".sql": "SQL",
        ".r": "R",
        ".m": "MATLAB",
        ".jl": "Julia",
        ".clj": "Clojure",
        ".hs": "Haskell",
        ".ml": "OCaml",
        ".ex": "Elixir",
        ".exs": "Elixir",
    }

    # Count files by extension
    file_counts: Dict[str, int] = {}
    for ext, lang in extensions.items():
        files = list(repo_path.rglob(f"*{ext}"))
        # Filter out common directories
        files = [
            f
            for f in files
            if not any(
                part in str(f)
                for part in ["node_modules", ".git", "__pycache__", ".venv", "venv"]
            )
        ]
        if files:
            file_counts[lang] = file_counts.get(lang, 0) + len(files)
            languages.add(lang)

    # Return sorted by file count
    return sorted(languages, key=lambda x: file_counts.get(x, 0), reverse=True)


def detect_frameworks(repo_path: Path, languages: List[str]) -> List[str]:
    """
    Detect frameworks and libraries in use.

    Args:
        repo_path: Path to repository root
        languages: Detected languages

    Returns:
        List of framework names
    """
    frameworks: Set[str] = set()

    # Check for common dependency files
    if (repo_path / "requirements.txt").exists() or (
        repo_path / "pyproject.toml"
    ).exists():
        # Python frameworks
        try:
            if (repo_path / "requirements.txt").exists():
                with open(
                    repo_path / "requirements.txt", "r", encoding="utf-8"
                ) as f:
                    content = f.read().lower()
                    if "fastapi" in content or "uvicorn" in content:
                        frameworks.add("FastAPI")
                    if "flask" in content:
                        frameworks.add("Flask")
                    if "django" in content:
                        frameworks.add("Django")
        except Exception:
            pass

    if (repo_path / "package.json").exists():
        # JavaScript/TypeScript frameworks
        try:
            with open(repo_path / "package.json", "r", encoding="utf-8") as f:
                import json

                package_data = json.load(f)
                deps = {
                    **package_data.get("dependencies", {}),
                    **package_data.get("devDependencies", {}),
                }
                deps_lower = {k.lower(): v for k, v in deps.items()}

                if "react" in deps_lower:
                    frameworks.add("React")
                if "next" in deps_lower:
                    frameworks.add("Next.js")
                if "express" in deps_lower:
                    frameworks.add("Express")
                if "vue" in deps_lower:
                    frameworks.add("Vue")
                if "angular" in deps_lower:
                    frameworks.add("Angular")
        except Exception:
            pass

    return sorted(frameworks)


def extract_metadata(repo_path: Path) -> Metadata:
    """
    Extract repository metadata.

    Args:
        repo_path: Path to repository root

    Returns:
        Metadata object
    """
    from repogenome.utils.git_utils import get_repo_hash

    languages = detect_languages(repo_path)
    frameworks = detect_frameworks(repo_path, languages)
    repo_hash = get_repo_hash(repo_path)

    return Metadata(
        repo_hash=repo_hash,
        languages=languages,
        frameworks=frameworks,
        repogenome_version="0.6.0",
    )

