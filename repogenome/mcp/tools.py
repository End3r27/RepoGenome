"""MCP tool implementations for RepoGenome."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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
            from repogenome.core.errors import format_error
            return {
                "success": False,
                **format_error(
                    f"Scan failed: {str(e)}",
                    "Check repository path and permissions",
                    exception=e,
                )
            }

    def query(
        self,
        query: str,
        format: str = "json",
        page: int = 1,
        page_size: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        fields: Optional[Union[str, List[str]]] = None,
        ids_only: bool = False,
        max_summary_length: Optional[int] = None,
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
            fields: Field selection (None = all fields, "*" = all fields, list = specific fields)
            ids_only: If True, return only node IDs (minimal context)
            max_summary_length: Maximum length for summaries (None = use config default)

        Returns:
            Query results with pagination
        """
        from repogenome.utils.field_filter import filter_fields
        from repogenome.core.config import RepoGenomeConfig
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )

        # Get max_summary_length from config if not provided
        if max_summary_length is None:
            config = RepoGenomeConfig.load()
            max_summary_length = config.max_summary_length

        # Check cache (include new parameters in cache key)
        if use_cache:
            cache_key = f"{query}:{format}:{page}:{page_size}:{str(filters)}:{str(fields)}:{ids_only}:{max_summary_length}"
            if cache_key in self._query_cache:
                cached_data, cached_time, is_compressed = self._query_cache[cache_key]
                if time.time() - cached_time < self._cache_ttl:
                    # Decompress if needed
                    if is_compressed:
                        import json
                        import gzip
                        decompressed = gzip.decompress(cached_data)
                        return json.loads(decompressed.decode('utf-8'))
                    return cached_data
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
                    
                    # Handle ids_only mode
                    if ids_only:
                        result = {
                            "type": "nodes",
                            "count": total_count,
                            "page": page,
                            "page_size": page_size,
                            "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
                            "ids": [node_id for node_id, _ in paginated_results],
                        }
                    else:
                        # Process results with field selection and summary truncation
                        processed_results = []
                        for node_id, node_data in paginated_results:
                            # Convert to dict
                            if hasattr(node_data, 'model_dump'):
                                node_dict = node_data.model_dump()
                            elif hasattr(node_data, 'dict'):
                                node_dict = node_data.dict()
                            else:
                                node_dict = node_data if isinstance(node_data, dict) else {}
                            
                            # Truncate summary if needed
                            if max_summary_length and "summary" in node_dict and node_dict.get("summary"):
                                summary = node_dict["summary"]
                                if len(summary) > max_summary_length:
                                    # Truncate at word boundary if possible
                                    truncated = summary[:max_summary_length - 3]
                                    last_space = truncated.rfind(" ")
                                    if last_space > max_summary_length * 0.8:  # Only if we keep most of the text
                                        truncated = truncated[:last_space]
                                    node_dict["summary"] = truncated + "..."
                            
                            # Apply field filtering
                            if fields:
                                node_dict = filter_fields({"id": node_id, **node_dict}, fields, context="node")
                            else:
                                node_dict = {"id": node_id, **node_dict}
                            
                            processed_results.append(node_dict)
                        
                        result = {
                            "type": "nodes",
                            "count": total_count,
                            "page": page,
                            "page_size": page_size,
                            "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
                            "results": processed_results,
                        }
                    
                    # Cache result with compression for large results
                    if use_cache:
                        cache_key = f"{query}:{format}:{page}:{page_size}:{str(filters)}:{str(fields)}:{ids_only}:{max_summary_length}"
                        import json
                        import gzip
                        result_json = json.dumps(result).encode('utf-8')
                        if len(result_json) > 10240:  # 10KB
                            compressed = gzip.compress(result_json)
                            self._query_cache[cache_key] = (compressed, time.time(), True)
                        else:
                            self._query_cache[cache_key] = (result, time.time(), False)
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
                        # Truncate summary if needed
                        if max_summary_length and summary and len(summary) > max_summary_length:
                            truncated = summary[:max_summary_length - 3]
                            last_space = truncated.rfind(" ")
                            if last_space > max_summary_length * 0.8:
                                truncated = truncated[:last_space]
                            node_dict["summary"] = truncated + "..."
                        
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

                # Handle ids_only mode
                if ids_only:
                    result = {
                        "type": "search",
                        "query": query,
                        "count": total_count,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
                        "ids": [item["id"] for item in paginated_results],
                    }
                else:
                    # Apply field filtering if specified
                    if fields:
                        paginated_results = [
                            filter_fields(item, fields, context="node")
                            for item in paginated_results
                        ]
                    
                    result = {
                        "type": "search",
                        "query": query,
                        "count": total_count,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
                        "results": paginated_results,
                    }
                
                # Cache result with compression for large results
                if use_cache:
                    cache_key = f"{query}:{format}:{page}:{page_size}:{str(filters)}:{str(fields)}:{ids_only}:{max_summary_length}"
                    import json
                    import gzip
                    result_json = json.dumps(result).encode('utf-8')
                    if len(result_json) > 10240:  # 10KB
                        compressed = gzip.compress(result_json)
                        self._query_cache[cache_key] = (compressed, time.time(), True)
                    else:
                        self._query_cache[cache_key] = (result, time.time(), False)
                    # Limit cache size
                    if len(self._query_cache) > 100:
                        # Remove oldest entries
                        sorted_cache = sorted(self._query_cache.items(), key=lambda x: x[1][1])
                        for key, _ in sorted_cache[:20]:
                            del self._query_cache[key]
                
                return result
        except Exception as e:
            from repogenome.core.errors import format_error
            return format_error(
                f"Query failed: {str(e)}",
                "Check query syntax and try again",
                exception=e,
            )

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
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )

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
            from repogenome.core.errors import format_error
            return format_error(
                f"Impact analysis failed: {str(e)}",
                "Verify node IDs and try again",
                exception=e,
            )

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
            from repogenome.core.errors import format_error
            return format_error(
                f"Update failed: {str(e)}",
                "Check genome file and try again",
                exception=e,
            )

    def validate(self) -> Dict[str, Any]:
        """
        Validate RepoGenome consistency with repository.

        Returns:
            Validation result
        """
        genome = self.storage.load_genome()
        if genome is None:
            from repogenome.core.errors import format_error
            return format_error(
                "No genome found",
                "Run repogenome.scan to generate genome",
            )

        # Check if stale
        if self.storage.is_stale():
            from repogenome.core.errors import format_error
            return format_error(
                "Genome is stale (repo hash mismatch)",
                "Run repogenome.scan to regenerate",
            )

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
            from repogenome.core.errors import format_error
            return format_error(
                "Genome has consistency issues",
                "Run repogenome.scan to regenerate",
                details={"issues": issues},
            )

        from repogenome.core.errors import format_error
        return {
            "valid": True,
            "message": "Genome is valid and up-to-date",
            "nodes": len(genome.nodes),
            "edges": len(genome.edges),
        }

    def get_node(
        self,
        node_id: str,
        max_depth: int = 1,
        fields: Optional[Union[str, List[str]]] = None,
        include_edges: bool = True,
        edge_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific node.

        Args:
            node_id: Node ID to retrieve
            max_depth: Maximum depth for relationships (0 = node only, 1 = direct only)
            fields: Field selection (None = all fields)
            include_edges: Whether to include edge information (default: True)
            edge_types: Filter edges by type (None = all types)

        Returns:
            Node details with relationships
        """
        from repogenome.utils.field_filter import filter_fields
        
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )

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

            result: Dict[str, Any] = {"node": node_dict}

            # Get edges if requested and depth > 0
            if include_edges and max_depth > 0:
                # Get incoming edges
                incoming_edges = []
                for edge in genome.edges:
                    if edge.to == node_id:
                        edge_type = edge.type.value if hasattr(edge.type, 'value') else str(edge.type)
                        if edge_types is None or edge_type in edge_types:
                            incoming_edges.append({
                                "from": edge.from_,
                                "to": edge.to,
                                "type": edge_type,
                            })

                # Get outgoing edges
                outgoing_edges = []
                for edge in genome.edges:
                    if edge.from_ == node_id:
                        edge_type = edge.type.value if hasattr(edge.type, 'value') else str(edge.type)
                        if edge_types is None or edge_type in edge_types:
                            outgoing_edges.append({
                                "from": edge.from_,
                                "to": edge.to,
                                "type": edge_type,
                            })

                result["incoming_edges"] = incoming_edges
                result["outgoing_edges"] = outgoing_edges
                result["incoming_count"] = len(incoming_edges)
                result["outgoing_count"] = len(outgoing_edges)

            # Get risk information
            if node_id in genome.risk:
                risk = genome.risk[node_id]
                if hasattr(risk, 'model_dump'):
                    risk_data = risk.model_dump()
                elif hasattr(risk, 'dict'):
                    risk_data = risk.dict()
                else:
                    risk_data = risk if isinstance(risk, dict) else None
                result["risk"] = risk_data

            # Apply field filtering if specified
            if fields:
                result = filter_fields(result, fields, context="node")

            return result
        except Exception as e:
            from repogenome.core.errors import format_error
            return format_error(
                f"Failed to get node: {str(e)}",
                "Verify node ID and try again",
                exception=e,
            )

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
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )

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
            from repogenome.core.errors import format_error
            return format_error(
                f"Search failed: {str(e)}",
                "Check search parameters and try again",
                exception=e,
            )

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
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )

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
            from repogenome.core.errors import format_error
            return format_error(
                f"Failed to get dependencies: {str(e)}",
                "Verify node ID and try again",
                exception=e,
            )

    def stats(self) -> Dict[str, Any]:
        """
        Get repository statistics and metrics.

        Returns:
            Repository statistics
        """
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )

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
            from repogenome.core.errors import format_error
            return format_error(
                f"Failed to get stats: {str(e)}",
                "Check genome file and try again",
                exception=e,
            )

    def export(self, format: str = "json", output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export genome to different formats via MCP.

        Args:
            format: Export format ("json", "graphml", "dot", "csv")
            output_path: Optional output path (default: genome location with format extension)

        Returns:
            Export result
        """
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )

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
            from repogenome.core.errors import format_error
            return format_error(
                f"Export failed: {str(e)}",
                "Check format and output path",
                exception=e,
            )

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

