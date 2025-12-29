"""
RepoGenome - Unified Repository Intelligence Artifact Generator

RepoGenome.json is a continuously evolving, machine-readable knowledge organism
that encodes the structure, behavior, intent, and history of a codebase.
"""

__version__ = "0.7.0"

from repogenome.core.generator import RepoGenomeGenerator
from repogenome.core.genome import Genome
from repogenome.core.schema import RepoGenome

try:
    from repogenome.mcp.server import RepoGenomeMCPServer

    __all__ = [
        "RepoGenomeGenerator",
        "RepoGenome",
        "Genome",
        "RepoGenomeMCPServer",
        "__version__",
    ]
except ImportError:
    __all__ = ["RepoGenomeGenerator", "RepoGenome", "Genome", "__version__"]

