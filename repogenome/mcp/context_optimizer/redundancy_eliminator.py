"""Redundancy elimination engine for detecting duplicate logic."""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Set

from repogenome.core.schema import Node, RepoGenome

logger = logging.getLogger(__name__)


class RedundancyEliminator:
    """Detects and eliminates redundant logic across files."""

    def __init__(self, genome: RepoGenome):
        """
        Initialize redundancy eliminator.
        
        Args:
            genome: RepoGenome instance
        """
        self.genome = genome
        self.duplicate_index: Dict[str, List[str]] = {}  # hash -> [node_ids]
        self._build_index()

    def _build_index(self):
        """Build index of duplicate logic."""
        # Group nodes by their semantic hash
        hash_to_nodes: Dict[str, List[str]] = {}
        
        for node_id, node in self.genome.nodes.items():
            if node.type.value != "function":
                continue
            
            # Generate hash from node characteristics
            logic_hash = self._hash_node_logic(node, node_id)
            
            if logic_hash not in hash_to_nodes:
                hash_to_nodes[logic_hash] = []
            hash_to_nodes[logic_hash].append(node_id)
        
        # Only keep hashes with multiple occurrences
        for logic_hash, node_ids in hash_to_nodes.items():
            if len(node_ids) > 1:
                self.duplicate_index[logic_hash] = node_ids

    def _hash_node_logic(self, node: Node, node_id: str) -> str:
        """
        Generate hash for node logic.
        
        Args:
            node: Node to hash
            node_id: Node ID
            
        Returns:
            Hash string
        """
        # Create hash from:
        # 1. Summary (normalized)
        # 2. Type
        # 3. File path (normalized)
        # 4. Language
        
        components = []
        
        # Normalized summary (lowercase, remove extra whitespace)
        if node.summary:
            normalized_summary = " ".join(node.summary.lower().split())
            components.append(f"summary:{normalized_summary}")
        
        components.append(f"type:{node.type.value}")
        
        if node.file:
            # Normalize file path (remove common prefixes)
            normalized_file = node.file.replace("\\", "/").lower()
            components.append(f"file:{normalized_file}")
        
        if node.language:
            components.append(f"lang:{node.language.lower()}")
        
        # Create hash
        hash_input = "|".join(components)
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:16]

    def get_duplicates(self, node_id: str) -> Optional[List[str]]:
        """
        Get list of nodes with duplicate logic to the given node.
        
        Args:
            node_id: Node ID to check
            
        Returns:
            List of duplicate node IDs (excluding the input node), or None if no duplicates
        """
        if node_id not in self.genome.nodes:
            return None
        
        node = self.genome.nodes[node_id]
        logic_hash = self._hash_node_logic(node, node_id)
        
        duplicates = self.duplicate_index.get(logic_hash, [])
        # Remove the input node from the list
        duplicates = [nid for nid in duplicates if nid != node_id]
        
        return duplicates if duplicates else None

    def eliminate_redundancy(self, node_ids: List[str]) -> Dict[str, Any]:
        """
        Eliminate redundant nodes from a list.
        
        Args:
            node_ids: List of node IDs to deduplicate
            
        Returns:
            Dictionary with:
            - unique_nodes: List of unique node IDs
            - duplicate_groups: Dict mapping representative node_id -> [duplicate_ids]
        """
        seen_hashes: Dict[str, str] = {}  # hash -> representative_node_id
        duplicate_groups: Dict[str, List[str]] = {}
        unique_nodes: List[str] = []
        
        for node_id in node_ids:
            if node_id not in self.genome.nodes:
                continue
            
            node = self.genome.nodes[node_id]
            logic_hash = self._hash_node_logic(node, node_id)
            
            if logic_hash in seen_hashes:
                # This is a duplicate
                representative = seen_hashes[logic_hash]
                if representative not in duplicate_groups:
                    duplicate_groups[representative] = []
                duplicate_groups[representative].append(node_id)
            else:
                # First occurrence - keep it
                seen_hashes[logic_hash] = node_id
                unique_nodes.append(node_id)
        
        return {
            "unique_nodes": unique_nodes,
            "duplicate_groups": duplicate_groups,
        }

    def get_duplicate_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get duplicate information for a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            Dictionary with duplicate information, or None if no duplicates
        """
        duplicates = self.get_duplicates(node_id)
        if not duplicates:
            return None
        
        return {
            "hash": self._hash_node_logic(self.genome.nodes[node_id], node_id),
            "occurrences": [node_id] + duplicates,
        }

