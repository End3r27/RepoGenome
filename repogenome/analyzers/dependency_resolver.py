"""Enhanced dependency resolution for imports."""

from pathlib import Path
from typing import Optional


class DependencyResolver:
    """Resolve imports to actual file paths."""

    def resolve_python_import(
        self, repo_path: Path, from_file: str, import_module: str
    ) -> Optional[str]:
        """
        Resolve Python import to file path.

        Args:
            repo_path: Repository root
            from_file: File containing the import
            import_module: Module being imported

        Returns:
            Relative file path or None
        """
        from_file_path = repo_path / from_file
        from_dir = from_file_path.parent

        # Handle relative imports
        if import_module.startswith("."):
            parts = import_module.split(".")
            depth = len([p for p in parts if p == ""])
            module_parts = [p for p in parts if p]
            
            target_dir = from_dir
            for _ in range(depth - 1):
                if target_dir == repo_path:
                    break
                target_dir = target_dir.parent

            # Try different resolutions
            for ext in [".py"]:
                # Try as file
                if module_parts:
                    test_path = target_dir / f"{'/'.join(module_parts)}{ext}"
                    if test_path.exists() and test_path.is_file():
                        return str(test_path.relative_to(repo_path))
                    
                    # Try as package with __init__.py
                    test_path = target_dir / "/".join(module_parts) / f"__init__{ext}"
                    if test_path.exists():
                        return str(test_path.relative_to(repo_path))

        # Handle absolute imports
        else:
            parts = import_module.split(".")
            
            # Try in repo root
            for ext in [".py"]:
                # Try as file
                test_path = repo_path / f"{'/'.join(parts)}{ext}"
                if test_path.exists() and test_path.is_file():
                    return str(test_path.relative_to(repo_path))
                
                # Try as package
                test_path = repo_path / "/".join(parts) / f"__init__{ext}"
                if test_path.exists():
                    return str(test_path.relative_to(repo_path))
                
                # Try parent directories (for namespace packages)
                current = repo_path
                for part in parts:
                    current = current / part
                    init_path = current / f"__init__{ext}"
                    if init_path.exists():
                        return str(init_path.relative_to(repo_path))

        return None

    def resolve_typescript_import(
        self, repo_path: Path, from_file: str, import_module: str
    ) -> Optional[str]:
        """
        Resolve TypeScript/JavaScript import to file path.

        Args:
            repo_path: Repository root
            from_file: File containing the import
            import_module: Module being imported

        Returns:
            Relative file path or None
        """
        from_file_path = repo_path / from_file
        from_dir = from_file_path.parent

        # Skip node_modules and external packages
        if import_module.startswith(".") or "/" not in import_module:
            # Relative or local import
            if import_module.startswith("."):
                parts = import_module.split("/")
                depth = len([p for p in parts if p in [".", ".."]])
                module_parts = [p for p in parts if p not in [".", ".."]]
                
                target_dir = from_dir
                for _ in range(depth):
                    if target_dir == repo_path:
                        break
                    target_dir = target_dir.parent

                # Try different extensions
                for ext in [".ts", ".tsx", ".js", ".jsx"]:
                    if module_parts:
                        test_path = target_dir / f"{'/'.join(module_parts)}{ext}"
                        if test_path.exists():
                            return str(test_path.relative_to(repo_path))
                    else:
                        # Try index file
                        test_path = target_dir / f"index{ext}"
                        if test_path.exists():
                            return str(test_path.relative_to(repo_path))

        return None

