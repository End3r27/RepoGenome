"""
Core schema definitions for RepoGenome JSON structure.

This module defines the complete data model for repogenome.json using Pydantic
for validation and serialization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field


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


class Metadata(BaseModel):
    """Repository metadata and generation information."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    repo_hash: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    repogenome_version: str = Field(default="0.1.0")


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True, by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepoGenome":
        """Create RepoGenome from dictionary."""
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

    def save(self, path: str) -> None:
        """Save genome to JSON file."""
        import json

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "RepoGenome":
        """Load genome from JSON file."""
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

