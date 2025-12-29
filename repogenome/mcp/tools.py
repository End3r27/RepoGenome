"""MCP tool implementations for RepoGenome."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from repogenome.core.generator import RepoGenomeGenerator
from repogenome.core.query import GenomeQuery, parse_simple_query
from repogenome.core.schema import RepoGenome
from repogenome.mcp.storage import GenomeStorage


def _validate_node_id(node_id: str, genome: RepoGenome) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate that a node ID exists in the genome.
    
    Args:
        node_id: Node ID to validate
        genome: RepoGenome instance
        
    Returns:
        Tuple of (is_valid, error_dict if invalid)
    """
    if not node_id or not isinstance(node_id, str):
        return False, {
            "error": "Invalid node ID",
            "reason": "Node ID must be a non-empty string",
            "action": "Provide a valid node ID string"
        }
    
    if node_id not in genome.nodes:
        # Try to find similar node IDs
        suggestions = _find_similar_node_ids(node_id, genome, max_suggestions=5)
        error_msg = {
            "error": f"Node not found: {node_id}",
            "action": "Use repogenome.query or repogenome.search to find valid node IDs"
        }
        if suggestions:
            error_msg["suggestions"] = suggestions
            error_msg["hint"] = f"Did you mean one of: {', '.join(suggestions[:3])}?"
        return False, error_msg
    
    return True, None


def _find_similar_node_ids(node_id: str, genome: RepoGenome, max_suggestions: int = 5) -> List[str]:
    """
    Find similar node IDs using simple string matching.
    
    Args:
        node_id: The node ID to find similarities for
        genome: RepoGenome instance
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        List of similar node IDs
    """
    import difflib
    
    node_id_lower = node_id.lower()
    candidate_ids = list(genome.nodes.keys())
    
    # Calculate similarity scores
    similarities = []
    for candidate_id in candidate_ids:
        # Use SequenceMatcher for similarity
        similarity = difflib.SequenceMatcher(None, node_id_lower, candidate_id.lower()).ratio()
        
        # Boost score if one contains the other
        if node_id_lower in candidate_id.lower() or candidate_id.lower() in node_id_lower:
            similarity += 0.3
        
        # Boost score if they share common substrings
        if len(node_id) > 3:
            common = sum(1 for i in range(len(node_id_lower) - 2) 
                        if node_id_lower[i:i+3] in candidate_id.lower())
            similarity += common * 0.1
        
        similarities.append((candidate_id, similarity))
    
    # Sort by similarity and return top matches
    similarities.sort(key=lambda x: x[1], reverse=True)
    return [node_id for node_id, score in similarities[:max_suggestions] if score > 0.3]


