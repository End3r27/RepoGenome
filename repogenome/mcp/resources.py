"""MCP resource handlers for RepoGenome."""

import json
from typing import Any, Dict, Optional

from repogenome.mcp.storage import GenomeStorage


class RepoGenomeResources:
    """Handles MCP resources for RepoGenome."""

    def __init__(self, storage: GenomeStorage):
        """
        Initialize resource handlers.

        Args:
            storage: GenomeStorage instance
        """
        self.storage = storage

    def get_current(self) -> Optional[Dict[str, Any]]:
        """
        Get current genome resource (repogenome://current).

        Returns:
            Full genome as dict or None
        """
        genome = self.storage.load_genome()
        if genome is None:
            return None

        return genome.to_dict()

    def get_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get summary resource (repogenome://summary).

        Returns:
            Summary section as dict or None
        """
        return self.storage.get_summary()

    def get_diff(self) -> Optional[Dict[str, Any]]:
        """
        Get diff resource (repogenome://diff).

        Returns:
            Diff dict or None
        """
        return self.storage.get_diff()

    def read_resource(self, uri: str) -> Optional[str]:
        """
        Read resource by URI.

        Args:
            uri: Resource URI (repogenome://current, repogenome://summary, repogenome://diff)

        Returns:
            JSON string or None
        """
        if uri == "repogenome://current":
            data = self.get_current()
        elif uri == "repogenome://summary":
            data = self.get_summary()
        elif uri == "repogenome://diff":
            data = self.get_diff()
        else:
            return None

        if data is None:
            return None

        return json.dumps(data, indent=2, ensure_ascii=False)

    def list_resources(self) -> list:
        """
        List available resources.

        Returns:
            List of resource URIs
        """
        resources = [
            {
                "uri": "repogenome://current",
                "name": "Current Genome",
                "description": "Full, up-to-date repository genome",
                "mimeType": "application/json",
            },
            {
                "uri": "repogenome://summary",
                "name": "Summary",
                "description": "Fast boot context (summary section only)",
                "mimeType": "application/json",
            },
            {
                "uri": "repogenome://diff",
                "name": "Diff",
                "description": "Changes since last update",
                "mimeType": "application/json",
            },
        ]

        # Only include diff if genome exists
        genome = self.storage.load_genome()
        if genome is None:
            resources = [r for r in resources if r["uri"] != "repogenome://diff"]

        return resources

