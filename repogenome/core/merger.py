"""Incremental merger for updating genomes without full regeneration."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from repogenome.core.schema import GenomeDiff, RepoGenome
from repogenome.utils.git_utils import get_changed_files
from repogenome.utils.json_diff import compute_genome_diff, get_affected_nodes


class GenomeMerger:
    """Handle incremental updates to RepoGenome."""

    def __init__(self, repo_path: Path):
        """
        Initialize merger.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path

    def update_incremental(
        self,
        old_genome: RepoGenome,
        subsystems: Dict[str, Any],
        changed_files: Optional[List[str]] = None,
    ) -> RepoGenome:
        """
        Perform incremental update.

        Args:
            old_genome: Previous genome
            subsystems: Dictionary of subsystem instances
            changed_files: Optional list of changed files (auto-detect if None)

        Returns:
            Updated genome
        """
        # Detect changed files if not provided
        if changed_files is None:
            changed_files = get_changed_files(self.repo_path)

        # Convert old genome to dict for easier manipulation
        old_dict = old_genome.to_dict()

        # Determine which subsystems need re-analysis
        affected_nodes = get_affected_nodes(changed_files, old_dict)
        subsystems_to_update = self._determine_subsystems_to_update(
            affected_nodes, old_dict, subsystems
        )

        # Run affected subsystems
        updated_data: Dict[str, Any] = {}

        # Always run RepoSpider first (other subsystems depend on it)
        if "repospider" in subsystems:
            repospider_result = subsystems["repospider"].analyze(
                self.repo_path, old_dict
            )
            updated_data.update(repospider_result)

        # Run other subsystems if they need updating
        for subsystem_name in subsystems_to_update:
            if subsystem_name == "repospider":
                continue  # Already done
            if subsystem_name in subsystems:
                subsystem = subsystems[subsystem_name]
                # Pass updated data as existing genome for dependent subsystems
                subsystem_result = subsystem.analyze(
                    self.repo_path, {**old_dict, **updated_data}
                )
                updated_data.update(subsystem_result)

        # Merge old and new data
        merged_data = self._merge_data(old_dict, updated_data, affected_nodes)

        # Create new genome
        new_genome = RepoGenome.from_dict(merged_data)

        # Compute diff and convert to GenomeDiff object
        diff_dict = compute_genome_diff(old_dict, new_genome.to_dict())
        
        # Convert edge dicts to Edge objects
        from repogenome.core.schema import Edge
        added_edges = [Edge(**e) if isinstance(e, dict) else e for e in diff_dict.get("added_edges", [])]
        removed_edges = [Edge(**e) if isinstance(e, dict) else e for e in diff_dict.get("removed_edges", [])]
        
        diff = GenomeDiff(
            added_nodes=diff_dict.get("added_nodes", []),
            removed_nodes=diff_dict.get("removed_nodes", []),
            modified_nodes=diff_dict.get("modified_nodes", []),
            added_edges=added_edges,
            removed_edges=removed_edges,
        )
        new_genome.genome_diff = diff

        return new_genome

    def _determine_subsystems_to_update(
        self,
        affected_nodes: set,
        old_genome: Dict[str, Any],
        subsystems: Dict[str, Any],
    ) -> List[str]:
        """
        Determine which subsystems need re-analysis with smart selection.

        Args:
            affected_nodes: Set of affected node IDs
            old_genome: Old genome dictionary
            subsystems: Available subsystems

        Returns:
            List of subsystem names to update
        """
        total_nodes = len(old_genome.get("nodes", {}))
        affected_ratio = len(affected_nodes) / total_nodes if total_nodes > 0 else 1.0

        # If many nodes affected (>50%), update all subsystems
        if affected_ratio > 0.5:
            return list(subsystems.keys())

        # Analyze affected node types to determine which subsystems need updates
        affected_types = set()
        affected_files = set()
        
        for node_id in affected_nodes:
            node_data = old_genome.get("nodes", {}).get(node_id, {})
            node_type = node_data.get("type", "")
            affected_types.add(node_type)
            
            file_path = node_data.get("file", "")
            if file_path:
                affected_files.add(file_path)

        subsystems_to_update = ["repospider"]  # Always update RepoSpider

        # FlowWeaver: update if functions/classes changed or entry points affected
        if "flowweaver" in subsystems:
            if any(t in affected_types for t in ["function", "class", "method"]):
                subsystems_to_update.append("flowweaver")
            # Check if entry points affected
            entry_points = old_genome.get("summary", {}).get("entry_points", [])
            if any(ep in affected_nodes for ep in entry_points):
                subsystems_to_update.append("flowweaver")

        # IntentAtlas: update if structure changed significantly
        if "intentatlas" in subsystems:
            if affected_ratio > 0.1 or any(t in affected_types for t in ["class", "module"]):
                subsystems_to_update.append("intentatlas")

        # ContractLens: update if public APIs changed
        if "contractlens" in subsystems:
            # Check if any affected nodes are public
            public_nodes = [
                nid for nid in affected_nodes
                if old_genome.get("nodes", {}).get(nid, {}).get("visibility") == "public"
            ]
            if public_nodes:
                subsystems_to_update.append("contractlens")

        # TestGalaxy: update if test files or tested code changed
        if "testgalaxy" in subsystems:
            test_files = [f for f in affected_files if "test" in f.lower() or "spec" in f.lower()]
            if test_files or affected_ratio > 0.05:
                subsystems_to_update.append("testgalaxy")

        # ChronoMap: always update if files changed (tracks history)
        if affected_nodes and "chronomap" in subsystems:
            subsystems_to_update.append("chronomap")

        # Security: update if security-sensitive files changed
        if "security" in subsystems:
            security_files = [
                f for f in affected_files
                if any(keyword in f.lower() for keyword in ["auth", "security", "crypto", "password", "token"])
            ]
            if security_files:
                subsystems_to_update.append("security")

        return subsystems_to_update

    def _merge_data(
        self, old_data: Dict[str, Any], new_data: Dict[str, Any], affected_nodes: set
    ) -> Dict[str, Any]:
        """
        Merge old and new genome data.

        Args:
            old_data: Old genome dictionary
            new_data: New data from subsystems
            affected_nodes: Set of affected node IDs

        Returns:
            Merged genome dictionary
        """
        merged = old_data.copy()

        # Merge nodes: remove affected, add new
        merged_nodes = merged.get("nodes", {}).copy()
        for node_id in affected_nodes:
            merged_nodes.pop(node_id, None)

        # Add new/updated nodes
        new_nodes = new_data.get("nodes", {})
        merged_nodes.update(new_nodes)
        merged["nodes"] = merged_nodes

        # Merge edges: remove edges involving affected nodes, add new
        merged_edges = [
            e
            for e in merged.get("edges", [])
            if e.get("from") not in affected_nodes
            and e.get("from_") not in affected_nodes
            and e.get("to") not in affected_nodes
        ]
        merged_edges.extend(new_data.get("edges", []))
        merged["edges"] = merged_edges

        # Merge other sections (replace entirely for simplicity)
        for key in ["flows", "concepts", "history", "risk", "contracts"]:
            if key in new_data:
                merged[key] = new_data[key]

        # Merge tests if present
        if "tests" in new_data:
            merged["tests"] = new_data["tests"]

        # Update test nodes and edges if present
        if "test_nodes" in new_data:
            test_nodes = merged.get("nodes", {})
            test_nodes.update(new_data["test_nodes"])
            merged["nodes"] = test_nodes

        if "test_edges" in new_data:
            merged_edges = merged.get("edges", [])
            merged_edges.extend(new_data["test_edges"])
            merged["edges"] = merged_edges

        return merged

