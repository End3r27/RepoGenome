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

from repogenome.mcp.contract import AgentContract
from repogenome.mcp.resources import RepoGenomeResources
from repogenome.mcp.storage import GenomeStorage
from repogenome.mcp.tools import RepoGenomeTools


class RepoGenomeMCPServer:
    """MCP server for RepoGenome."""

    def __init__(self, repo_path: Path):
        """
        Initialize MCP server.

        Args:
            repo_path: Path to repository root
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP SDK not available. Install with: pip install mcp>=0.9.0"
            )

        self.repo_path = Path(repo_path).resolve()
        self.storage = GenomeStorage(self.repo_path)
        self.resources = RepoGenomeResources(self.storage)
        self.tools = RepoGenomeTools(self.storage, str(self.repo_path))
        self.contract = AgentContract()

        # Create MCP server
        self.server = Server("repogenome")

        # Register handlers
        self._register_resources()
        self._register_tools()

    def _register_resources(self):
        """Register MCP resources."""
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources."""
            resources = self.resources.list_resources()
            return [
                Resource(
                    uri=r["uri"],
                    name=r["name"],
                    description=r["description"],
                    mimeType=r["mimeType"],
                )
                for r in resources
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource by URI."""
            # Mark genome as loaded if current is accessed
            if uri == "repogenome://current":
                self.contract.mark_genome_loaded()

            content = self.resources.read_resource(uri)
            if content is None:
                raise ValueError(f"Resource not found: {uri}")
            return content

    def _register_tools(self):
        """Register MCP tools."""
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
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
                    description="Query RepoGenome graph without touching code",
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
            ]

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

