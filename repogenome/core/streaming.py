"""
Streaming JSON writer for large RepoGenome files.

This module provides a streaming writer that can write genomes incrementally
without loading the entire structure into memory.
"""

import json
import gzip
from typing import Any, Dict, Optional, TextIO
from pathlib import Path

from repogenome.core.schema import (
    RepoGenome,
    Node,
    Edge,
    Metadata,
    Summary,
    Flow,
    Concept,
    History,
    Risk,
    Contract,
    Tests,
    _compress_dict,
    _compress_field_name,
)


class StreamingGenomeWriter:
    """Streaming writer for RepoGenome JSON files."""

    def __init__(
        self,
        file_path: str,
        compact: bool = False,
        minify: bool = False,
        exclude_defaults: bool = False,
        max_summary_length: Optional[int] = None,
        compress: bool = False,
    ):
        """
        Initialize streaming writer.

        Args:
            file_path: Output file path
            compact: Use compact field names
            minify: Minify JSON (no indentation)
            exclude_defaults: Exclude default values
            max_summary_length: Truncate summaries
            compress: Use gzip compression
        """
        self.file_path = file_path
        self.compact = compact
        self.minify = minify
        self.exclude_defaults = exclude_defaults
        self.max_summary_length = max_summary_length
        self.compress = compress
        self.indent = None if minify else 2
        self.separator = "," if minify else ", "
        self.newline = "" if minify else "\n"
        self.indent_str = "" if minify else "  "
        self.file: Optional[TextIO] = None
        self.first_item = True

    def __enter__(self):
        """Open file for writing."""
        if self.compress:
            if not self.file_path.endswith(".gz"):
                self.file_path = self.file_path + ".gz"
            self.file = gzip.open(self.file_path, "wt", encoding="utf-8")
        else:
            self.file = open(self.file_path, "w", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close file."""
        if self.file:
            self.file.close()

    def _write(self, text: str):
        """Write text to file."""
        if self.file:
            self.file.write(text)

    def _write_indent(self, level: int = 0):
        """Write indentation."""
        if not self.minify:
            self._write(self.indent_str * level)

    def _write_key(self, key: str):
        """Write JSON key."""
        if self.compact:
            key = _compress_field_name(key)
        self._write(json.dumps(key, ensure_ascii=False))
        self._write(":" if self.minify else ": ")

    def _write_separator(self):
        """Write item separator."""
        if not self.first_item:
            self._write(self.separator)
        self.first_item = False

    def start_object(self):
        """Start JSON object."""
        self._write("{")
        self.first_item = True

    def end_object(self):
        """End JSON object."""
        self._write("}")

    def start_array(self):
        """Start JSON array."""
        self._write("[")
        self.first_item = True

    def end_array(self):
        """End JSON array."""
        self._write("]")

    def write_metadata(self, metadata: Metadata):
        """Write metadata section."""
        self._write_separator()
        self._write_indent(1)
        self._write_key("metadata")
        self._write_object_fields(
            {
                "generated_at": metadata.generated_at.isoformat(),
                "repo_hash": metadata.repo_hash,
                "languages": metadata.languages,
                "frameworks": metadata.frameworks,
                "repogenome_version": metadata.repogenome_version,
            },
            context="metadata",
        )

    def write_summary(self, summary: Summary):
        """Write summary section."""
        self._write_separator()
        self._write_indent(1)
        self._write_key("summary")
        self._write_object_fields(
            {
                "entry_points": summary.entry_points,
                "architectural_style": summary.architectural_style,
                "core_domains": summary.core_domains,
                "hotspots": summary.hotspots,
                "do_not_touch": summary.do_not_touch,
            },
            context="summary",
        )

    def write_nodes(self, nodes: Dict[str, Node]):
        """Write nodes section (streaming)."""
        self._write_separator()
        self._write_indent(1)
        self._write_key("nodes")
        self.start_object()
        self._write(self.newline)
        
        node_items = list(nodes.items())
        for i, (node_id, node) in enumerate(node_items):
            if i > 0:
                self._write(self.separator)
                self._write(self.newline)
            
            self._write_indent(2)
            self._write(json.dumps(node_id, ensure_ascii=False))
            self._write(":" if self.minify else ": ")
            
            node_dict = node.to_dict(
                compact=self.compact,
                exclude_defaults=self.exclude_defaults,
                max_summary_length=self.max_summary_length,
                node_id=node_id,
            )
            self._write(json.dumps(node_dict, ensure_ascii=False))
        
        self._write(self.newline)
        self._write_indent(1)
        self.end_object()

    def write_edges(self, edges: list):
        """Write edges section (streaming)."""
        self._write_separator()
        self._write_indent(1)
        self._write_key("edges")
        self.start_array()
        self._write(self.newline)
        
        for i, edge in enumerate(edges):
            if i > 0:
                self._write(self.separator)
                self._write(self.newline)
            
            self._write_indent(2)
            edge_dict = edge.model_dump(by_alias=True)
            if self.compact:
                edge_dict = _compress_dict(edge_dict, context="edge")
            self._write(json.dumps(edge_dict, ensure_ascii=False))
        
        self._write(self.newline)
        self._write_indent(1)
        self.end_array()

    def write_flows(self, flows: list):
        """Write flows section (streaming)."""
        if not flows:
            return
        
        self._write_separator()
        self._write_indent(1)
        self._write_key("flows")
        self.start_array()
        self._write(self.newline)
        
        for i, flow in enumerate(flows):
            if i > 0:
                self._write(self.separator)
                self._write(self.newline)
            
            self._write_indent(2)
            flow_dict = flow.model_dump(by_alias=True)
            if self.compact:
                flow_dict = _compress_dict(flow_dict, context="flow")
            self._write(json.dumps(flow_dict, ensure_ascii=False))
        
        self._write(self.newline)
        self._write_indent(1)
        self.end_array()

    def write_concepts(self, concepts: Dict[str, Concept]):
        """Write concepts section (streaming)."""
        if not concepts:
            return
        
        self._write_separator()
        self._write_indent(1)
        self._write_key("concepts")
        self.start_object()
        self._write(self.newline)
        
        concept_items = list(concepts.items())
        for i, (concept_id, concept) in enumerate(concept_items):
            if i > 0:
                self._write(self.separator)
                self._write(self.newline)
            
            self._write_indent(2)
            self._write(json.dumps(concept_id, ensure_ascii=False))
            self._write(":" if self.minify else ": ")
            
            concept_dict = concept.model_dump(by_alias=True)
            if self.compact:
                concept_dict = _compress_dict(concept_dict, context="concept")
            self._write(json.dumps(concept_dict, ensure_ascii=False))
        
        self._write(self.newline)
        self._write_indent(1)
        self.end_object()

    def write_history(self, history: Dict[str, History]):
        """Write history section (streaming)."""
        if not history:
            return
        
        self._write_separator()
        self._write_indent(1)
        self._write_key("history")
        self.start_object()
        self._write(self.newline)
        
        history_items = list(history.items())
        for i, (node_id, hist) in enumerate(history_items):
            if i > 0:
                self._write(self.separator)
                self._write(self.newline)
            
            self._write_indent(2)
            self._write(json.dumps(node_id, ensure_ascii=False))
            self._write(":" if self.minify else ": ")
            
            hist_dict = hist.model_dump(by_alias=True)
            if self.compact:
                hist_dict = _compress_dict(hist_dict, context="history")
            self._write(json.dumps(hist_dict, ensure_ascii=False))
        
        self._write(self.newline)
        self._write_indent(1)
        self.end_object()

    def write_risk(self, risk: Dict[str, Risk]):
        """Write risk section (streaming)."""
        if not risk:
            return
        
        self._write_separator()
        self._write_indent(1)
        self._write_key("risk")
        self.start_object()
        self._write(self.newline)
        
        risk_items = list(risk.items())
        for i, (node_id, risk_data) in enumerate(risk_items):
            if i > 0:
                self._write(self.separator)
                self._write(self.newline)
            
            self._write_indent(2)
            self._write(json.dumps(node_id, ensure_ascii=False))
            self._write(":" if self.minify else ": ")
            
            risk_dict = risk_data.model_dump(by_alias=True)
            if self.compact:
                risk_dict = _compress_dict(risk_dict, context="risk")
            self._write(json.dumps(risk_dict, ensure_ascii=False))
        
        self._write(self.newline)
        self._write_indent(1)
        self.end_object()

    def write_contracts(self, contracts: Dict[str, Contract]):
        """Write contracts section (streaming)."""
        if not contracts:
            return
        
        self._write_separator()
        self._write_indent(1)
        self._write_key("contracts")
        self.start_object()
        self._write(self.newline)
        
        contract_items = list(contracts.items())
        for i, (contract_id, contract) in enumerate(contract_items):
            if i > 0:
                self._write(self.separator)
                self._write(self.newline)
            
            self._write_indent(2)
            self._write(json.dumps(contract_id, ensure_ascii=False))
            self._write(":" if self.minify else ": ")
            
            contract_dict = contract.model_dump(by_alias=True)
            if self.compact:
                contract_dict = _compress_dict(contract_dict, context="contract")
            self._write(json.dumps(contract_dict, ensure_ascii=False))
        
        self._write(self.newline)
        self._write_indent(1)
        self.end_object()

    def write_tests(self, tests: Optional[Tests]):
        """Write tests section."""
        if not tests:
            return
        
        self._write_separator()
        self._write_indent(1)
        self._write_key("tests")
        tests_dict = tests.model_dump(by_alias=True)
        if self.compact:
            tests_dict = _compress_dict(tests_dict, context="tests")
        self._write(json.dumps(tests_dict, ensure_ascii=False))

    def _write_object_fields(self, fields: Dict[str, Any], context: Optional[str] = None):
        """Write object fields."""
        self.start_object()
        self._write(self.newline)
        
        field_items = list(fields.items())
        for i, (key, value) in enumerate(field_items):
            if value is None and self.exclude_defaults:
                continue
            
            if i > 0:
                self._write(self.separator)
                self._write(self.newline)
            
            self._write_indent(2)
            self._write_key(key)
            self._write(json.dumps(value, ensure_ascii=False))
        
        self._write(self.newline)
        self._write_indent(1)
        self.end_object()


def save_streaming(
    genome: RepoGenome,
    path: str,
    compact: bool = False,
    minify: bool = False,
    exclude_defaults: bool = False,
    max_summary_length: Optional[int] = None,
    compress: bool = False,
) -> None:
    """
    Save genome using streaming writer (memory-efficient for large genomes).

    Args:
        genome: RepoGenome to save
        path: Output file path
        compact: Use compact field names
        minify: Minify JSON
        exclude_defaults: Exclude default values
        max_summary_length: Truncate summaries
        compress: Use gzip compression
    """
    with StreamingGenomeWriter(
        path,
        compact=compact,
        minify=minify,
        exclude_defaults=exclude_defaults,
        max_summary_length=max_summary_length,
        compress=compress,
    ) as writer:
        writer.start_object()
        writer._write(writer.newline)
        
        # Write sections in order
        if genome.metadata:
            writer.write_metadata(genome.metadata)
        
        if genome.summary:
            writer.write_summary(genome.summary)
        
        if genome.nodes:
            writer.write_nodes(genome.nodes)
        
        if genome.edges:
            writer.write_edges(genome.edges)
        
        if genome.flows:
            writer.write_flows(genome.flows)
        
        if genome.concepts:
            writer.write_concepts(genome.concepts)
        
        if genome.history:
            writer.write_history(genome.history)
        
        if genome.risk:
            writer.write_risk(genome.risk)
        
        if genome.contracts:
            writer.write_contracts(genome.contracts)
        
        if genome.tests:
            writer.write_tests(genome.tests)
        
        writer._write(writer.newline)
        writer.end_object()