def _validate_pagination(page: int, page_size: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate pagination parameters."""
    if page < 1:
        return False, {
            "error": "Invalid page number",
            "reason": f"Page must be >= 1, got {page}",
            "action": "Use page >= 1"
        }
    
    if page_size < 1 or page_size > 1000:
        return False, {
            "error": "Invalid page size",
            "reason": f"Page size must be between 1 and 1000, got {page_size}",
            "action": "Use page_size between 1 and 1000"
        }
    
    return True, None


def _validate_depth(depth: int, max_depth: int = 10) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate depth parameter."""
    if depth < 0:
        return False, {
            "error": "Invalid depth",
            "reason": f"Depth must be >= 0, got {depth}",
            "action": "Use depth >= 0"
        }
    
    if depth > max_depth:
        return False, {
            "error": "Invalid depth",
            "reason": f"Depth must be <= {max_depth}, got {depth}",
            "action": f"Use depth <= {max_depth} for performance"
        }
    
    return True, None


def _validate_direction(direction: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate direction parameter."""
    valid_directions = ["incoming", "outgoing", "both"]
    if direction not in valid_directions:
        return False, {
            "error": "Invalid direction",
            "reason": f"Direction must be one of {valid_directions}, got {direction}",
            "action": f"Use one of: {', '.join(valid_directions)}"
        }
    
    return True, None


def _validate_scope(scope: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate scan scope parameter."""
    valid_scopes = ["full", "structure", "flows", "history"]
    if scope not in valid_scopes:
        return False, {
            "error": "Invalid scope",
            "reason": f"Scope must be one of {valid_scopes}, got {scope}",
            "action": f"Use one of: {', '.join(valid_scopes)}"
        }
    
    return True, None


def _validate_operation(operation: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate operation parameter."""
    valid_operations = ["modify", "delete", "add"]
    if operation not in valid_operations:
        return False, {
            "error": "Invalid operation",
            "reason": f"Operation must be one of {valid_operations}, got {operation}",
            "action": f"Use one of: {', '.join(valid_operations)}"
        }
    
    return True, None


def _validate_export_format(format: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate export format parameter."""
    valid_formats = ["json", "graphml", "dot", "csv", "cypher", "plantuml"]
    if format not in valid_formats:
        return False, {
            "error": "Invalid export format",
            "reason": f"Format must be one of {valid_formats}, got {format}",
            "action": f"Use one of: {', '.join(valid_formats)}"
        }
    
    return True, None


def _validate_limit(limit: int, max_limit: int = 1000) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Validate limit parameter."""
    if limit < 1:
        return False, {
            "error": "Invalid limit",
            "reason": f"Limit must be >= 1, got {limit}",
            "action": "Use limit >= 1"
        }
    
    if limit > max_limit:
        return False, {
            "error": "Invalid limit",
            "reason": f"Limit must be <= {max_limit}, got {limit}",
            "action": f"Use limit <= {max_limit} for performance"
        }
    
    return True, None


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
        self._query_cache: Dict[str, Tuple[Any, float, bool]] = {}
        self._cache_ttl: float = 300.0  # 5 minutes
        self._cache_stats: Dict[str, Any] = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0,
        }

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
        from repogenome.core.errors import format_error
        
        # Validate scope
        is_valid, error = _validate_scope(scope)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
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

        # Validate pagination parameters
        is_valid, error = _validate_pagination(page, page_size)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        # Validate max_summary_length if provided
        if max_summary_length is not None and max_summary_length < 0:
            return format_error(
                "Invalid max_summary_length",
                "max_summary_length must be >= 0",
                details={"value": max_summary_length}
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
                current_time = time.time()
                if current_time - cached_time < self._cache_ttl:
                    # Cache hit - update access time for LRU
                    if is_compressed:
                        import json
                        import gzip
                        decompressed = gzip.decompress(cached_data)
                        self._cache_stats["hits"] += 1
                        return json.loads(decompressed.decode('utf-8'))
                    # Update access time
                    self._query_cache[cache_key] = (cached_data, current_time, False)
                    self._cache_stats["hits"] += 1
                    return cached_data
                else:
                    # Remove expired cache entry
                    del self._query_cache[cache_key]
                    self._cache_stats["size"] = len(self._query_cache)
            
            self._cache_stats["misses"] += 1

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
                        
                        # Add query suggestions if no results
                        if total_count == 0:
                            result["suggestions"] = {
                                "hint": "No results found. Try:",
                                "options": [
                                    "Use more general search terms",
                                    "Check spelling and typos",
                                    "Try different field filters",
                                    "Use repogenome.search for fuzzy matching",
                                    "Use repogenome.filter for advanced filtering"
                                ]
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
                        self._cache_stats["size"] = len(self._query_cache)
                        
                        # Smarter cache eviction: limit cache size with LRU
                        max_cache_size = 100
                        if len(self._query_cache) > max_cache_size:
                            # Remove oldest entries (LRU eviction)
                            sorted_cache = sorted(self._query_cache.items(), key=lambda x: x[1][1])
                            evict_count = len(self._query_cache) - max_cache_size + 20  # Evict 20 extra to reduce churn
                            for key, _ in sorted_cache[:evict_count]:
                                del self._query_cache[key]
                                self._cache_stats["evictions"] += 1
                            self._cache_stats["size"] = len(self._query_cache)
                    
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
                    
                    # Add query suggestions if no results
                    if total_count == 0:
                        result["suggestions"] = {
                            "hint": "No results found. Try:",
                            "options": [
                                "Use more general search terms",
                                "Check spelling and typos",
                                "Try removing filters",
                                "Use repogenome.search for better text matching",
                                "Use repogenome.filter for advanced filtering"
                            ]
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
                    self._cache_stats["size"] = len(self._query_cache)
                    
                    # Smarter cache eviction: limit cache size with LRU
                    max_cache_size = 100
                    if len(self._query_cache) > max_cache_size:
                        # Remove oldest entries (LRU eviction)
                        sorted_cache = sorted(self._query_cache.items(), key=lambda x: x[1][1])
                        evict_count = len(self._query_cache) - max_cache_size + 20  # Evict 20 extra to reduce churn
                        for key, _ in sorted_cache[:evict_count]:
                            del self._query_cache[key]
                            self._cache_stats["evictions"] += 1
                        self._cache_stats["size"] = len(self._query_cache)
                
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

        # Validate operation
        is_valid, error = _validate_operation(operation)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        # Validate affected_nodes
        if not affected_nodes or not isinstance(affected_nodes, list):
            return format_error(
                "Invalid affected_nodes",
                "affected_nodes must be a non-empty list of node IDs",
                details={"value": affected_nodes}
            )
        
        # Validate all node IDs exist
        invalid_nodes = []
        for node_id in affected_nodes:
            if not isinstance(node_id, str):
                invalid_nodes.append(f"{node_id} (not a string)")
            elif node_id not in genome.nodes:
                invalid_nodes.append(node_id)
        
        if invalid_nodes:
            suggestions = {}
            for node_id in invalid_nodes[:5]:  # Limit suggestions
                if isinstance(node_id, str):
                    similar = _find_similar_node_ids(node_id, genome, max_suggestions=3)
                    if similar:
                        suggestions[node_id] = similar
            
            return format_error(
                f"Invalid node IDs in affected_nodes: {len(invalid_nodes)} node(s) not found",
                "All node IDs in affected_nodes must exist in the genome",
                details={
                    "invalid_nodes": invalid_nodes[:10],  # Limit error details
                    "suggestions": suggestions
                }
            )
        
        try:
            affected_flows = []
            affected_contracts = []
            total_risk = 0.0
            max_risk = 0.0

            for node_id in affected_nodes:

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

        # Validate node_id
        is_valid, error = _validate_node_id(node_id, genome)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        # Validate max_depth
        is_valid, error = _validate_depth(max_depth, max_depth=10)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        try:

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

        # Validate limit
        is_valid, error = _validate_limit(limit, max_limit=1000)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        try:
            import fnmatch
            import difflib
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
                score = 0.0

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

                # Text query filter with scoring
                if match and query:
                    query_lower = query.lower()
                    summary = str(node_dict.get('summary', '') or '').lower()
                    file_path = str(node_dict.get('file', '') or '').lower()
                    node_id_lower = node_id.lower()
                    node_type_str = str(node_dict.get('type', '') or '').lower()
                    
                    # Calculate relevance score
                    # Exact match in node ID gets highest score
                    if query_lower == node_id_lower:
                        score += 100.0
                    elif query_lower in node_id_lower:
                        score += 50.0
                    else:
                        # Use sequence matcher for fuzzy matching
                        similarity = difflib.SequenceMatcher(None, query_lower, node_id_lower).ratio()
                        score += similarity * 30.0
                    
                    # Match in summary
                    if query_lower in summary:
                        score += 20.0
                        # Boost if at start of summary
                        if summary.startswith(query_lower):
                            score += 10.0
                    else:
                        # Fuzzy match in summary
                        similarity = difflib.SequenceMatcher(None, query_lower, summary[:len(query_lower) * 2]).ratio()
                        score += similarity * 10.0
                    
                    # Match in file path
                    if query_lower in file_path:
                        score += 15.0
                        # Boost if in filename
                        if '/' in file_path:
                            filename = file_path.split('/')[-1]
                            if query_lower in filename.lower():
                                score += 10.0
                    
                    # Match in type
                    if query_lower in node_type_str:
                        score += 5.0
                    
                    # Only include if there's some match
                    if score < 0.1:
                        match = False

                if match:
                    results.append({
                        "id": node_id,
                        "score": round(score, 2),
                        **node_dict
                    })

            # Sort by score (descending)
            results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            
            # Add search suggestions if no results
            suggestions = None
            if len(results) == 0 and query:
                # Try to find similar node IDs
                similar_nodes = _find_similar_node_ids(query, genome, max_suggestions=5)
                if similar_nodes:
                    suggestions = {
                        "hint": "No exact matches found. Did you mean:",
                        "similar_nodes": similar_nodes,
                        "options": [
                            "Try a more general search term",
                            "Check spelling",
                            "Use repogenome.query for structured queries",
                            "Use repogenome.filter for advanced filtering"
                        ]
                    }

            return {
                "count": len(results),
                "results": results[:limit],
                "filters": {
                    "query": query,
                    "node_type": node_type,
                    "language": language,
                    "file_pattern": file_pattern,
                },
                "suggestions": suggestions,
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

        # Validate node_id
        is_valid, error = _validate_node_id(node_id, genome)
        if not is_valid:
            return format_error(**error)
        
        # Validate direction
        is_valid, error = _validate_direction(direction)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        # Validate depth
        is_valid, error = _validate_depth(depth, max_depth=10)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        try:
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
            format: Export format ("json", "graphml", "dot", "csv", "cypher", "plantuml")
            output_path: Optional output path (default: genome location with format extension)

        Returns:
            Export result
        """
        from repogenome.core.errors import format_error
        
        # Validate format
        is_valid, error = _validate_export_format(format)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
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

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get query cache statistics.
        
        Returns:
            Cache statistics dictionary
        """
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "hit_rate": round(hit_rate, 2),
            "evictions": self._cache_stats["evictions"],
            "current_size": self._cache_stats["size"],
            "max_size": 100,
            "ttl_seconds": self._cache_ttl,
        }
    
    def clear_cache(self) -> Dict[str, Any]:
        """
        Clear the query cache.
        
        Returns:
            Result dictionary
        """
        old_size = len(self._query_cache)
        self._query_cache.clear()
        self._cache_stats["size"] = 0
        return {
            "success": True,
            "cleared_entries": old_size,
            "message": f"Cleared {old_size} cache entries",
        }

    def batch_get_nodes(
        self,
        node_ids: List[str],
        fields: Optional[Union[str, List[str]]] = None,
        include_edges: bool = False,
    ) -> Dict[str, Any]:
        """
        Get multiple nodes in a single call.
        
        Args:
            node_ids: List of node IDs to retrieve
            fields: Field selection (None = all fields)
            include_edges: Whether to include edge information
            
        Returns:
            Dictionary with nodes and any errors
        """
        from repogenome.utils.field_filter import filter_fields
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )
        
        # Validate input
        if not node_ids or not isinstance(node_ids, list):
            return format_error(
                "Invalid node_ids",
                "node_ids must be a non-empty list",
                details={"value": node_ids}
            )
        
        if len(node_ids) > 100:
            return format_error(
                "Too many node IDs",
                "Maximum 100 node IDs allowed per batch request",
                details={"count": len(node_ids), "limit": 100}
            )
        
        try:
            nodes = {}
            errors = {}
            not_found = []
            
            for node_id in node_ids:
                if not isinstance(node_id, str):
                    errors[node_id] = "Node ID must be a string"
                    continue
                
                if node_id not in genome.nodes:
                    not_found.append(node_id)
                    continue
                
                node = genome.nodes[node_id]
                
                # Convert to dict
                if hasattr(node, 'model_dump'):
                    node_dict = node.model_dump()
                elif hasattr(node, 'dict'):
                    node_dict = node.dict()
                else:
                    node_dict = node if isinstance(node, dict) else {}
                
                # Get edges if requested
                if include_edges:
                    incoming_edges = []
                    outgoing_edges = []
                    for edge in genome.edges:
                        if edge.to == node_id:
                            edge_type = edge.type.value if hasattr(edge.type, 'value') else str(edge.type)
                            incoming_edges.append({
                                "from": edge.from_,
                                "to": edge.to,
                                "type": edge_type,
                            })
                        if edge.from_ == node_id:
                            edge_type = edge.type.value if hasattr(edge.type, 'value') else str(edge.type)
                            outgoing_edges.append({
                                "from": edge.from_,
                                "to": edge.to,
                                "type": edge_type,
                            })
                    node_dict["incoming_edges"] = incoming_edges
                    node_dict["outgoing_edges"] = outgoing_edges
                
                # Apply field filtering
                if fields:
                    node_dict = filter_fields({"id": node_id, **node_dict}, fields, context="node")
                else:
                    node_dict = {"id": node_id, **node_dict}
                
                nodes[node_id] = node_dict
            
            result: Dict[str, Any] = {
                "nodes": nodes,
                "count": len(nodes),
                "total_requested": len(node_ids),
            }
            
            if not_found:
                # Try to find suggestions for not found nodes
                suggestions = {}
                for node_id in not_found[:10]:  # Limit suggestions
                    similar = _find_similar_node_ids(node_id, genome, max_suggestions=3)
                    if similar:
                        suggestions[node_id] = similar
                
                result["not_found"] = not_found
                result["suggestions"] = suggestions
                result["errors"] = {
                    "message": f"{len(not_found)} node(s) not found",
                    "hint": "Use suggestions to find similar node IDs"
                }
            
            if errors:
                result["errors"] = result.get("errors", {})
                result["errors"]["validation_errors"] = errors
            
            return result
        except Exception as e:
            return format_error(
                f"Batch get nodes failed: {str(e)}",
                "Verify node IDs and try again",
                exception=e,
            )
    
    def batch_dependencies(
        self,
        node_ids: List[str],
        direction: str = "both",
        depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Get dependencies for multiple nodes in a single call.
        
        Args:
            node_ids: List of node IDs to get dependencies for
            direction: "incoming", "outgoing", or "both"
            depth: Maximum depth to traverse
            
        Returns:
            Dictionary with dependency graphs for each node
        """
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )
        
        # Validate input
        if not node_ids or not isinstance(node_ids, list):
            return format_error(
                "Invalid node_ids",
                "node_ids must be a non-empty list",
            )
        
        if len(node_ids) > 50:
            return format_error(
                "Too many node IDs",
                "Maximum 50 node IDs allowed per batch request",
                details={"count": len(node_ids), "limit": 50}
            )
        
        # Validate direction and depth
        is_valid, error = _validate_direction(direction)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        is_valid, error = _validate_depth(depth, max_depth=5)  # Lower max for batch
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        try:
            results = {}
            not_found = []
            
            for node_id in node_ids:
                if node_id not in genome.nodes:
                    not_found.append(node_id)
                    continue
                
                # Reuse dependencies logic
                dep_result = self.dependencies(node_id, direction, depth)
                if "error" not in dep_result:
                    results[node_id] = dep_result.get("graph", {})
                else:
                    not_found.append(node_id)
            
            result: Dict[str, Any] = {
                "dependencies": results,
                "count": len(results),
                "total_requested": len(node_ids),
            }
            
            if not_found:
                result["not_found"] = not_found
                result["errors"] = {
                    "message": f"{len(not_found)} node(s) not found or failed",
                }
            
            return result
        except Exception as e:
            return format_error(
                f"Batch dependencies failed: {str(e)}",
                "Verify node IDs and try again",
                exception=e,
            )
    
    def compare(
        self,
        node_id1: str,
        node_id2: Optional[str] = None,
        compare_with_previous: bool = False,
    ) -> Dict[str, Any]:
        """
        Compare two nodes or current genome with previous version.
        
        Args:
            node_id1: First node ID (or only node if comparing with previous)
            node_id2: Second node ID (optional, if None and compare_with_previous=False, returns error)
            compare_with_previous: If True, compare node_id1 with previous genome version
            
        Returns:
            Comparison result showing differences
        """
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )
        
        try:
            if compare_with_previous:
                # Compare node with previous version
                # This would require storing previous genome version, which is not currently implemented
                # For now, return a message suggesting to use genome diff
                return format_error(
                    "Previous version comparison not yet implemented",
                    "Use repogenome.scan with incremental=False to regenerate and compare manually",
                    details={
                        "feature": "compare_with_previous",
                        "status": "not_implemented"
                    }
                )
            
            # Compare two nodes
            if not node_id2:
                return format_error(
                    "Second node ID required",
                    "Provide node_id2 or set compare_with_previous=True",
                )
            
            # Validate both node IDs exist
            is_valid1, error1 = _validate_node_id(node_id1, genome)
            if not is_valid1:
                return format_error(
                    error1.get("error", "Validation failed"),
                    error1.get("action"),
                    error1.get("details")
                )
            
            is_valid2, error2 = _validate_node_id(node_id2, genome)
            if not is_valid2:
                return format_error(
                    error2.get("error", "Validation failed"),
                    error2.get("action"),
                    error2.get("details")
                )
            
            # Get both nodes
            node1 = genome.nodes[node_id1]
            node2 = genome.nodes[node_id2]
            
            # Convert to dicts
            if hasattr(node1, 'model_dump'):
                node1_dict = node1.model_dump()
            elif hasattr(node1, 'dict'):
                node1_dict = node1.dict()
            else:
                node1_dict = node1 if isinstance(node1, dict) else {}
            
            if hasattr(node2, 'model_dump'):
                node2_dict = node2.model_dump()
            elif hasattr(node2, 'dict'):
                node2_dict = node2.dict()
            else:
                node2_dict = node2 if isinstance(node2, dict) else {}
            
            # Compare fields
            differences = {}
            all_keys = set(node1_dict.keys()) | set(node2_dict.keys())
            
            for key in all_keys:
                val1 = node1_dict.get(key)
                val2 = node2_dict.get(key)
                
                if val1 != val2:
                    differences[key] = {
                        "node1": val1,
                        "node2": val2,
                    }
            
            # Compare edges
            edges1_in = [e for e in genome.edges if e.to == node_id1]
            edges1_out = [e for e in genome.edges if e.from_ == node_id1]
            edges2_in = [e for e in genome.edges if e.to == node_id2]
            edges2_out = [e for e in genome.edges if e.from_ == node_id2]
            
            edge_differences = {
                "incoming_count": {
                    "node1": len(edges1_in),
                    "node2": len(edges2_in),
                },
                "outgoing_count": {
                    "node1": len(edges1_out),
                    "node2": len(edges2_out),
                },
            }
            
            return {
                "node1_id": node_id1,
                "node2_id": node_id2,
                "differences": differences,
                "edge_differences": edge_differences,
                "total_differences": len(differences),
            }
        except Exception as e:
            return format_error(
                f"Comparison failed: {str(e)}",
                "Verify node IDs and try again",
                exception=e,
            )
    
    def filter_nodes(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        fields: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Advanced filtering with complex expressions.
        
        Args:
            filters: Filter dictionary with AND/OR/NOT logic, range queries, regex patterns
            limit: Maximum number of results
            fields: Field selection
            
        Returns:
            Filtered nodes
        """
        from repogenome.utils.field_filter import filter_fields
        from repogenome.core.errors import format_error
        import re
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )
        
        # Validate limit
        is_valid, error = _validate_limit(limit, max_limit=1000)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        try:
            results = []
            
            for node_id, node_data in genome.nodes.items():
                # Convert to dict
                if hasattr(node_data, 'model_dump'):
                    node_dict = node_data.model_dump()
                elif hasattr(node_data, 'dict'):
                    node_dict = node_data.dict()
                else:
                    node_dict = node_data if isinstance(node_data, dict) else {}
                
                # Apply filters with AND/OR/NOT logic
                if self._match_advanced_filters(node_dict, filters):
                    # Apply field filtering
                    if fields:
                        node_dict = filter_fields({"id": node_id, **node_dict}, fields, context="node")
                    else:
                        node_dict = {"id": node_id, **node_dict}
                    
                    results.append(node_dict)
                    
                    if len(results) >= limit:
                        break
            
            return {
                "count": len(results),
                "results": results,
                "filters_applied": filters,
            }
        except Exception as e:
            return format_error(
                f"Filter failed: {str(e)}",
                "Check filter syntax and try again",
                exception=e,
            )
    
    def _match_advanced_filters(self, node_dict: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Match node against advanced filter expressions.
        
        Supports:
        - AND/OR/NOT logic
        - Range queries (__gt, __gte, __lt, __lte)
        - Regex patterns (__regex)
        - In operator (__in)
        """
        # Handle AND logic
        if "and" in filters:
            for filter_item in filters["and"]:
                if not self._match_advanced_filters(node_dict, filter_item):
                    return False
            return True
        
        # Handle OR logic
        if "or" in filters:
            for filter_item in filters["or"]:
                if self._match_advanced_filters(node_dict, filter_item):
                    return True
            return False
        
        # Handle NOT logic
        if "not" in filters:
            return not self._match_advanced_filters(node_dict, filters["not"])
        
        # Handle individual filter conditions
        for key, value in filters.items():
            if key in ["and", "or", "not"]:
                continue  # Already handled
            
            node_value = node_dict.get(key)
            
            # Handle operators
            if "__" in key:
                field, op = key.split("__", 1)
                node_value = node_dict.get(field)
                
                if op == "gt" and not (node_value is not None and node_value > value):
                    return False
                elif op == "gte" and not (node_value is not None and node_value >= value):
                    return False
                elif op == "lt" and not (node_value is not None and node_value < value):
                    return False
                elif op == "lte" and not (node_value is not None and node_value <= value):
                    return False
                elif op == "in" and node_value not in value:
                    return False
                elif op == "regex":
                    if not isinstance(node_value, str) or not re.search(value, str(node_value)):
                        return False
                else:
                    # Unknown operator
                    continue
            else:
                # Simple equality
                if hasattr(node_value, 'value'):
                    node_value = node_value.value
                if str(node_value) != str(value):
                    return False
        
        return True
    
    def find_path(
        self,
        from_node: str,
        to_node: str,
        max_depth: int = 10,
        edge_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Find paths between two nodes.
        
        Args:
            from_node: Source node ID
            to_node: Target node ID
            max_depth: Maximum path length
            edge_types: Optional filter for edge types to consider
            
        Returns:
            Path information (shortest path, all paths, or paths with constraints)
        """
        from repogenome.core.errors import format_error
        
        genome = self.storage.load_genome()
        if genome is None:
            return format_error(
                "No genome found",
                "Run repogenome.scan first",
            )
        
        # Validate node IDs
        is_valid1, error1 = _validate_node_id(from_node, genome)
        if not is_valid1:
            return format_error(
                error1.get("error", "Validation failed"),
                error1.get("action"),
                error1.get("details")
            )
        
        is_valid2, error2 = _validate_node_id(to_node, genome)
        if not is_valid2:
            return format_error(
                error2.get("error", "Validation failed"),
                error2.get("action"),
                error2.get("details")
            )
        
        # Validate depth
        is_valid, error = _validate_depth(max_depth, max_depth=20)
        if not is_valid:
            return format_error(
                error.get("error", "Validation failed"),
                error.get("action"),
                error.get("details")
            )
        
        try:
            # BFS to find shortest path
            from collections import deque
            
            queue = deque([(from_node, [from_node])])
            visited = {from_node}
            paths = []
            
            while queue:
                current, path = queue.popleft()
                
                if len(path) > max_depth:
                    continue
                
                if current == to_node:
                    paths.append(path)
                    # Continue to find all paths (limit to reasonable number)
                    if len(paths) >= 100:
                        break
                    continue
                
                # Explore neighbors
                for edge in genome.edges:
                    if edge.from_ != current:
                        continue
                    
                    # Filter by edge type if specified
                    if edge_types:
                        edge_type = edge.type.value if hasattr(edge.type, 'value') else str(edge.type)
                        if edge_type not in edge_types:
                            continue
                    
                    neighbor = edge.to
                    
                    # Avoid cycles (except allow revisiting if on path to target)
                    if neighbor not in visited or neighbor == to_node:
                        if neighbor not in path:  # Avoid direct cycles
                            visited.add(neighbor)
                            queue.append((neighbor, path + [neighbor]))
            
            if not paths:
                return {
                    "from_node": from_node,
                    "to_node": to_node,
                    "path_found": False,
                    "message": "No path found between nodes",
                }
            
            # Return shortest path and all paths
            shortest_path = min(paths, key=len)
            
            return {
                "from_node": from_node,
                "to_node": to_node,
                "path_found": True,
                "shortest_path": shortest_path,
                "shortest_path_length": len(shortest_path) - 1,
                "all_paths": paths[:10],  # Limit to first 10 paths
                "total_paths_found": len(paths),
            }
        except Exception as e:
            return format_error(
                f"Find path failed: {str(e)}",
                "Verify node IDs and try again",
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

