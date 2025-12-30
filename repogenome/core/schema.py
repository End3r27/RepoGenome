"""
Core schema definitions for RepoGenome JSON structure.

This module defines the complete data model for repogenome.json using Pydantic
for validation and serialization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field

# Field name compression mappings for compact mode
# Using unique short names to avoid conflicts
COMPACT_FIELD_MAP = {
    # Node fields
    "type": "t",
    "file": "f",
    "language": "lang",
    "visibility": "v",
    "summary": "s",
    "criticality": "c",
    # Edge fields
    "from": "fr",
    "to": "to",
    # Flow fields
    "entry": "e",
    "path": "p",
    "side_effects": "se",
    "confidence": "cf",
    # Concept fields
    "nodes": "n",
    "description": "d",
    # History fields
    "churn_score": "cs",
    "last_major_change": "lmc",
    "notes": "nt",
    # Risk fields
    "risk_score": "rs",
    "reasons": "r",
    # Contract fields
    "depends_on": "do",
    "breaking_change_risk": "bcr",
    # Metadata fields
    "generated_at": "ga",
    "repo_hash": "rh",
    "languages": "langs",
    "frameworks": "fw",
    "repogenome_version": "rv",
    # Summary fields
    "entry_points": "ep",
    "architectural_style": "as",
    "core_domains": "cd",
    "hotspots": "hs",
    "do_not_touch": "dnt",
    # Tests fields
    "coverage": "cov",
    "test_files": "tf",
    # GenomeDiff fields
    "added_nodes": "an",
    "removed_nodes": "rn",
    "added_edges": "ae",
    "removed_edges": "re",
    "modified_nodes": "mn",
}

# Reverse mapping for decompression - handle conflicts by checking context
EXPANDED_FIELD_MAP = {v: k for k, v in COMPACT_FIELD_MAP.items()}


def _compress_field_name(field_name: str) -> str:
    """Compress a field name using the mapping."""
    return COMPACT_FIELD_MAP.get(field_name, field_name)


def _expand_field_name(compact_name: str, context: Optional[str] = None) -> str:
    """Expand a compact field name back to full name."""
    # Context-aware expansion for ambiguous mappings
    if compact_name == "t":
        # "t" could be "type" or "to" - check context
        if context == "edge":
            return "to"
        return "type"
    elif compact_name == "f":
        # "f" could be "file" or "from" - check context
        if context == "edge":
            return "from"
        return "file"
    elif compact_name == "n":
        # "n" could be "nodes" or "notes" - check context
        if context == "history":
            return "notes"
        return "nodes"
    elif compact_name == "l":
        # "l" could be "language" or "languages" - check context
        if context == "metadata":
            return "languages"
        return "language"
    
    return EXPANDED_FIELD_MAP.get(compact_name, compact_name)


def _compress_dict(data: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
    """Recursively compress field names in a dictionary."""
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        compressed_key = _compress_field_name(key)
        if isinstance(value, dict):
            result[compressed_key] = _compress_dict(value, context)
        elif isinstance(value, list):
            result[compressed_key] = [
                _compress_dict(item, context) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[compressed_key] = value
    return result


def _expand_dict(data: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
    """Recursively expand field names in a dictionary."""
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        expanded_key = _expand_field_name(key, context)
        if isinstance(value, dict):
            result[expanded_key] = _expand_dict(value, context)
        elif isinstance(value, list):
            result[expanded_key] = [
                _expand_dict(item, context) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[expanded_key] = value
    return result


class SummaryMode(str, Enum):
    """Summary detail levels for context reduction."""

    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"


class NodeType(str, Enum):
    """Types of nodes in the repository graph."""

    FILE = "file"
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    TEST = "test"
    CONFIG = "config"
    RESOURCE = "resource"
    CONCEPT = "concept"


class EdgeType(str, Enum):
    """Types of relationships between nodes."""

    IMPORTS = "imports"
    CALLS = "calls"
    DEFINES = "defines"
    TESTS = "tests"
    CONFIGURES = "configures"
    DEPENDS_ON = "depends_on"
    MUTATES = "mutates"
    EMITS = "emits"
    REFERENCES = "references"


class Metadata(BaseModel):
    """Repository metadata and generation information."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    repo_hash: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    repogenome_version: str = Field(default="0.9.0")


