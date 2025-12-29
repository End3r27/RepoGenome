"""MCP resource handlers for RepoGenome."""

import json
from typing import Any, Dict, Optional, Tuple

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

    def get_current(self) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get current genome resource (repogenome://current).

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        genome, is_stale, error = self.storage.get_genome_status()
        if genome is None:
            error_info = {
                "error": "Genome not available",
                "reason": error or "Genome file not found",
                "action": "Run repogenome.scan to generate genome",
            }
            if self.storage.is_genome_file_present():
                error_info["reason"] = error or "Failed to load genome file"
                error_info["action"] = "Check genome file validity or run repogenome.scan to regenerate"
            return None, error_info

        data = genome.to_dict()
        if is_stale:
            if "_metadata" not in data:
                data["_metadata"] = {}
            data["_metadata"]["stale"] = True
            data["_metadata"]["warning"] = "Genome is stale (repo hash mismatch). Run repogenome.scan to regenerate."

        return data, None

    def get_summary(self) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get summary resource (repogenome://summary).

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        summary = self.storage.get_summary()
        if summary is None:
            error_info = {
                "error": "Summary not available",
                "reason": self.storage.get_load_error() or "Genome file not found",
                "action": "Run repogenome.scan to generate genome",
            }
            if self.storage.is_genome_file_present():
                error_info["reason"] = self.storage.get_load_error() or "Failed to load genome file"
                error_info["action"] = "Check genome file validity or run repogenome.scan to regenerate"
            return None, error_info

        return summary, None

    def get_diff(self) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get diff resource (repogenome://diff).

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        diff = self.storage.get_diff()
        if diff is None:
            genome, is_stale, error = self.storage.get_genome_status()
            if genome is None:
                error_info = {
                    "error": "Diff not available",
                    "reason": error or "Genome file not found",
                    "action": "Run repogenome.scan to generate genome",
                }
                if self.storage.is_genome_file_present():
                    error_info["reason"] = error or "Failed to load genome file"
                    error_info["action"] = "Check genome file validity or run repogenome.scan to regenerate"
            else:
                error_info = {
                    "error": "Diff not available",
                    "reason": "No diff data available in genome",
                    "action": "Diff is only available after genome updates",
                }
            return None, error_info

        return diff, None

    def read_resource(self, uri: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Read resource by URI.

        Args:
            uri: Resource URI (repogenome://current, repogenome://summary, repogenome://diff)
                Can be a string or AnyUrl object from Pydantic

        Returns:
            Tuple of (json_string, error_dict). One will be None.
        """
        # Convert URI to string if it's not already (handles AnyUrl objects from Pydantic)
        uri_str = str(uri) if not isinstance(uri, str) else uri
        
        # Normalize URI: strip whitespace and convert to lowercase for comparison
        normalized_uri = uri_str.strip()
        normalized_lower = normalized_uri.lower()
        
        # Explicit URI matching (case-insensitive)
        if normalized_lower == "repogenome://current":
            data, error = self.get_current()
        elif normalized_lower == "repogenome://summary":
            data, error = self.get_summary()
        elif normalized_lower == "repogenome://diff":
            data, error = self.get_diff()
        else:
            # Provide detailed error information for debugging
            error = {
                "error": "Unknown resource URI",
                "reason": f"URI not recognized: {uri_str!r}",
                "uri_details": {
                    "original": repr(uri),
                    "original_str": repr(uri_str),
                    "normalized": repr(normalized_uri),
                    "length": len(uri_str),
                    "normalized_length": len(normalized_uri),
                    "bytes": list(uri_str.encode('utf-8'))[:50],  # First 50 bytes for debugging
                },
                "action": "Use one of: repogenome://current, repogenome://summary, repogenome://diff",
                "available_uris": ["repogenome://current", "repogenome://summary", "repogenome://diff"],
            }
            return None, error

        if error is not None:
            return None, error

        if data is None:
            error = {
                "error": "Resource data is None",
                "reason": "Unexpected state: data is None but no error was set",
                "action": "Report this as a bug",
            }
            return None, error

        return json.dumps(data, indent=2, ensure_ascii=False), None

    def get_stats(self) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get repository statistics resource (repogenome://stats).

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        from repogenome.mcp.tools import RepoGenomeTools
        from pathlib import Path
        
        tools = RepoGenomeTools(self.storage, str(self.storage.repo_path))
        stats_result = tools.stats()
        
        if "error" in stats_result:
            return None, {
                "error": "Stats not available",
                "reason": stats_result.get("error", "Unknown error"),
                "action": "Run repogenome.scan to generate genome",
            }
        
        return stats_result, None

    def get_node_resource(self, node_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get individual node resource (repogenome://nodes/{node_id}).

        Args:
            node_id: Node ID to retrieve

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        from repogenome.mcp.tools import RepoGenomeTools
        from pathlib import Path
        
        tools = RepoGenomeTools(self.storage, str(self.storage.repo_path))
        node_result = tools.get_node(node_id)
        
        if "error" in node_result:
            return None, {
                "error": "Node not available",
                "reason": node_result.get("error", "Unknown error"),
                "action": "Check node ID or run repogenome.scan to generate genome",
            }
        
        return node_result, None

    def read_resource(self, uri: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Read resource by URI.

        Args:
            uri: Resource URI (repogenome://current, repogenome://summary, repogenome://diff, 
                 repogenome://stats, repogenome://nodes/{node_id})
                Can be a string or AnyUrl object from Pydantic

        Returns:
            Tuple of (json_string, error_dict). One will be None.
        """
        # Convert URI to string if it's not already (handles AnyUrl objects from Pydantic)
        uri_str = str(uri) if not isinstance(uri, str) else uri
        
        # Normalize URI: strip whitespace and convert to lowercase for comparison
        normalized_uri = uri_str.strip()
        normalized_lower = normalized_uri.lower()
        
        # Explicit URI matching (case-insensitive)
        if normalized_lower == "repogenome://current":
            data, error = self.get_current()
        elif normalized_lower == "repogenome://summary":
            data, error = self.get_summary()
        elif normalized_lower == "repogenome://diff":
            data, error = self.get_diff()
        elif normalized_lower == "repogenome://stats":
            data, error = self.get_stats()
        elif normalized_lower.startswith("repogenome://nodes/"):
            # Extract node_id from URI
            node_id = normalized_uri.replace("repogenome://nodes/", "").strip()
            if node_id:
                data, error = self.get_node_resource(node_id)
            else:
                error = {
                    "error": "Invalid node resource URI",
                    "reason": "Node ID is missing from URI",
                    "action": "Use format: repogenome://nodes/{node_id}",
                }
                return None, error
        else:
            # Provide detailed error information for debugging
            error = {
                "error": "Unknown resource URI",
                "reason": f"URI not recognized: {uri_str!r}",
                "uri_details": {
                    "original": repr(uri),
                    "normalized": repr(normalized_uri),
                    "length": len(uri_str),
                    "normalized_length": len(normalized_uri),
                    "bytes": list(uri_str.encode('utf-8'))[:50],  # First 50 bytes for debugging
                },
                "action": "Use one of: repogenome://current, repogenome://summary, repogenome://diff, repogenome://stats, repogenome://nodes/{node_id}",
                "available_uris": [
                    "repogenome://current",
                    "repogenome://summary",
                    "repogenome://diff",
                    "repogenome://stats",
                    "repogenome://nodes/{node_id}",
                ],
            }
            return None, error

        if error is not None:
            return None, error

        if data is None:
            error = {
                "error": "Resource data is None",
                "reason": "Unexpected state: data is None but no error was set",
                "action": "Report this as a bug",
            }
            return None, error

        return json.dumps(data, indent=2, ensure_ascii=False), None

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
            {
                "uri": "repogenome://stats",
                "name": "Statistics",
                "description": "Repository statistics and metrics",
                "mimeType": "application/json",
            },
        ]

        # Only include diff if genome exists
        genome = self.storage.load_genome()
        if genome is None:
            resources = [r for r in resources if r["uri"] != "repogenome://diff"]
            resources = [r for r in resources if r["uri"] != "repogenome://stats"]

        return resources

