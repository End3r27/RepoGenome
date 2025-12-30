"""Migration utility to convert single-file genomes to sliced format."""

import logging
from pathlib import Path
from typing import Optional

from repogenome.core.schema import RepoGenome

logger = logging.getLogger(__name__)


def migrate_genome(
    repo_path: Path,
    genome_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    keep_original: bool = True,
) -> bool:
    """
    Migrate single-file genome to sliced format.

    Args:
        repo_path: Path to repository root
        genome_path: Path to genome.json file (None = auto-detect)
        output_dir: Output directory for sliced genome (None = use repogenome/)
        keep_original: Keep original genome.json file

    Returns:
        True if successful
    """
    repo_path = Path(repo_path).resolve()

    # Auto-detect genome path
    if genome_path is None:
        genome_path = repo_path / "repogenome.json"
    
    genome_path = Path(genome_path)
    
    if not genome_path.exists():
        logger.error(f"Genome file not found: {genome_path}")
        return False

    # Determine output directory
    if output_dir is None:
        output_dir = repo_path / "repogenome"
    else:
        output_dir = Path(output_dir)

    try:
        # Load genome
        logger.info(f"Loading genome from {genome_path}")
        genome = RepoGenome.load(str(genome_path))

        # Save in sliced format
        logger.info(f"Saving sliced genome to {output_dir}")
        genome.save_sliced(str(output_dir))

        logger.info(f"Migration successful. Sliced genome saved to {output_dir}")

        if not keep_original:
            logger.info(f"Removing original genome file: {genome_path}")
            genome_path.unlink()

        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


def main():
    """CLI entry point for migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate RepoGenome to sliced format")
    parser.add_argument("repo_path", type=Path, help="Path to repository root")
    parser.add_argument(
        "--genome-path",
        type=Path,
        help="Path to genome.json file (default: repo_path/repogenome.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for sliced genome (default: repo_path/repogenome)",
    )
    parser.add_argument(
        "--remove-original",
        action="store_true",
        help="Remove original genome.json file after migration",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    # Run migration
    success = migrate_genome(
        repo_path=args.repo_path,
        genome_path=args.genome_path,
        output_dir=args.output_dir,
        keep_original=not args.remove_original,
    )

    exit(0 if success else 1)


if __name__ == "__main__":
    main()