class Summary(BaseModel):
    """High-level summary for agent boot section."""

    entry_points: List[str] = Field(default_factory=list)
    architectural_style: List[str] = Field(default_factory=list)
    core_domains: List[str] = Field(default_factory=list)
    hotspots: List[str] = Field(default_factory=list)
    do_not_touch: List[str] = Field(default_factory=list)


class Node(BaseModel):
    """A node in the repository graph."""

    type: NodeType
    file: Optional[str] = None
    language: Optional[str] = None
    visibility: Optional[str] = Field(None, description="public, private, protected")
    summary: Optional[str] = None
    criticality: float = Field(default=0.0, ge=0.0, le=1.0)

    def to_dict(
        self,
        compact: bool = False,
        exclude_defaults: bool = False,
        max_summary_length: Optional[int] = None,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert node to dictionary with optional compression.
        
        Args:
            compact: Use compact field names
            exclude_defaults: Exclude fields with default values
            max_summary_length: Truncate summary to this length
            node_id: Node ID for deduplication checks
        """
        data = self.model_dump(mode="json", exclude_none=True, by_alias=True)
        
        # Truncate summary if needed
        if max_summary_length and "summary" in data and data["summary"]:
            if len(data["summary"]) > max_summary_length:
                data["summary"] = data["summary"][:max_summary_length - 3] + "..."
        
        # Deduplication: remove file if it's redundant with node_id
        if node_id and "file" in data:
            # If node_id is just the file path, remove redundant file field
            if node_id == data["file"]:
                del data["file"]
        
        # Exclude defaults
        if exclude_defaults:
            if data.get("criticality") == 0.0:
                data.pop("criticality", None)
            if data.get("visibility") == "public":
                data.pop("visibility", None)
        
        # Compress field names if requested
        if compact:
            data = _compress_dict(data, context="node")
        
        return data


class Edge(BaseModel):
    """A relationship between two nodes."""

    from_: str = Field(..., alias="from")
    to: str
    type: EdgeType

    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class Flow(BaseModel):
    """A runtime execution path."""

    entry: str
    path: List[str]
    side_effects: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Concept(BaseModel):
    """A domain concept grouping."""

    nodes: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class History(BaseModel):
    """Temporal evolution data for a file or entity."""

    churn_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_major_change: Optional[str] = None
    notes: Optional[str] = None


class Risk(BaseModel):
    """Risk assessment for a node."""

    risk_score: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)


class Contract(BaseModel):
    """A public API contract."""

    depends_on: List[str] = Field(default_factory=list)
    breaking_change_risk: float = Field(default=0.0, ge=0.0, le=1.0)


class SemanticSummary(BaseModel):
    """Semantic summary for code compression."""

    preconditions: List[str] = Field(default_factory=list)
    postconditions: List[str] = Field(default_factory=list)
    failure_modes: List[str] = Field(default_factory=list)


class ContextScore(BaseModel):
    """Context relevance scoring."""

    relevance: float = Field(ge=0.0, le=1.0)
    freshness: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)


class ContextContract(BaseModel):
    """Context contract for enforcing requirements."""

    must_include: List[str] = Field(default_factory=list)
    optional: List[str] = Field(default_factory=list)
    forbidden: List[str] = Field(default_factory=list)


class ContextFeedback(BaseModel):
    """Context usage feedback."""

    used: List[str] = Field(default_factory=list)
    ignored: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class Tests(BaseModel):
    """Test coverage data."""

    coverage: Optional[Dict[str, float]] = None
    test_files: List[str] = Field(default_factory=list)


class GenomeDiff(BaseModel):
    """Diff between two genome versions."""

    added_nodes: List[str] = Field(default_factory=list)
    removed_nodes: List[str] = Field(default_factory=list)
    added_edges: List[Edge] = Field(default_factory=list)
    removed_edges: List[Edge] = Field(default_factory=list)
    modified_nodes: List[str] = Field(default_factory=list)


class RepoGenome(BaseModel):
    """
    Complete RepoGenome schema.

    This is the root model for repogenome.json files.
    """

    metadata: Metadata = Field(default_factory=Metadata)
    summary: Summary = Field(default_factory=Summary)
    nodes: Dict[str, Node] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)
    flows: List[Flow] = Field(default_factory=list)
    concepts: Dict[str, Concept] = Field(default_factory=dict)
    history: Dict[str, History] = Field(default_factory=dict)
    risk: Dict[str, Risk] = Field(default_factory=dict)
    contracts: Dict[str, Contract] = Field(default_factory=dict)
    tests: Optional[Tests] = None
    genome_diff: Optional[GenomeDiff] = None

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(
        self,
        compact: bool = False,
        lite: bool = False,
        exclude_defaults: bool = False,
        max_summary_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Args:
            compact: Use compact field names
            lite: Ultra-compact mode with only essential fields
            exclude_defaults: Exclude fields with default values
            max_summary_length: Truncate summaries to this length
        """
        if lite:
            return self._to_lite_dict(compact=compact, exclude_defaults=exclude_defaults)
        
        data = self.model_dump(mode="json", exclude_none=True, by_alias=True)
        
        # Process nodes with deduplication and truncation
        if "nodes" in data:
            processed_nodes = {}
            for node_id, node_data in data["nodes"].items():
                if isinstance(node_data, dict):
                    # Truncate summary
                    if max_summary_length and "summary" in node_data and node_data["summary"]:
                        if len(node_data["summary"]) > max_summary_length:
                            node_data["summary"] = node_data["summary"][:max_summary_length - 3] + "..."
                    
                    # Deduplication: remove file if redundant
                    if "file" in node_data and node_id == node_data["file"]:
                        del node_data["file"]
                    
                    # Exclude defaults
                    if exclude_defaults:
                        if node_data.get("criticality") == 0.0:
                            node_data.pop("criticality", None)
                        if node_data.get("visibility") == "public":
                            node_data.pop("visibility", None)
                    
                    processed_nodes[node_id] = node_data
                else:
                    processed_nodes[node_id] = node_data
            data["nodes"] = processed_nodes
        
        # Process concepts with truncation
        if "concepts" in data and max_summary_length:
            for concept_id, concept_data in data["concepts"].items():
                if isinstance(concept_data, dict) and "description" in concept_data:
                    desc = concept_data["description"]
                    if desc and len(desc) > max_summary_length:
                        concept_data["description"] = desc[:max_summary_length - 3] + "..."
        
        # Exclude defaults for other fields
        if exclude_defaults:
            if "flows" in data and not data["flows"]:
                data.pop("flows", None)
            if "concepts" in data and not data["concepts"]:
                data.pop("concepts", None)
            if "history" in data and not data["history"]:
                data.pop("history", None)
            if "risk" in data and not data["risk"]:
                data.pop("risk", None)
            if "contracts" in data and not data["contracts"]:
                data.pop("contracts", None)
        
        # Compress field names if requested
        if compact:
            data = _compress_dict(data)
        
        return data
    
    def _to_lite_dict(
        self,
        compact: bool = False,
        exclude_defaults: bool = False,
    ) -> Dict[str, Any]:
        """Create ultra-compact lite version with only essential fields."""
        data: Dict[str, Any] = {}
        
        # Essential metadata
        if self.metadata:
            data["metadata"] = {
                "generated_at": self.metadata.generated_at.isoformat(),
                "repo_hash": self.metadata.repo_hash,
                "repogenome_version": self.metadata.repogenome_version,
            }
            if compact:
                data["metadata"] = _compress_dict(data["metadata"], context="metadata")
        
        # Essential summary
        if self.summary:
            data["summary"] = {
                "entry_points": self.summary.entry_points,
                "core_domains": self.summary.core_domains,
            }
            if compact:
                data["summary"] = _compress_dict(data["summary"], context="summary")
        
        # Essential nodes (type, file if not in ID, criticality if > 0)
        if self.nodes:
            lite_nodes = {}
            for node_id, node in self.nodes.items():
                node_dict: Dict[str, Any] = {"type": node.type.value}
                
                # Only include file if not redundant
                if node.file and node.file != node_id:
                    node_dict["file"] = node.file
                
                # Only include criticality if > 0
                if node.criticality > 0:
                    node_dict["criticality"] = node.criticality
                
                if compact:
                    node_dict = _compress_dict(node_dict, context="node")
                
                lite_nodes[node_id] = node_dict
            data["nodes"] = lite_nodes
        
        # Essential edges
        if self.edges:
            lite_edges = []
            for edge in self.edges:
                edge_dict = {
                    "from": edge.from_,
                    "to": edge.to,
                    "type": edge.type.value,
                }
                if compact:
                    edge_dict = _compress_dict(edge_dict, context="edge")
                lite_edges.append(edge_dict)
            data["edges"] = lite_edges
        
        return data

    def get_summary_brief(self) -> Dict[str, Any]:
        """
        Get brief summary (minimal essential data).
        
        Returns:
            Dictionary with entry_points and core_domains only
        """
        return {
            "entry_points": self.summary.entry_points,
            "core_domains": self.summary.core_domains,
        }

    def get_summary_standard(self) -> Dict[str, Any]:
        """
        Get standard summary (current implementation).
        
        Returns:
            Dictionary with all standard summary fields
        """
        return self.summary.model_dump()

    def get_summary_detailed(self) -> Dict[str, Any]:
        """
        Get detailed summary (enhanced with metrics).
        
        Returns:
            Dictionary with standard summary plus additional metrics
        """
        summary = self.summary.model_dump()
        
        # Add metrics
        summary["metrics"] = {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "total_flows": len(self.flows),
            "total_concepts": len(self.concepts),
            "nodes_by_type": self._count_nodes_by_type(),
            "languages": list(set(
                node.language for node in self.nodes.values() if node.language
            )),
        }
        
        return summary

    def _count_nodes_by_type(self) -> Dict[str, int]:
        """Count nodes by type."""
        counts: Dict[str, int] = {}
        for node in self.nodes.values():
            node_type = node.type.value
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts

    def get_summary_by_mode(self, mode: SummaryMode) -> Dict[str, Any]:
        """
        Get summary by mode.
        
        Args:
            mode: Summary mode (brief, standard, detailed)
            
        Returns:
            Summary dictionary based on mode
        """
        if mode == SummaryMode.BRIEF:
            return self.get_summary_brief()
        elif mode == SummaryMode.DETAILED:
            return self.get_summary_detailed()
        else:  # STANDARD
            return self.get_summary_standard()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepoGenome":
        """Create RepoGenome from dictionary."""
        # Check if data is in compact format (has compressed field names)
        is_compact = _is_compact_format(data)
        if is_compact:
            data = _expand_dict(data)
        
        # Handle Edge "from" field in edges list
        if "edges" in data:
            edges_data = data["edges"]
            for edge in edges_data:
                if isinstance(edge, dict) and "from" in edge:
                    edge["from_"] = edge.pop("from")

        # Handle genome_diff if present
        if "genome_diff" in data and data["genome_diff"] is not None:
            diff_data = data["genome_diff"]
            # Convert edge dicts to Edge objects
            if "added_edges" in diff_data:
                diff_data["added_edges"] = [
                    Edge(**e) if isinstance(e, dict) else e
                    for e in diff_data["added_edges"]
                ]
            if "removed_edges" in diff_data:
                diff_data["removed_edges"] = [
                    Edge(**e) if isinstance(e, dict) else e
                    for e in diff_data["removed_edges"]
                ]
            data["genome_diff"] = GenomeDiff(**diff_data)

        return cls(**data)

    def save(
        self,
        path: str,
        compact: bool = False,
        lite: bool = False,
        minify: bool = False,
        exclude_defaults: bool = False,
        max_summary_length: Optional[int] = None,
        compress: bool = False,
        streaming: bool = False,
    ) -> None:
        """
        Save genome to JSON file with optional compression.
        
        Args:
            path: Output file path
            compact: Use compact field names
            lite: Ultra-compact mode
            minify: Minified JSON (no indentation)
            exclude_defaults: Exclude default values
            max_summary_length: Truncate summaries
            compress: Use gzip compression
            streaming: Use streaming writer (memory-efficient for large genomes)
        """
        # Use streaming writer for large genomes or when explicitly requested
        if streaming or (len(self.nodes) > 10000 or len(self.edges) > 50000):
            from repogenome.core.streaming import save_streaming
            save_streaming(
                self,
                path,
                compact=compact,
                minify=minify,
                exclude_defaults=exclude_defaults,
                max_summary_length=max_summary_length,
                compress=compress,
            )
            return
        
        # Standard save for smaller genomes
        import json
        import gzip

        data = self.to_dict(
            compact=compact,
            lite=lite,
            exclude_defaults=exclude_defaults,
            max_summary_length=max_summary_length,
        )
        
        json_str = json.dumps(data, ensure_ascii=False, indent=None if minify else 2)
        
        if compress:
            # Save as .json.gz
            if not path.endswith(".gz"):
                path = path + ".gz"
            with gzip.open(path, "wt", encoding="utf-8") as f:
                f.write(json_str)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)

    @classmethod
    def load(cls, path: str) -> "RepoGenome":
        """Load genome from JSON file (supports both regular and compressed formats)."""
        import json
        import gzip

        # Check if file is gzipped
        if path.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return cls.from_dict(data)

    def save_sliced(self, base_path: str) -> None:
        """
        Save genome in sliced format (separate JSON files).
        
        Args:
            base_path: Base directory path for sliced genome (e.g., "repogenome/")
        """
        from pathlib import Path
        import json

        base = Path(base_path)
        base.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        meta_path = base / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        
        # Save summary
        summary_path = base / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(self.summary.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        
        # Save nodes - split into files and symbols
        nodes_base = base / "nodes"
        nodes_base.mkdir(exist_ok=True)
        
        file_nodes: Dict[str, Any] = {}
        symbol_nodes: Dict[str, Any] = {}
        
        for node_id, node in self.nodes.items():
            node_dict = node.model_dump(mode="json")
            node_type = node.type.value if hasattr(node.type, 'value') else str(node.type)
            if node_type == "file":
                file_nodes[node_id] = node_dict
            else:
                symbol_nodes[node_id] = node_dict
        
        with open(nodes_base / "files.json", "w", encoding="utf-8") as f:
            json.dump(file_nodes, f, indent=2, ensure_ascii=False)
        
        with open(nodes_base / "symbols.json", "w", encoding="utf-8") as f:
            json.dump(symbol_nodes, f, indent=2, ensure_ascii=False)
        
        # Save edges
        edges_path = base / "edges.json"
        edges_data = [edge.model_dump(mode="json", by_alias=True) for edge in self.edges]
        with open(edges_path, "w", encoding="utf-8") as f:
            json.dump(edges_data, f, indent=2, ensure_ascii=False)
        
        # Save flows
        flows_path = base / "flows.json"
        flows_data = [flow.model_dump(mode="json") for flow in self.flows]
        with open(flows_path, "w", encoding="utf-8") as f:
            json.dump(flows_data, f, indent=2, ensure_ascii=False)
        
        # Save intents (concepts)
        intents_path = base / "intents.json"
        intents_data = {k: v.model_dump(mode="json") for k, v in self.concepts.items()}
        with open(intents_path, "w", encoding="utf-8") as f:
            json.dump(intents_data, f, indent=2, ensure_ascii=False)
        
        # Save history
        history_path = base / "history.json"
        history_data = {k: v.model_dump(mode="json") for k, v in self.history.items()}
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        # Save risk
        risk_path = base / "risk.json"
        risk_data = {k: v.model_dump(mode="json") for k, v in self.risk.items()}
        with open(risk_path, "w", encoding="utf-8") as f:
            json.dump(risk_data, f, indent=2, ensure_ascii=False)
        
        # Save contracts
        contracts_path = base / "contracts.json"
        contracts_data = {k: v.model_dump(mode="json") for k, v in self.contracts.items()}
        with open(contracts_path, "w", encoding="utf-8") as f:
            json.dump(contracts_data, f, indent=2, ensure_ascii=False)
        
        # Build and save indexes
        indexes_base = base / "indexes"
        indexes_base.mkdir(exist_ok=True)
        
        # Index by symbol
        by_symbol: Dict[str, List[str]] = {}
        for node_id, node in self.nodes.items():
            if node.file:
                if node.file not in by_symbol:
                    by_symbol[node.file] = []
                by_symbol[node.file].append(node_id)
        
        with open(indexes_base / "by_symbol.json", "w", encoding="utf-8") as f:
            json.dump(by_symbol, f, indent=2, ensure_ascii=False)
        
        # Index by intent
        by_intent: Dict[str, List[str]] = {}
        for intent_id, concept in self.concepts.items():
            by_intent[intent_id] = concept.nodes
        
        with open(indexes_base / "by_intent.json", "w", encoding="utf-8") as f:
            json.dump(by_intent, f, indent=2, ensure_ascii=False)
        
        # Index by recent changes (based on history churn)
        by_change: Dict[str, List[str]] = {"recent": []}
        for node_id, hist in self.history.items():
            if hist.churn_score > 0.5:  # High churn = recent changes
                by_change["recent"].append(node_id)
        
        with open(indexes_base / "by_change.json", "w", encoding="utf-8") as f:
            json.dump(by_change, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_sliced(cls, base_path: str) -> "RepoGenome":
        """
        Load genome from sliced format (separate JSON files).
        
        Args:
            base_path: Base directory path for sliced genome (e.g., "repogenome/")
            
        Returns:
            RepoGenome instance
        """
        from pathlib import Path
        import json

        base = Path(base_path)
        
        # Load metadata
        meta_path = base / "meta.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata_dict = json.load(f)
        metadata = Metadata(**metadata_dict)
        
        # Load nodes
        nodes_base = base / "nodes"
        file_nodes_path = nodes_base / "files.json"
        symbol_nodes_path = nodes_base / "symbols.json"
        
        nodes: Dict[str, Node] = {}
        
        if file_nodes_path.exists():
            with open(file_nodes_path, "r", encoding="utf-8") as f:
                file_nodes_dict = json.load(f)
                for node_id, node_data in file_nodes_dict.items():
                    nodes[node_id] = Node(**node_data)
        
        if symbol_nodes_path.exists():
            with open(symbol_nodes_path, "r", encoding="utf-8") as f:
                symbol_nodes_dict = json.load(f)
                for node_id, node_data in symbol_nodes_dict.items():
                    nodes[node_id] = Node(**node_data)
        
        # Load edges
        edges_path = base / "edges.json"
        edges: List[Edge] = []
        if edges_path.exists():
            with open(edges_path, "r", encoding="utf-8") as f:
                edges_data = json.load(f)
                for edge_data in edges_data:
                    # Handle "from" field alias
                    if "from" in edge_data:
                        edge_data["from_"] = edge_data.pop("from")
                    edges.append(Edge(**edge_data))
        
        # Load flows
        flows_path = base / "flows.json"
        flows: List[Flow] = []
        if flows_path.exists():
            with open(flows_path, "r", encoding="utf-8") as f:
                flows_data = json.load(f)
                flows = [Flow(**flow_data) for flow_data in flows_data]
        
        # Load intents (concepts)
        intents_path = base / "intents.json"
        concepts: Dict[str, Concept] = {}
        if intents_path.exists():
            with open(intents_path, "r", encoding="utf-8") as f:
                intents_data = json.load(f)
                concepts = {k: Concept(**v) for k, v in intents_data.items()}
        
        # Load history
        history_path = base / "history.json"
        history: Dict[str, History] = {}
        if history_path.exists():
            with open(history_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                history = {k: History(**v) for k, v in history_data.items()}
        
        # Load risk
        risk_path = base / "risk.json"
        risk: Dict[str, Risk] = {}
        if risk_path.exists():
            with open(risk_path, "r", encoding="utf-8") as f:
                risk_data = json.load(f)
                risk = {k: Risk(**v) for k, v in risk_data.items()}
        
        # Load contracts
        contracts_path = base / "contracts.json"
        contracts: Dict[str, Contract] = {}
        if contracts_path.exists():
            with open(contracts_path, "r", encoding="utf-8") as f:
                contracts_data = json.load(f)
                contracts = {k: Contract(**v) for k, v in contracts_data.items()}
        
        # Load tests
        tests: Optional[Tests] = None
        
        # Load summary
        summary_path = base / "summary.json"
        summary = Summary()
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
                summary = Summary(**summary_data)
        
        return cls(
            metadata=metadata,
            summary=summary,
            nodes=nodes,
            edges=edges,
            flows=flows,
            concepts=concepts,
            history=history,
            risk=risk,
            contracts=contracts,
            tests=tests,
        )


def _is_compact_format(data: Dict[str, Any]) -> bool:
    """Check if data uses compact field names."""
    # Check a few common fields to determine if compact
    if "metadata" in data and isinstance(data["metadata"], dict):
        # Check for compact field names
        if "ga" in data["metadata"] or "rv" in data["metadata"]:
            return True
    if "nodes" in data and isinstance(data["nodes"], dict) and data["nodes"]:
        # Check first node
        first_node = next(iter(data["nodes"].values()))
        if isinstance(first_node, dict) and ("t" in first_node or "f" in first_node):
            return True
    return False

