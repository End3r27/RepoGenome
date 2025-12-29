"""MCP resource handlers for RepoGenome."""

import json
from typing import Any, Dict, List, Optional, Tuple, Union

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

    def get_current(
        self,
        fields: Optional[Union[str, List[str]]] = None,
        summary_mode: Optional[str] = None,
        variant: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get current genome resource (repogenome://current).

        Args:
            fields: Field selection (None = all fields)
            summary_mode: Summary mode (brief, standard, detailed)
            variant: Resource variant (brief, standard, detailed, lite)

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        from repogenome.utils.field_filter import filter_fields
        from repogenome.core.schema import SummaryMode
        
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

        # Handle variants
        if variant == "brief" or variant == "lite":
            data = genome._to_lite_dict()
        elif variant == "detailed":
            data = genome.to_dict()
            # Add additional metadata for detailed mode
            data["_detailed_metrics"] = {
                "file_count": sum(1 for n in genome.nodes.values() if n.type.value == "file"),
                "function_count": sum(1 for n in genome.nodes.values() if n.type.value == "function"),
                "class_count": sum(1 for n in genome.nodes.values() if n.type.value == "class"),
            }
        else:  # standard or None
            data = genome.to_dict()
        
        # Handle summary mode
        if summary_mode:
            try:
                mode = SummaryMode(summary_mode.lower())
                data["summary"] = genome.get_summary_by_mode(mode)
            except ValueError:
                pass  # Invalid mode, use default
        
        # Apply field filtering
        if fields:
            data = filter_fields(data, fields)
        
        if is_stale:
            if "_metadata" not in data:
                data["_metadata"] = {}
            data["_metadata"]["stale"] = True
            data["_metadata"]["warning"] = "Genome is stale (repo hash mismatch). Run repogenome.scan to regenerate."

        return data, None

    def get_summary(
        self,
        fields: Optional[Union[str, List[str]]] = None,
        summary_mode: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get summary resource (repogenome://summary).

        Args:
            fields: Field selection (None = all fields)
            summary_mode: Summary mode (brief, standard, detailed)

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        from repogenome.utils.field_filter import filter_fields
        from repogenome.core.schema import SummaryMode
        
        genome = self.storage.load_genome()
        if genome is None:
            error_info = {
                "error": "Summary not available",
                "reason": self.storage.get_load_error() or "Genome file not found",
                "action": "Run repogenome.scan to generate genome",
            }
            if self.storage.is_genome_file_present():
                error_info["reason"] = self.storage.get_load_error() or "Failed to load genome file"
                error_info["action"] = "Check genome file validity or run repogenome.scan to regenerate"
            return None, error_info

        # Get summary by mode
        if summary_mode:
            try:
                mode = SummaryMode(summary_mode.lower())
                summary = genome.get_summary_by_mode(mode)
            except ValueError:
                summary = genome.summary.model_dump()
        else:
            summary = genome.summary.model_dump()
        
        # Apply field filtering
        if fields:
            summary = filter_fields(summary, fields, context="summary")
        
        # Add staleness metadata if needed
        if self.storage.is_stale():
            summary["_metadata"] = {
                "stale": True,
                "warning": "Genome is stale (repo hash mismatch). Run repogenome.scan to regenerate.",
            }

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

    def get_stats(
        self,
        fields: Optional[Union[str, List[str]]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get repository statistics resource (repogenome://stats).

        Args:
            fields: Field selection (None = all fields)

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        from repogenome.mcp.tools import RepoGenomeTools
        from repogenome.utils.field_filter import filter_fields
        from pathlib import Path
        
        tools = RepoGenomeTools(self.storage, str(self.storage.repo_path))
        stats_result = tools.stats()
        
        if "error" in stats_result:
            return None, {
                "error": "Stats not available",
                "reason": stats_result.get("error", "Unknown error"),
                "action": "Run repogenome.scan to generate genome",
            }
        
        # Apply field filtering if specified
        if fields:
            stats_result = filter_fields(stats_result, fields, context="stats")
        
        return stats_result, None

    def get_node_resource(
        self,
        node_id: str,
        fields: Optional[Union[str, List[str]]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Get individual node resource (repogenome://nodes/{node_id}).

        Args:
            node_id: Node ID to retrieve
            fields: Field selection (None = all fields)

        Returns:
            Tuple of (data_dict, error_dict). One will be None.
        """
        from repogenome.mcp.tools import RepoGenomeTools
        from repogenome.utils.field_filter import filter_fields
        from pathlib import Path
        
        tools = RepoGenomeTools(self.storage, str(self.storage.repo_path))
        node_result = tools.get_node(node_id)
        
        if "error" in node_result:
            return None, {
                "error": "Node not available",
                "reason": node_result.get("error", "Unknown error"),
                "action": "Check node ID or run repogenome.scan to generate genome",
            }
        
        # Apply field filtering if specified
        if fields:
            node_result = filter_fields(node_result, fields, context="node")
        
        return node_result, None

    def read_resource(
        self,
        uri: str,
        fields: Optional[Union[str, List[str]]] = None,
        summary_mode: Optional[str] = None,
        minify: bool = False,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Read resource by URI.

        Args:
            uri: Resource URI (repogenome://current, repogenome://summary, repogenome://diff, 
                 repogenome://stats, repogenome://nodes/{node_id})
                Can be a string or AnyUrl object from Pydantic
                Supports query parameters: ?fields=id,type&mode=brief
            fields: Field selection (overrides URI query params)
            summary_mode: Summary mode (overrides URI query params)
            minify: Minify JSON output (no indentation)

        Returns:
            Tuple of (json_string, error_dict). One will be None.
        """
        from urllib.parse import urlparse, parse_qs
        
        # Convert URI to string if it's not already (handles AnyUrl objects from Pydantic)
        uri_str = str(uri) if not isinstance(uri, str) else uri
        
        # Parse URI and query parameters
        parsed = urlparse(uri_str)
        query_params = parse_qs(parsed.query)
        
        # Extract parameters from query string
        uri_fields = query_params.get("fields", [None])[0]
        uri_mode = query_params.get("mode", [None])[0]
        uri_minify = query_params.get("minify", [None])[0]
        
        # Use provided parameters or fall back to URI params
        final_fields = fields or uri_fields
        final_mode = summary_mode or uri_mode
        final_minify = minify or (uri_minify and uri_minify.lower() in ("true", "1", "yes"))
        
        # Normalize URI path: strip whitespace and convert to lowercase for comparison
        normalized_path = parsed.path.strip().lower()
        
        # Handle variants (brief, standard, detailed)
        variant = None
        if normalized_path.endswith("/brief") or normalized_path.endswith("/lite"):
            variant = "brief"
            normalized_path = normalized_path.rsplit("/", 1)[0]
        elif normalized_path.endswith("/detailed"):
            variant = "detailed"
            normalized_path = normalized_path.rsplit("/", 1)[0]
        elif normalized_path.endswith("/standard"):
            variant = "standard"
            normalized_path = normalized_path.rsplit("/", 1)[0]
        
        # Explicit URI matching (case-insensitive)
        if normalized_path == "repogenome://current" or normalized_path == "/current":
            data, error = self.get_current(fields=final_fields, summary_mode=final_mode, variant=variant)
        elif normalized_path == "repogenome://summary" or normalized_path == "/summary":
            data, error = self.get_summary(fields=final_fields, summary_mode=final_mode)
        elif normalized_path == "repogenome://diff" or normalized_path == "/diff":
            data, error = self.get_diff()
        elif normalized_path == "repogenome://stats" or normalized_path == "/stats":
            data, error = self.get_stats(fields=final_fields)
        elif normalized_path.startswith("repogenome://nodes/") or normalized_path.startswith("/nodes/"):
            # Extract node_id from URI
            node_id = parsed.path.replace("repogenome://nodes/", "").replace("/nodes/", "").strip()
            if node_id:
                data, error = self.get_node_resource(node_id, fields=final_fields)
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

