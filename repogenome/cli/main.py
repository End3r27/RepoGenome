"""CLI interface for RepoGenome."""

import json
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from repogenome.cli.output import (
    create_progress_bar,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from repogenome.core.config import RepoGenomeConfig, create_default_config
from repogenome.core.generator import RepoGenomeGenerator
from repogenome.core.schema import RepoGenome

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """RepoGenome - Unified Repository Intelligence Artifact Generator."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: repogenome.json in repository root)",
)
@click.option(
    "--subsystems",
    multiple=True,
    help="Enable specific subsystems (can be used multiple times)",
)
@click.option(
    "--exclude-subsystems",
    multiple=True,
    help="Exclude specific subsystems (can be used multiple times)",
)
@click.option(
    "--incremental",
    is_flag=True,
    help="Perform incremental update if genome exists",
)
@click.option(
    "--log",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default=None,
    help="Set logging level",
)
@click.option(
    "--compact",
    is_flag=True,
    help="Use compact field names in output",
)
@click.option(
    "--minify",
    is_flag=True,
    help="Minify JSON output (no indentation, combines with --compact)",
)
@click.option(
    "--lite",
    is_flag=True,
    help="Ultra-compact mode with only essential fields",
)
@click.option(
    "--compress",
    is_flag=True,
    help="Compress output with gzip (.json.gz)",
)
@click.option(
    "--max-summary-length",
    type=int,
    default=None,
    help="Maximum length for summaries (default: 200, 0 = no summaries)",
)
@click.option(
    "--exclude-defaults",
    is_flag=True,
    help="Exclude fields with default values",
)
def generate(
    path: Path,
    output: Path,
    subsystems,
    exclude_subsystems,
    incremental,
    log,
    compact,
    minify,
    lite,
    compress,
    max_summary_length,
    exclude_defaults,
):
    """Generate a new RepoGenome for the repository."""
    if log:
        logging.basicConfig(level=log.upper(), format='%(asctime)s - %(levelname)s - %(message)s')

    console.print(f"[bold]Generating RepoGenome for:[/bold] {path}")

    # Determine output path
    if output is None:
        output = path / "repogenome.json"
    else:
        output = Path(output)

    # Check for existing genome in incremental mode
    existing_genome = None
    if incremental and output.exists():
        console.print("[yellow]Found existing genome, performing incremental update[/yellow]")
        existing_genome = output

    # Determine enabled subsystems
    enabled_subsystems = None
    if subsystems:
        enabled_subsystems = list(subsystems)
    elif exclude_subsystems:
        all_subsystems = [
            "repospider",
            "flowweaver",
            "intentatlas",
            "chronomap",
            "testgalaxy",
            "contractlens",
        ]
        enabled_subsystems = [s for s in all_subsystems if s not in exclude_subsystems]

    # Generate genome
    try:
        logger = logging.getLogger(__name__) if log else None
        generator = RepoGenomeGenerator(path, enabled_subsystems=enabled_subsystems, logger=logger)

        if incremental and existing_genome:
            genome = generator.generate(incremental=True, existing_genome_path=existing_genome)
        else:
            genome = generator.generate(incremental=False)

        # Load config for compression options (CLI flags override config)
        config = RepoGenomeConfig.load()
        
        # Determine compression options (CLI flags take precedence)
        use_compact = compact or (minify and not compact) or config.compact_fields
        use_minify = minify or config.minify_json
        use_lite = lite
        use_compress = compress or config.enable_compression
        use_exclude_defaults = exclude_defaults or config.exclude_defaults
        summary_length = max_summary_length if max_summary_length is not None else config.max_summary_length
        
        # Save genome with compression options
        genome.save(
            str(output),
            compact=use_compact,
            lite=use_lite,
            minify=use_minify,
            exclude_defaults=use_exclude_defaults,
            max_summary_length=summary_length,
            compress=use_compress,
        )

        # Show file size
        file_size = output.stat().st_size if output.exists() else 0
        size_mb = file_size / (1024 * 1024)
        console.print(f"[green]OK[/green] Genome generated: {output} ({size_mb:.2f} MB)")

        # Print summary
        summary = genome.summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Entry points: {len(summary.entry_points)}")
        console.print(f"  Nodes: {len(genome.nodes)}")
        console.print(f"  Edges: {len(genome.edges)}")
        console.print(f"  Concepts: {len(genome.concepts)}")
        console.print(f"  Flows: {len(genome.flows)}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--genome",
    "-g",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to genome file (default: repogenome.json in repository root)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
def update(path: Path, genome: Path, verbose):
    """Update an existing RepoGenome incrementally."""
    if verbose:
        print_info(f"Updating genome for: {path}")

    # Determine genome path
    if genome is None:
        genome = path / "repogenome.json"

    if not genome.exists():
        print_error(f"Genome not found at {genome}")
        console.print("Use 'generate' command to create a new genome.")
        raise click.Abort()

    try:
        config_obj = RepoGenomeConfig.load()

        with create_progress_bar() as progress:
            task = progress.add_task("[cyan]Updating genome...", total=None)

            generator = RepoGenomeGenerator(path, config=config_obj)
            updated_genome = generator.generate(
                incremental=True,
                existing_genome_path=genome,
                progress=progress,
            )

            progress.update(task, completed=True)

        # Save updated genome
        updated_genome.save(str(genome))

        print_success(f"Genome updated: {genome}")

        # Show diff if available
        if updated_genome.genome_diff:
            diff = updated_genome.genome_diff
            console.print("\n[bold]Changes:[/bold]")
            console.print(f"  Added nodes: {len(diff.added_nodes)}")
            console.print(f"  Removed nodes: {len(diff.removed_nodes)}")
            console.print(f"  Modified nodes: {len(diff.modified_nodes)}")
            console.print(f"  Added edges: {len(diff.added_edges)}")
            console.print(f"  Removed edges: {len(diff.removed_edges)}")

    except Exception as e:
        print_error(f"{e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()


@main.command()
@click.argument("genome", type=click.Path(exists=True, path_type=Path))
def validate(genome: Path):
    """Validate a RepoGenome JSON file."""
    console.print(f"[bold]Validating:[/bold] {genome}")

    try:
        loaded_genome = RepoGenome.load(str(genome))
        console.print("[green]OK[/green] Genome is valid")

        # Print structure summary
        console.print("\n[bold]Structure:[/bold]")
        console.print(f"  Metadata: OK")
        console.print(f"  Summary: OK")
        console.print(f"  Nodes: {len(loaded_genome.nodes)}")
        console.print(f"  Edges: {len(loaded_genome.edges)}")
        console.print(f"  Flows: {len(loaded_genome.flows)}")
        console.print(f"  Concepts: {len(loaded_genome.concepts)}")
        console.print(f"  History: {len(loaded_genome.history)}")
        console.print(f"  Risk: {len(loaded_genome.risk)}")
        console.print(f"  Contracts: {len(loaded_genome.contracts)}")

    except Exception as e:
        print_error(f"{e}")
        print_error("Genome is invalid")
        raise click.Abort()


@main.command()
@click.argument("old_genome", type=click.Path(exists=True, path_type=Path))
@click.argument("new_genome", type=click.Path(exists=True, path_type=Path))
def diff(old_genome: Path, new_genome: Path):
    """Show differences between two genomes."""
    console.print(f"[bold]Comparing genomes:[/bold]")
    console.print(f"  Old: {old_genome}")
    console.print(f"  New: {new_genome}")

    try:
        old = RepoGenome.load(str(old_genome))
        new = RepoGenome.load(str(new_genome))

        from repogenome.utils.json_diff import compute_genome_diff

        diff_data = compute_genome_diff(old.to_dict(), new.to_dict())

        # Create diff table
        table = Table(title="Genome Diff")

        table.add_column("Change Type", style="cyan")
        table.add_column("Count", justify="right", style="magenta")
        table.add_column("Items", style="yellow")

        table.add_row(
            "Added Nodes",
            str(len(diff_data["added_nodes"])),
            ", ".join(diff_data["added_nodes"][:10])
            + ("..." if len(diff_data["added_nodes"]) > 10 else ""),
        )
        table.add_row(
            "Removed Nodes",
            str(len(diff_data["removed_nodes"])),
            ", ".join(diff_data["removed_nodes"][:10])
            + ("..." if len(diff_data["removed_nodes"]) > 10 else ""),
        )
        table.add_row(
            "Modified Nodes",
            str(len(diff_data["modified_nodes"])),
            ", ".join(diff_data["modified_nodes"][:10])
            + ("..." if len(diff_data["modified_nodes"]) > 10 else ""),
        )
        table.add_row("Added Edges", str(len(diff_data["added_edges"])), "")
        table.add_row("Removed Edges", str(len(diff_data["removed_edges"])), "")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("repogenome.toml"),
    help="Output path for config file",
)
def init(output: Path):
    """Create a default configuration file."""
    output_path = Path(output)
    if output_path.exists():
        if not click.confirm(f"{output_path} already exists. Overwrite?"):
            return

    create_default_config(output_path)
    print_success(f"Configuration file created: {output_path}")


@main.command()
@click.argument("genome", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["graphml", "dot", "json"], case_sensitive=False),
    default="graphml",
    help="Export format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: <genome>.<format>)",
)
def export(genome: Path, format: str, output: Path):
    """Export genome to different formats."""
    try:
        loaded_genome = RepoGenome.load(str(genome))

        # Determine output path
        if output is None:
            output = genome.with_suffix(f".{format}")
        else:
            output = Path(output)

        format_lower = format.lower()

        if format_lower == "graphml":
            from repogenome.export.graphml import export_graphml

            export_graphml(loaded_genome, output)
        elif format_lower == "dot":
            from repogenome.export.dot import export_dot

            export_dot(loaded_genome, output)
        elif format_lower == "json":
            # JSON is already the default format, just copy/save
            loaded_genome.save(str(output))
        else:
            print_error(f"Unsupported format: {format}")
            raise click.Abort()

        print_success(f"Exported to {output} ({format})")

    except Exception as e:
        print_error(f"{e}")
        raise click.Abort()


@main.command()
@click.argument("genome", type=click.Path(exists=True, path_type=Path))
@click.argument("query", type=str)
def query(genome: Path, query: str):
    """Query a genome using simple query syntax."""
    try:
        loaded_genome = RepoGenome.load(str(genome))

        from repogenome.core.query import GenomeQuery, parse_simple_query

        query_obj = GenomeQuery(loaded_genome)

        # Parse query
        parsed = parse_simple_query(query)

        if parsed.get("type") == "nodes":
            filters = parsed.get("filters", {})
            results = query_obj.query_nodes(filters)

            console.print(f"\n[bold]Found {len(results)} nodes:[/bold]\n")

            table = Table()
            table.add_column("Node ID", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("File", style="yellow")

            for node_id, node_data in results[:50]:  # Limit to 50
                table.add_row(
                    node_id[:60],  # Truncate long IDs
                    node_data.get("type", ""),
                    node_data.get("file", "")[:40] or "",
                )

            console.print(table)

            if len(results) > 50:
                console.print(f"\n... and {len(results) - 50} more results")

        else:
            print_error("Unsupported query type. Use: nodes where <condition>")

    except Exception as e:
        print_error(f"{e}")
        raise click.Abort()


@main.command()
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to repogenome.json file or directory to search (default: current directory)",
)
@click.option(
    "--min-connections",
    "-m",
    type=int,
    default=0,
    help="Minimum number of connections to show a node (default: 0)",
)
def ragnatela(path: Path, min_connections: int):
    """Visualize codebase connections in an interactive 3D space.

    Opens a 3D visualization window showing all connections in the codebase.
    Main systems (highly connected nodes) appear as larger spheres.
    Use mouse drag to rotate and mouse wheel to zoom.
    """
    try:
        from repogenome.visualization.ragnatela import visualize_ragnatela

        # Determine if path is a file or directory
        genome_path = None
        search_directory = None

        if path:
            if path.is_file():
                genome_path = path
            elif path.is_dir():
                search_directory = path
            else:
                print_error(f"Path must be a file or directory: {path}")
                raise click.Abort()
        else:
            # Default to current directory
            search_directory = Path.cwd()

        console.print("[bold]Loading RepoGenome...[/bold]")
        visualize_ragnatela(
            genome_path=genome_path,
            search_directory=search_directory,
            min_connections=min_connections,
        )

    except ImportError as e:
        print_error(f"{e}")
        console.print("Install vispy with: pip install vispy>=0.14.0")
        raise click.Abort()
    except Exception as e:
        print_error(f"{e}")
        raise click.Abort()


if __name__ == "__main__":
    main()

