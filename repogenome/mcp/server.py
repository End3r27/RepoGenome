"""MCP server implementation for RepoGenome."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Resource,
        Tool,
        TextContent,
        ImageContent,
        EmbeddedResource,
    )
    MCP_AVAILABLE = True
except ImportError:
    # Fallback if MCP SDK not available
    MCP_AVAILABLE = False
    Server = None
    stdio_server = None

from repogenome.core.config import RepoGenomeConfig
from repogenome.mcp.contract import AgentContract
from repogenome.mcp.resources import RepoGenomeResources
from repogenome.mcp.storage import GenomeStorage
from repogenome.mcp.tools import RepoGenomeTools


class RepoGenomeMCPServer:
    """MCP server for RepoGenome."""

    def __init__(self, repo_path: Path, config: Optional[RepoGenomeConfig] = None, debug: bool = False):
        """
        Initialize MCP server.

        Args:
            repo_path: Path to repository root
            config: Optional configuration (None = load from file or use defaults)
            debug: Enable debug mode with detailed diagnostics
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP SDK not available. Install with: pip install mcp>=0.9.0"
            )

        self.repo_path = Path(repo_path).resolve()
        self.config = config or RepoGenomeConfig.load()
        self.debug = debug
        self.storage = GenomeStorage(self.repo_path)
        self.resources = RepoGenomeResources(self.storage)
        self.tools = RepoGenomeTools(self.storage, str(self.repo_path))
        self.contract = AgentContract()

        # Set up logging if debug mode is enabled
        if self.debug:
            import logging
            logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

        # Create MCP server
        self.server = Server("repogenome")

        # Register handlers (these will populate _registered_tools and _registered_resources)
        self._registered_tools = []
        self._registered_resources = []
        self._register_resources()
        self._register_tools()

    def _register_resources(self):
        """Register MCP resources."""
        # Get resources list
        resources = self.resources.list_resources()
        resource_list = [
            Resource(
                uri=r["uri"],
                name=r["name"],
                description=r["description"],
                mimeType=r["mimeType"],
            )
            for r in resources
        ]
        # Store for diagnostics
        self._registered_resources = resource_list
        if self.debug:
            import logging
            logging.debug(f"Registered {len(resource_list)} resources")
            for r in resource_list:
                logging.debug(f"  - {r.uri}: {r.description}")
        
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources."""
            return resource_list

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource by URI."""
            # Convert URI to string if it's not already (handles AnyUrl objects from Pydantic)
            uri_str = str(uri) if not isinstance(uri, str) else uri
            
            # Normalize URI for contract marking
            normalized_uri = uri_str.strip().lower()
            # Mark genome as loaded if current is accessed
            if normalized_uri.startswith("repogenome://current"):
                self.contract.mark_genome_loaded()

            # Parse query parameters from URI if present
            content, error = self.resources.read_resource(uri_str)
            if error is not None:
                # Use concise error format
                from repogenome.core.errors import format_error
                error_formatted = format_error(
                    error.get('error', 'Unknown error'),
                    error.get('action', 'No action specified'),
                    details=error.get('details'),
                )
                error_message = json.dumps(error_formatted, indent=2)
                raise ValueError(error_message)
            
            if content is None:
                # Fallback error (should not happen with new implementation)
                from repogenome.core.errors import format_error
                error_formatted = format_error(
                    "Resource not found",
                    "Run repogenome.scan to generate or regenerate the genome",
                )
                raise ValueError(json.dumps(error_formatted, indent=2))
            
            return content

    def _register_tools(self):
        """Register MCP tools."""
        # Create tool list
        tool_list = [
                Tool(
                    name="repogenome.scan",
                    description="Scan repository and generate RepoGenome",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "scope": {
                                "type": "string",
                                "enum": ["full", "structure", "flows", "history"],
                                "default": "full",
                                "description": "Scan scope",
                            },
                            "incremental": {
                                "type": "boolean",
                                "default": True,
                                "description": "Use incremental update if possible",
                            },
                        },
                    },
                ),
                Tool(
                    name="repogenome.query",
                    description="Query RepoGenome graph with pagination, field selection, and advanced filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query string (natural language or structured)",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["json", "graph"],
                                "default": "json",
                                "description": "Output format",
                            },
                            "page": {
                                "type": "integer",
                                "default": 1,
                                "description": "Page number (1-indexed)",
                            },
                            "page_size": {
                                "type": "integer",
                                "default": 50,
                                "description": "Number of results per page",
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional filters (supports AND/OR logic)",
                            },
                            "fields": {
                                "type": ["array", "string"],
                                "items": {"type": "string"},
                                "description": "Field selection (None = all fields, '*' = all fields, list = specific fields). Supports aliases: t=type, f=file, s=summary",
                            },
                            "ids_only": {
                                "type": "boolean",
                                "default": False,
                                "description": "Return only node IDs (minimal context)",
                            },
                            "max_summary_length": {
                                "type": "integer",
                                "description": "Maximum length for summaries (None = use config default)",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="repogenome.impact",
                    description="Simulate impact of proposed changes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "affected_nodes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of node IDs that will be affected",
                            },
                            "operation": {
                                "type": "string",
                                "enum": ["modify", "delete", "add"],
                                "default": "modify",
                                "description": "Operation type",
                            },
                        },
                        "required": ["affected_nodes"],
                    },
                ),
                Tool(
                    name="repogenome.update",
                    description="Incrementally update genome after code changes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "added_nodes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of new node IDs",
                            },
                            "removed_nodes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of removed node IDs",
                            },
                            "updated_edges": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "List of updated edge dicts",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for update",
                            },
                        },
                    },
                ),
                Tool(
                    name="repogenome.validate",
                    description="Ensure RepoGenome matches repo state",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="repogenome.get_node",
                    description="Get detailed information about a specific node with configurable depth and field selection",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_id": {
                                "type": "string",
                                "description": "Node ID to retrieve",
                            },
                            "max_depth": {
                                "type": "integer",
                                "default": 1,
                                "description": "Maximum depth for relationships (0 = node only, 1 = direct only)",
                            },
                            "fields": {
                                "type": ["array", "string"],
                                "items": {"type": "string"},
                                "description": "Field selection (None = all fields). Supports dot notation: node.id, incoming_edges.from",
                            },
                            "include_edges": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to include edge information",
                            },
                            "edge_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter edges by type (None = all types)",
                            },
                        },
                        "required": ["node_id"],
                    },
                ),
                Tool(
                    name="repogenome.search",
                    description="Advanced search with filters (type, language, file pattern)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Text search query",
                            },
                            "node_type": {
                                "type": "string",
                                "description": "Filter by node type (e.g., 'function', 'class', 'file')",
                            },
                            "language": {
                                "type": "string",
                                "description": "Filter by programming language",
                            },
                            "file_pattern": {
                                "type": "string",
                                "description": "File path pattern (supports wildcards)",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50,
                                "description": "Maximum number of results",
                            },
                        },
                    },
                ),
                Tool(
                    name="repogenome.dependencies",
                    description="Get dependency graph for a node",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_id": {
                                "type": "string",
                                "description": "Node ID to get dependencies for",
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["incoming", "outgoing", "both"],
                                "default": "both",
                                "description": "Direction of dependencies",
                            },
                            "depth": {
                                "type": "integer",
                                "default": 1,
                                "description": "Maximum depth to traverse (1 = direct dependencies only)",
                            },
                        },
                        "required": ["node_id"],
                    },
                ),
                Tool(
                    name="repogenome.stats",
                    description="Get repository statistics and metrics",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="repogenome.export",
                    description="Export genome to different formats via MCP",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "enum": ["json", "graphml", "dot", "csv", "cypher", "plantuml"],
                                "default": "json",
                                "description": "Export format",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Optional output path (default: genome location with format extension)",
                            },
                        },
                    },
                ),
                Tool(
                    name="repogenome.batch",
                    description="Batch operations: get multiple nodes or dependencies in one call",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["get_nodes", "dependencies"],
                                "description": "Batch operation type",
                            },
                            "node_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of node IDs",
                            },
                            "fields": {
                                "type": ["array", "string"],
                                "items": {"type": "string"},
                                "description": "Field selection (for get_nodes)",
                            },
                            "include_edges": {
                                "type": "boolean",
                                "default": False,
                                "description": "Include edge information (for get_nodes)",
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["incoming", "outgoing", "both"],
                                "default": "both",
                                "description": "Direction of dependencies (for dependencies)",
                            },
                            "depth": {
                                "type": "integer",
                                "default": 1,
                                "description": "Maximum depth (for dependencies)",
                            },
                        },
                        "required": ["operation", "node_ids"],
                    },
                ),
                Tool(
                    name="repogenome.compare",
                    description="Compare two nodes or node with previous version",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node_id1": {
                                "type": "string",
                                "description": "First node ID",
                            },
                            "node_id2": {
                                "type": "string",
                                "description": "Second node ID (optional if compare_with_previous=True)",
                            },
                            "compare_with_previous": {
                                "type": "boolean",
                                "default": False,
                                "description": "Compare node_id1 with previous genome version",
                            },
                        },
                        "required": ["node_id1"],
                    },
                ),
                Tool(
                    name="repogenome.filter",
                    description="Advanced filtering with complex expressions (AND/OR/NOT, ranges, regex)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filters": {
                                "type": "object",
                                "description": "Filter dictionary with AND/OR/NOT logic, range queries, regex patterns",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 100,
                                "description": "Maximum number of results",
                            },
                            "fields": {
                                "type": ["array", "string"],
                                "items": {"type": "string"},
                                "description": "Field selection",
                            },
                        },
                        "required": ["filters"],
                    },
                ),
                Tool(
                    name="repogenome.find_path",
                    description="Find paths between two nodes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "from_node": {
                                "type": "string",
                                "description": "Source node ID",
                            },
                            "to_node": {
                                "type": "string",
                                "description": "Target node ID",
                            },
                            "max_depth": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum path length",
                            },
                            "edge_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional filter for edge types to consider",
                            },
                        },
                        "required": ["from_node", "to_node"],
                    },
                ),
            ]
        # Store for diagnostics
        self._registered_tools = tool_list
        if self.debug:
            import logging
            logging.debug(f"Registered {len(tool_list)} tools")
            for tool in tool_list:
                logging.debug(f"  - {tool.name}: {tool.description}")
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return tool_list

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            # Enforce contract
            contract_check = self.contract.enforce_contract_middleware(name, arguments)
            if contract_check:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": contract_check}, indent=2),
                    )
                ]

            # Route to appropriate tool handler
            try:
                if name == "repogenome.scan":
                    result = self.tools.scan(
                        scope=arguments.get("scope", "full"),
                        incremental=arguments.get("incremental", True),
                    )
                    if result.get("success"):
                        self.contract.mark_genome_loaded()

                elif name == "repogenome.query":
                    result = self.tools.query(
                        query=arguments.get("query", ""),
                        format=arguments.get("format", "json"),
                        page=arguments.get("page", 1),
                        page_size=arguments.get("page_size", 50),
                        filters=arguments.get("filters"),
                        fields=arguments.get("fields"),
                        ids_only=arguments.get("ids_only", False),
                        max_summary_length=arguments.get("max_summary_length"),
                    )

                elif name == "repogenome.impact":
                    result = self.tools.impact(
                        affected_nodes=arguments.get("affected_nodes", []),
                        operation=arguments.get("operation", "modify"),
                    )
                    self.contract.mark_impact_checked()

                elif name == "repogenome.update":
                    result = self.tools.update(
                        added_nodes=arguments.get("added_nodes"),
                        removed_nodes=arguments.get("removed_nodes"),
                        updated_edges=arguments.get("updated_edges"),
                        reason=arguments.get("reason"),
                    )
                    if result.get("success"):
                        self.contract.reset_edit_state()

                elif name == "repogenome.validate":
                    result = self.tools.validate()
                    self.contract.update_validation_result(result)

                elif name == "repogenome.get_node":
                    result = self.tools.get_node(
                        node_id=arguments.get("node_id", ""),
                        max_depth=arguments.get("max_depth", 1),
                        fields=arguments.get("fields"),
                        include_edges=arguments.get("include_edges", True),
                        edge_types=arguments.get("edge_types"),
                    )

                elif name == "repogenome.search":
                    result = self.tools.search(
                        query=arguments.get("query"),
                        node_type=arguments.get("node_type"),
                        language=arguments.get("language"),
                        file_pattern=arguments.get("file_pattern"),
                        limit=arguments.get("limit", 50),
                    )

                elif name == "repogenome.dependencies":
                    result = self.tools.dependencies(
                        node_id=arguments.get("node_id", ""),
                        direction=arguments.get("direction", "both"),
                        depth=arguments.get("depth", 1),
                    )

                elif name == "repogenome.stats":
                    result = self.tools.stats()

                elif name == "repogenome.export":
                    result = self.tools.export(
                        format=arguments.get("format", "json"),
                        output_path=arguments.get("output_path"),
                    )

                elif name == "repogenome.batch":
                    operation = arguments.get("operation")
                    node_ids = arguments.get("node_ids", [])
                    
                    if operation == "get_nodes":
                        result = self.tools.batch_get_nodes(
                            node_ids=node_ids,
                            fields=arguments.get("fields"),
                            include_edges=arguments.get("include_edges", False),
                        )
                    elif operation == "dependencies":
                        result = self.tools.batch_dependencies(
                            node_ids=node_ids,
                            direction=arguments.get("direction", "both"),
                            depth=arguments.get("depth", 1),
                        )
                    else:
                        result = {"error": f"Unknown batch operation: {operation}"}

                elif name == "repogenome.compare":
                    result = self.tools.compare(
                        node_id1=arguments.get("node_id1", ""),
                        node_id2=arguments.get("node_id2"),
                        compare_with_previous=arguments.get("compare_with_previous", False),
                    )

                elif name == "repogenome.filter":
                    result = self.tools.filter_nodes(
                        filters=arguments.get("filters", {}),
                        limit=arguments.get("limit", 100),
                        fields=arguments.get("fields"),
                    )

                elif name == "repogenome.find_path":
                    result = self.tools.find_path(
                        from_node=arguments.get("from_node", ""),
                        to_node=arguments.get("to_node", ""),
                        max_depth=arguments.get("max_depth", 10),
                        edge_types=arguments.get("edge_types"),
                    )

                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": str(e)}, indent=2),
                    )
                ]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )

    def log_diagnostics(self, console=None):
        """
        Log diagnostic information about the server.
        
        Args:
            console: Optional Rich Console instance for output
        """
        from rich.console import Console
        from rich.table import Table
        
        if console is None:
            console = Console()
        
        console.print("\n[bold cyan][DEBUG] RepoGenome MCP Server Diagnostics[/bold cyan]")
        console.print(f"[dim]Repository path:[/dim] {self.repo_path}")
        
        # Check genome file status
        genome_file = self.repo_path / "repogenome.json"
        genome_exists = genome_file.exists()
        console.print(f"[dim]Genome file exists:[/dim] {genome_exists}")
        if genome_exists:
            try:
                file_size = genome_file.stat().st_size
                size_mb = file_size / (1024 * 1024)
                console.print(f"[dim]Genome file size:[/dim] {size_mb:.2f} MB")
            except Exception:
                pass
        
        # Show registered tools
        console.print(f"\n[dim]Registered {len(self._registered_tools)} tools:[/dim]")
        for tool in self._registered_tools:
            console.print(f"  [green]-[/green] [bold]{tool.name}[/bold]: {tool.description}")
        
        # Show registered resources
        console.print(f"\n[dim]Registered {len(self._registered_resources)} resources:[/dim]")
        for resource in self._registered_resources:
            console.print(f"  [green]-[/green] [bold]{resource.uri}[/bold]: {resource.description}")
        
        # Show contract status
        console.print(f"\n[dim]Contract status:[/dim]")
        console.print(f"  [dim]Genome loaded:[/dim] {self.contract.check_genome_loaded()}")
        
        console.print("")

    def run_sync(self):
        """Run server synchronously (for CLI)."""
        asyncio.run(self.run())


def create_server(repo_path: Path) -> RepoGenomeMCPServer:
    """
    Create and return MCP server instance.

    Args:
        repo_path: Path to repository root

    Returns:
        RepoGenomeMCPServer instance
    """
    return RepoGenomeMCPServer(repo_path)

