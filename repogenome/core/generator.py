"""Main generator orchestrator for RepoGenome."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from repogenome.core.merger import GenomeMerger
from repogenome.core.metadata import extract_metadata
from repogenome.core.schema import RepoGenome, Summary
from repogenome.subsystems.base import Subsystem
from repogenome.subsystems.chronomap import ChronoMap
from repogenome.subsystems.contractlens import ContractLens
from repogenome.subsystems.flowweaver import FlowWeaver
from repogenome.subsystems.intentatlas import IntentAtlas
from repogenome.subsystems.repospider import RepoSpider
from repogenome.subsystems.testgalaxy import TestGalaxy
from repogenome.subsystems.security import SecurityAnalyzer


class RepoGenomeGenerator:
    """
    Main generator for creating RepoGenome artifacts.

    Coordinates all subsystems and merges results into a unified genome.
    """

    def __init__(
        self,
        repo_path: Path,
        enabled_subsystems: Optional[List[str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize generator.

        Args:
            repo_path: Path to repository root
            enabled_subsystems: Optional list of subsystem names to enable.
                               If None, enables all available subsystems.
            logger: Optional logger instance.
        """
        self.repo_path = Path(repo_path).resolve()
        self.logger = logger or logging.getLogger(__name__)
        self.subsystems: Dict[str, Subsystem] = {}

        # Register all available subsystems
        all_subsystems = {
            "repospider": RepoSpider(),
            "flowweaver": FlowWeaver(),
            "intentatlas": IntentAtlas(),
            "chronomap": ChronoMap(),
            "testgalaxy": TestGalaxy(),
            "contractlens": ContractLens(),
            "security": SecurityAnalyzer(),
        }

        # Enable requested subsystems (or all if None)
        if enabled_subsystems is None:
            enabled_subsystems = list(all_subsystems.keys())

        for name in enabled_subsystems:
            if name in all_subsystems:
                self.subsystems[name] = all_subsystems[name]

        self.merger = GenomeMerger(self.repo_path)

    def generate(
        self,
        incremental: bool = False,
        existing_genome_path: Optional[Path] = None,
        progress: Optional[Any] = None,
    ) -> RepoGenome:
        """
        Generate RepoGenome for the repository.

        Args:
            incremental: If True, perform incremental update
            existing_genome_path: Path to existing genome (required for incremental)

        Returns:
            RepoGenome object
        """
        self.logger.info("Starting genome generation")
        if incremental and existing_genome_path:
            self.logger.info("Performing incremental generation")
            return self._generate_incremental(existing_genome_path, progress)
        else:
            self.logger.info("Performing full generation")
            return self._generate_full(progress)

    def _generate_full(self, progress: Optional[Any] = None) -> RepoGenome:
        """Generate complete genome from scratch."""
        self.logger.info("Extracting metadata")
        
        # Extract metadata
        if progress:
            task = progress.add_task("Extracting metadata", total=None)
        metadata = extract_metadata(self.repo_path)
        if progress:
            progress.update(task, completed=True)

        # Run subsystems in dependency order
        accumulated_data: Dict[str, Any] = {}

        # 1. RepoSpider (no dependencies)
        if "repospider" in self.subsystems:
            if progress:
                task = progress.add_task("Analyzing repository structure (RepoSpider)", total=None)
            repospider_result = self.subsystems["repospider"].analyze(
                self.repo_path, None, progress=progress
            )
            accumulated_data.update(repospider_result)
            if progress:
                progress.update(task, completed=True)

        # 2. Other subsystems (may depend on RepoSpider)
        subsystem_order = [
            "flowweaver",
            "intentatlas",
            "contractlens",
            "testgalaxy",
            "chronomap",
            "security",
        ]

        for subsystem_name in subsystem_order:
            if subsystem_name in self.subsystems:
                subsystem = self.subsystems[subsystem_name]
                subsystem_display = subsystem_name.replace("_", " ").title()
                if progress:
                    task = progress.add_task(f"Running {subsystem_display}", total=None)
                subsystem_result = subsystem.analyze(
                    self.repo_path, accumulated_data, progress=progress
                )
                accumulated_data.update(subsystem_result)
                if progress:
                    progress.update(task, completed=True)

        # Build summary
        summary = self._build_summary(accumulated_data)

        # Calculate risk scores
        risk = self._calculate_risk(accumulated_data)

        # Build genome
        genome_dict = {
            "metadata": metadata.model_dump(),
            "summary": summary.model_dump(),
            "nodes": accumulated_data.get("nodes", {}),
            "edges": accumulated_data.get("edges", []),
            "flows": accumulated_data.get("flows", []),
            "concepts": accumulated_data.get("concepts", {}),
            "history": accumulated_data.get("history", {}),
            "risk": risk,
            "contracts": accumulated_data.get("contracts", {}),
            "tests": accumulated_data.get("tests"),
        }

        # Handle test nodes/edges (merge into main nodes/edges)
        if "test_nodes" in accumulated_data:
            genome_dict["nodes"].update(accumulated_data["test_nodes"])
        if "test_edges" in accumulated_data:
            genome_dict["edges"].extend(accumulated_data["test_edges"])
        
        # Clean up test_nodes/test_edges from accumulated_data to avoid duplicates
        accumulated_data.pop("test_nodes", None)
        accumulated_data.pop("test_edges", None)

        genome = RepoGenome.from_dict(genome_dict)
        return genome

    def _generate_incremental(
        self, existing_genome_path: Path, progress: Optional[Any] = None
    ) -> RepoGenome:
        """Generate genome using incremental update."""
        old_genome = RepoGenome.load(str(existing_genome_path))
        return self.merger.update_incremental(
            old_genome, self.subsystems, changed_files=None
        )

    def _build_summary(self, data: Dict[str, Any]) -> Summary:
        """Build summary section from analysis data."""
        entry_points = data.get("entry_points", [])

        # Extract architectural style from structure
        architectural_style = self._detect_architectural_style(data)

        # Extract core domains from concepts
        core_domains = list(data.get("concepts", {}).keys())

        # Identify hotspots (high churn or high fan-in)
        hotspots = self._identify_hotspots(data)

        # Identify do_not_touch (legacy, deprecated, high risk)
        do_not_touch = self._identify_do_not_touch(data)

        return Summary(
            entry_points=entry_points,
            architectural_style=architectural_style,
            core_domains=core_domains,
            hotspots=hotspots,
            do_not_touch=do_not_touch,
        )

    def _detect_architectural_style(self, data: Dict[str, Any]) -> List[str]:
        """Detect architectural patterns from code structure."""
        styles = []

        nodes = data.get("nodes", {})
        edges = data.get("edges", [])

        # Check for layered architecture (model/view/controller separation)
        has_model = any("model" in node_id.lower() for node_id in nodes.keys())
        has_view = any("view" in node_id.lower() for node_id in nodes.keys())
        has_controller = any(
            "controller" in node_id.lower() for node_id in nodes.keys()
        )

        if has_model and has_view and has_controller:
            styles.append("MVC")

        # Check for layered architecture (service/data layers)
        has_service = any("service" in node_id.lower() for node_id in nodes.keys())
        has_data = any(
            "data" in node_id.lower() or "dao" in node_id.lower()
            for node_id in nodes.keys()
        )

        if has_service and has_data:
            styles.append("Layered")

        # Check for API-first architecture
        api_routes = [
            node_id
            for node_id, node_data in nodes.items()
            if node_data.get("type") == "function"
            and any(
                keyword in node_id.lower()
                for keyword in ["route", "endpoint", "api", "handler"]
            )
        ]

        if api_routes:
            styles.append("API-First")

        return styles if styles else ["Monolithic"]

    def _identify_hotspots(self, data: Dict[str, Any]) -> List[str]:
        """Identify code hotspots (frequently changed, high complexity)."""
        hotspots = []

        nodes = data.get("nodes", {})
        history = data.get("history", {})

        # High churn files
        for node_id, hist_data in history.items():
            churn = hist_data.get("churn_score", 0.0)
            if churn > 0.7:
                hotspots.append(node_id)

        # High fan-in nodes (critical dependencies)
        fan_in: Dict[str, int] = {}
        edges = data.get("edges", [])
        for edge in edges:
            edge_type = edge.get("type")
            if edge_type in ["calls", "imports"]:
                to_node = edge.get("to")
                fan_in[to_node] = fan_in.get(to_node, 0) + 1

        for node_id, count in fan_in.items():
            if count > 10:
                hotspots.append(node_id)

        return hotspots[:20]  # Limit to top 20

    def _identify_do_not_touch(self, data: Dict[str, Any]) -> List[str]:
        """Identify files/nodes that should not be touched."""
        do_not_touch = []

        nodes = data.get("nodes", {})
        history = data.get("history", {})

        # Legacy markers in file paths
        for node_id, node_data in nodes.items():
            file_path = node_data.get("file", "")
            if any(
                keyword in file_path.lower()
                for keyword in ["legacy", "deprecated", "old", "_old", "backup"]
            ):
                do_not_touch.append(node_id)

        # Files with high risk and low churn (stable but risky to change)
        for node_id, hist_data in history.items():
            churn = hist_data.get("churn_score", 0.0)
            last_change = hist_data.get("last_major_change")
            # Low churn + old = legacy
            if churn < 0.2 and last_change:
                # Check if last change was > 1 year ago (simplified)
                do_not_touch.append(node_id)

        return list(set(do_not_touch))  # Deduplicate

    def _calculate_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk scores for nodes."""
        from repogenome.core.schema import Risk

        risk_scores: Dict[str, Risk] = {}

        nodes = data.get("nodes", {})
        edges = data.get("edges", [])
        history = data.get("history", {})
        contracts = data.get("contracts", {})

        # Calculate fan-in for each node
        fan_in: Dict[str, int] = {}
        for edge in edges:
            edge_type = edge.get("type")
            if edge_type in ["calls", "imports"]:
                to_node = edge.get("to")
                fan_in[to_node] = fan_in.get(to_node, 0) + 1

        # Calculate risk for each node
        for node_id, node_data in nodes.items():
            reasons = []
            risk_score = 0.0

            # High fan-in increases risk
            node_fan_in = fan_in.get(node_id, 0)
            if node_fan_in > 5:
                reasons.append(f"High fan-in ({node_fan_in})")
                risk_score += min(0.4, node_fan_in / 20.0)

            # High churn increases risk
            hist_data = history.get(node_id, {})
            churn = hist_data.get("churn_score", 0.0)
            if churn > 0.7:
                reasons.append("High churn")
                risk_score += 0.3

            # Public API increases risk
            if node_id in contracts:
                reasons.append("Public API")
                risk_score += 0.2

            # Low test coverage (would need test data)
            # This is a placeholder

            risk_score = min(1.0, risk_score)

            if risk_score > 0 or reasons:
                risk_scores[node_id] = Risk(
                    risk_score=risk_score, reasons=reasons
                )

        return {k: v.model_dump() for k, v in risk_scores.items()}

