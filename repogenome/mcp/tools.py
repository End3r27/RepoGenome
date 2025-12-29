"""MCP tool implementations for RepoGenome."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from repogenome.core.generator import RepoGenomeGenerator
from repogenome.core.query import GenomeQuery, parse_simple_query
from repogenome.core.schema import RepoGenome
from repogenome.mcp.storage import GenomeStorage


class RepoGenomeTools:
    """Handles MCP tools for RepoGenome."""

    def __init__(self, storage: GenomeStorage, repo_path: str):
        """
        Initialize tool handlers.

        Args:
            storage: GenomeStorage instance
            repo_path: Path to repository root
        """
        self.storage = storage
        self.repo_path = repo_path
        self._query_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._cache_ttl: float = 300.0  # 5 minutes

    def scan(
        self, scope: str = "full", incremental: bool = True
    ) -> Dict[str, Any]:
        """
        Scan repository and generate RepoGenome.

        Args:
            scope: Scan scope ("full", "structure", "flows", "history")
            incremental: Use incremental update if possible

        Returns:
            Result dict with success status and message
        """
        try:
            from pathlib import Path

            generator = RepoGenomeGenerator(Path(self.repo_path))

            # Determine which subsystems to enable based on scope
            if scope == "structure":
                enabled_subsystems = ["repospider"]
            elif scope == "flows":
                enabled_subsystems = ["repospider", "flowweaver"]
            elif scope == "history":
                enabled_subsystems = ["repospider", "chronomap"]
            else:  # full
                enabled_subsystems = None

            generator.subsystems = {
                k: v
                for k, v in generator.subsystems.items()
                if enabled_subsystems is None or k in enabled_subsystems
            }

            # Check if incremental update is possible
            existing_genome = self.storage.load_genome()
            if incremental and existing_genome and not self.storage.is_stale():
                genome = generator.generate(
                    incremental=True,
                    existing_genome_path=self.storage.genome_path,
                )
            else:
                genome = generator.generate(incremental=False)

            # Save genome
            self.storage.save_genome(genome)

            return {
                "success": True,
                "message": f"Genome generated successfully ({scope} scan)",
                "nodes": len(genome.nodes),
                "edges": len(genome.edges),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def query(
        self,
        query: str,
        format: str = "json",
        page: int = 1,
        page_size: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Query RepoGenome graph with pagination and advanced filtering.

        Args:
            query: Query string (natural language or structured)
            format: Output format ("json" or "graph")
            page: Page number (1-indexed)
            page_size: Number of results per page
            filters: Additional filters (AND/OR logic supported)
            use_cache: Whether to use cached query results

        Returns:
            Query results with pagination
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        # Check cache
        if use_cache:
            cache_key = f"{query}:{format}:{page}:{page_size}:{str(filters)}"
            if cache_key in self._query_cache:
                cached_result, cached_time = self._query_cache[cache_key]
                if time.time() - cached_time < self._cache_ttl:
                    return cached_result
                else:
                    # Remove expired cache entry
                    del self._query_cache[cache_key]

        try:
            query_obj = GenomeQuery(genome)

            # Try to parse as structured query
            parsed = parse_simple_query(query)
            if parsed:
                if parsed.get("type") == "nodes":
                    # Merge parsed filters with additional filters
                    query_filters = parsed.get("filters", {})
                    if filters:
                        # Support AND/OR logic in filters
                        if "and" in filters or "or" in filters:
                            query_filters = filters
                        else:
                            # Merge filters (AND logic by default)
                            query_filters.update(filters)
                    
                    results = query_obj.query_nodes(query_filters)
                    
                    # Apply pagination
                    total_count = len(results)
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    paginated_results = results[start_idx:end_idx]
                    
                    result = {
                        "type": "nodes",
                        "count": total_count,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
                        "results": [
                            {
                                "id": node_id,
                                **(node_data.model_dump() if hasattr(node_data, 'model_dump') else (node_data if isinstance(node_data, dict) else {}))
                            }
                            for node_id, node_data in paginated_results
                        ],
                    }
                    
                    # Cache result
                    if use_cache:
                        cache_key = f"{query}:{format}:{page}:{page_size}:{str(filters)}"
                        self._query_cache[cache_key] = (result, time.time())
                        # Limit cache size
                        if len(self._query_cache) > 100:
                            # Remove oldest entries
                            sorted_cache = sorted(self._query_cache.items(), key=lambda x: x[1][1])
                            for key, _ in sorted_cache[:20]:
                                del self._query_cache[key]
                    
                    return result
            else:
                # Natural language query - simple keyword matching
                query_lower = query.lower()
                results = []

                # Search in nodes
                for node_id, node_data in genome.nodes.items():
                    # Convert Pydantic model to dict if needed
                    if hasattr(node_data, 'model_dump'):
                        node_dict = node_data.model_dump()
                    elif hasattr(node_data, 'dict'):
                        node_dict = node_data.dict()
                    else:
                        node_dict = node_data if isinstance(node_data, dict) else {}
                    
                    # Apply additional filters if provided
                    if filters:
                        match = True
                        if "type" in filters and node_dict.get('type') != filters["type"]:
                            match = False
                        if match and "language" in filters and node_dict.get('language') != filters["language"]:
                            match = False
                        if not match:
                            continue
                    
                    summary = node_dict.get('summary', '') or ''
                    file_path = node_dict.get('file', '') or ''
                    node_str = f"{node_id} {summary} {file_path}".lower()
                    if any(word in node_str for word in query_lower.split()):
                        results.append({"id": node_id, **node_dict})

                # Search in concepts
                for concept_id, concept_data in genome.concepts.items():
                    if any(word in concept_id.lower() for word in query_lower.split()):
                        results.append(
                            {
                                "id": concept_id,
                                "type": "concept",
                                **concept_data.model_dump(),
                            }
                        )

                # Apply pagination
                total_count = len(results)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_results = results[start_idx:end_idx]

                result = {
                    "type": "search",
                    "query": query,
                    "count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
                    "results": paginated_results,
                }
                
                # Cache result
                if use_cache:
                    cache_key = f"{query}:{format}:{page}:{page_size}:{str(filters)}"
                    self._query_cache[cache_key] = (result, time.time())
                    # Limit cache size
                    if len(self._query_cache) > 100:
                        # Remove oldest entries
                        sorted_cache = sorted(self._query_cache.items(), key=lambda x: x[1][1])
                        for key, _ in sorted_cache[:20]:
                            del self._query_cache[key]
                
                return result
        except Exception as e:
            return {"error": f"Query failed: {str(e)}"}

    def impact(
        self, affected_nodes: List[str], operation: str = "modify"
    ) -> Dict[str, Any]:
        """
        Simulate impact of proposed changes.

        Args:
            affected_nodes: List of node IDs that will be affected
            operation: Operation type ("modify", "delete", "add")

        Returns:
            Impact analysis with risk score and affected components
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        try:
            affected_flows = []
            affected_contracts = []
            total_risk = 0.0
            max_risk = 0.0

            for node_id in affected_nodes:
                if node_id not in genome.nodes:
                    continue

                node = genome.nodes[node_id]

                # Check flows
                for flow in genome.flows:
                    if node_id in flow.path:
                        affected_flows.append(flow.entry)

                # Check contracts
                for contract_id, contract in genome.contracts.items():
                    if node_id in contract.depends_on:
                        affected_contracts.append(contract_id)

                # Get risk score
                risk_data = genome.risk.get(node_id)
                if risk_data:
                    risk_score = risk_data.risk_score
                    total_risk += risk_score
                    max_risk = max(max_risk, risk_score)

            # Calculate average risk
            avg_risk = total_risk / len(affected_nodes) if affected_nodes else 0.0

            # Determine if approval required
            requires_approval = (
                max_risk > 0.7
                or len(affected_flows) > 5
                or len(affected_contracts) > 0
            )

            return {
                "risk_score": max(max_risk, avg_risk),
                "affected_flows": list(set(affected_flows)),
                "affected_contracts": list(set(affected_contracts)),
                "affected_nodes_count": len(affected_nodes),
                "requires_approval": requires_approval,
                "operation": operation,
            }
        except Exception as e:
            return {"error": f"Impact analysis failed: {str(e)}"}

    def update(
        self,
        added_nodes: Optional[List[str]] = None,
        removed_nodes: Optional[List[str]] = None,
        updated_edges: Optional[List[Dict[str, Any]]] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Incrementally update genome after code changes.

        Args:
            added_nodes: List of new node IDs
            removed_nodes: List of removed node IDs
            updated_edges: List of updated edge dicts
            reason: Reason for update

        Returns:
            Update result
        """
        try:
            # Trigger incremental scan
            result = self.scan(scope="full", incremental=True)
            if not result.get("success"):
                return result

            genome = self.storage.load_genome()
            if genome is None:
                return {"error": "Failed to load updated genome"}

            # Log the update reason if provided
            update_info = {
                "success": True,
                "message": "Genome updated successfully",
                "reason": reason,
                "nodes": len(genome.nodes),
                "edges": len(genome.edges),
            }

            if genome.genome_diff:
                update_info["diff"] = {
                    "added_nodes": len(genome.genome_diff.added_nodes),
                    "removed_nodes": len(genome.genome_diff.removed_nodes),
                    "modified_nodes": len(genome.genome_diff.modified_nodes),
                }

            return update_info
        except Exception as e:
            return {"error": f"Update failed: {str(e)}"}

    def validate(self) -> Dict[str, Any]:
        """
        Validate RepoGenome consistency with repository.

        Returns:
            Validation result
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {
                "valid": False,
                "error": "No genome found",
                "action": "Run repogenome.scan to generate genome",
            }

        # Check if stale
        if self.storage.is_stale():
            return {
                "valid": False,
                "error": "Genome is stale (repo hash mismatch)",
                "action": "Run repogenome.scan to regenerate",
            }

        # Basic validation checks
        issues = []

        # Check for orphaned edges
        node_ids = set(genome.nodes.keys())
        for edge in genome.edges:
            if edge.from_ not in node_ids:
                issues.append(f"Edge from missing node: {edge.from_}")
            if edge.to not in node_ids:
                issues.append(f"Edge to missing node: {edge.to}")

        if issues:
            return {
                "valid": False,
                "error": "Genome has consistency issues",
                "issues": issues,
                "action": "Run repogenome.scan to regenerate",
            }

        return {
            "valid": True,
            "message": "Genome is valid and up-to-date",
            "nodes": len(genome.nodes),
            "edges": len(genome.edges),
        }

    def get_node(self, node_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific node.

        Args:
            node_id: Node ID to retrieve

        Returns:
            Node details with relationships
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        try:
            if node_id not in genome.nodes:
                return {"error": f"Node not found: {node_id}"}

            node = genome.nodes[node_id]
            
            # Convert node to dict
            if hasattr(node, 'model_dump'):
                node_dict = node.model_dump()
            elif hasattr(node, 'dict'):
                node_dict = node.dict()
            else:
                node_dict = node if isinstance(node, dict) else {}

            # Get incoming edges
            incoming_edges = [
                {
                    "from": edge.from_,
                    "to": edge.to,
                    "type": edge.type if hasattr(edge, 'type') else None,
                }
                for edge in genome.edges
                if edge.to == node_id
            ]

            # Get outgoing edges
            outgoing_edges = [
                {
                    "from": edge.from_,
                    "to": edge.to,
                    "type": edge.type if hasattr(edge, 'type') else None,
                }
                for edge in genome.edges
                if edge.from_ == node_id
            ]

            # Get risk information
            risk_data = None
            if node_id in genome.risk:
                risk = genome.risk[node_id]
                if hasattr(risk, 'model_dump'):
                    risk_data = risk.model_dump()
                elif hasattr(risk, 'dict'):
                    risk_data = risk.dict()
                else:
                    risk_data = risk if isinstance(risk, dict) else None

            return {
                "node": node_dict,
                "incoming_edges": incoming_edges,
                "outgoing_edges": outgoing_edges,
                "risk": risk_data,
                "incoming_count": len(incoming_edges),
                "outgoing_count": len(outgoing_edges),
            }
        except Exception as e:
            return {"error": f"Failed to get node: {str(e)}"}

    def search(
        self,
        query: Optional[str] = None,
        node_type: Optional[str] = None,
        language: Optional[str] = None,
        file_pattern: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Advanced search with filters.

        Args:
            query: Text search query
            node_type: Filter by node type (e.g., "function", "class", "file")
            language: Filter by programming language
            file_pattern: File path pattern (supports wildcards)
            limit: Maximum number of results

        Returns:
            Search results
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        try:
            import fnmatch
            results = []

            for node_id, node_data in genome.nodes.items():
                # Convert to dict
                if hasattr(node_data, 'model_dump'):
                    node_dict = node_data.model_dump()
                elif hasattr(node_data, 'dict'):
                    node_dict = node_data.dict()
                else:
                    node_dict = node_data if isinstance(node_data, dict) else {}

                # Apply filters
                match = True

                # Type filter
                if node_type and node_dict.get('type') != node_type:
                    match = False

                # Language filter
                if match and language and node_dict.get('language') != language:
                    match = False

                # File pattern filter
                if match and file_pattern:
                    file_path = node_dict.get('file', '')
                    if not fnmatch.fnmatch(file_path, file_pattern):
                        match = False

                # Text query filter
                if match and query:
                    query_lower = query.lower()
                    summary = str(node_dict.get('summary', '') or '').lower()
                    file_path = str(node_dict.get('file', '') or '').lower()
                    node_str = f"{node_id} {summary} {file_path}".lower()
                    if query_lower not in node_str:
                        match = False

                if match:
                    results.append({"id": node_id, **node_dict})

            return {
                "count": len(results),
                "results": results[:limit],
                "filters": {
                    "query": query,
                    "node_type": node_type,
                    "language": language,
                    "file_pattern": file_pattern,
                },
            }
        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}

    def dependencies(self, node_id: str, direction: str = "both", depth: int = 1) -> Dict[str, Any]:
        """
        Get dependency graph for a node.

        Args:
            node_id: Node ID to get dependencies for
            direction: "incoming", "outgoing", or "both"
            depth: Maximum depth to traverse (1 = direct dependencies only)

        Returns:
            Dependency graph
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        try:
            if node_id not in genome.nodes:
                return {"error": f"Node not found: {node_id}"}

            def get_dependencies(current_id: str, current_depth: int, visited: set) -> Dict[str, Any]:
                if current_depth > depth or current_id in visited:
                    return {}
                
                visited.add(current_id)
                deps = {"id": current_id, "dependencies": []}

                if direction in ("outgoing", "both"):
                    for edge in genome.edges:
                        if edge.from_ == current_id:
                            dep_info = get_dependencies(edge.to, current_depth + 1, visited.copy())
                            deps["dependencies"].append({
                                "node": edge.to,
                                "type": edge.type if hasattr(edge, 'type') else None,
                                "dependencies": dep_info.get("dependencies", []),
                            })

                if direction in ("incoming", "both"):
                    for edge in genome.edges:
                        if edge.to == current_id:
                            dep_info = get_dependencies(edge.from_, current_depth + 1, visited.copy())
                            deps["dependencies"].append({
                                "node": edge.from_,
                                "type": edge.type if hasattr(edge, 'type') else None,
                                "dependencies": dep_info.get("dependencies", []),
                            })

                return deps

            graph = get_dependencies(node_id, 0, set())
            return {
                "node_id": node_id,
                "direction": direction,
                "depth": depth,
                "graph": graph,
            }
        except Exception as e:
            return {"error": f"Failed to get dependencies: {str(e)}"}

    def stats(self) -> Dict[str, Any]:
        """
        Get repository statistics and metrics.

        Returns:
            Repository statistics
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        try:
            # Count nodes by type
            nodes_by_type: Dict[str, int] = {}
            nodes_by_language: Dict[str, int] = {}
            files_count = 0

            for node_id, node_data in genome.nodes.items():
                # Convert to dict
                if hasattr(node_data, 'model_dump'):
                    node_dict = node_data.model_dump()
                elif hasattr(node_data, 'dict'):
                    node_dict = node_data.dict()
                else:
                    node_dict = node_data if isinstance(node_data, dict) else {}

                node_type = node_dict.get('type', 'unknown')
                nodes_by_type[node_type] = nodes_by_type.get(node_type, 0) + 1

                if node_type == 'file':
                    files_count += 1

                language = node_dict.get('language')
                if language:
                    nodes_by_language[language] = nodes_by_language.get(language, 0) + 1

            # Count edges by type
            edges_by_type: Dict[str, int] = {}
            for edge in genome.edges:
                edge_type = edge.type if hasattr(edge, 'type') else 'unknown'
                edges_by_type[edge_type] = edges_by_type.get(edge_type, 0) + 1

            # Calculate average criticality
            total_criticality = 0.0
            criticality_count = 0
            for node_id, node_data in genome.nodes.items():
                if hasattr(node_data, 'model_dump'):
                    node_dict = node_data.model_dump()
                elif hasattr(node_data, 'dict'):
                    node_dict = node_data.dict()
                else:
                    node_dict = node_data if isinstance(node_data, dict) else {}
                
                criticality = node_dict.get('criticality', 0.0)
                if criticality > 0:
                    total_criticality += criticality
                    criticality_count += 1

            avg_criticality = total_criticality / criticality_count if criticality_count > 0 else 0.0

            return {
                "total_nodes": len(genome.nodes),
                "total_edges": len(genome.edges),
                "total_files": files_count,
                "total_flows": len(genome.flows),
                "total_concepts": len(genome.concepts),
                "total_contracts": len(genome.contracts),
                "nodes_by_type": nodes_by_type,
                "nodes_by_language": nodes_by_language,
                "edges_by_type": edges_by_type,
                "average_criticality": avg_criticality,
                "entry_points": len(genome.summary.entry_points) if genome.summary else 0,
            }
        except Exception as e:
            return {"error": f"Failed to get stats: {str(e)}"}

    def export(self, format: str = "json", output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export genome to different formats via MCP.

        Args:
            format: Export format ("json", "graphml", "dot", "csv")
            output_path: Optional output path (default: genome location with format extension)

        Returns:
            Export result
        """
        genome = self.storage.load_genome()
        if genome is None:
            return {"error": "No genome found. Run repogenome.scan first."}

        try:
            from pathlib import Path

            # Determine output path
            if output_path is None:
                output_path = str(self.storage.genome_path.with_suffix(f".{format}"))
            else:
                output_path = str(Path(output_path))

            format_lower = format.lower()

            if format_lower == "json":
                genome.save(output_path)
            elif format_lower == "graphml":
                from repogenome.export.graphml import export_graphml
                export_graphml(genome, Path(output_path))
            elif format_lower == "dot":
                from repogenome.export.dot import export_dot
                export_dot(genome, Path(output_path))
            elif format_lower == "csv":
                # CSV export (new feature)
                self._export_csv(genome, Path(output_path))
            elif format_lower == "cypher":
                from repogenome.export.cypher import export_cypher
                export_cypher(genome, Path(output_path))
            elif format_lower == "plantuml":
                from repogenome.export.plantuml import export_plantuml
                export_plantuml(genome, Path(output_path))
            else:
                return {"error": f"Unsupported format: {format}"}

            return {
                "success": True,
                "format": format,
                "output_path": output_path,
                "message": f"Genome exported to {format} format",
            }
        except Exception as e:
            return {"error": f"Export failed: {str(e)}"}

    def _export_csv(self, genome: "RepoGenome", output_path: Path) -> None:
        """Export genome to CSV format."""
        import csv

        # Export nodes
        nodes_path = output_path.with_suffix('.nodes.csv')
        with open(nodes_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'type', 'file', 'language', 'visibility', 'summary', 'criticality'])
            
            for node_id, node_data in genome.nodes.items():
                if hasattr(node_data, 'model_dump'):
                    node_dict = node_data.model_dump()
                elif hasattr(node_data, 'dict'):
                    node_dict = node_data.dict()
                else:
                    node_dict = node_data if isinstance(node_data, dict) else {}
                
                writer.writerow([
                    node_id,
                    node_dict.get('type', ''),
                    node_dict.get('file', ''),
                    node_dict.get('language', ''),
                    node_dict.get('visibility', ''),
                    node_dict.get('summary', '') or '',
                    node_dict.get('criticality', 0.0),
                ])

        # Export edges
        edges_path = output_path.with_suffix('.edges.csv')
        with open(edges_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['from', 'to', 'type'])
            
            for edge in genome.edges:
                writer.writerow([
                    edge.from_,
                    edge.to,
                    edge.type if hasattr(edge, 'type') else '',
                ])

