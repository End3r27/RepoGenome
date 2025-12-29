"""
IntentAtlas subsystem - Domain concept extraction.

Analyzes code organization, naming patterns, and extracts domain concepts.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from repogenome.core.schema import Concept
from repogenome.subsystems.base import Subsystem


class IntentAtlas(Subsystem):
    """Extract domain concepts and responsibilities."""

    def __init__(self):
        """Initialize IntentAtlas."""
        super().__init__("intentatlas")
        self.depends_on_subsystems = ["repospider"]

    def analyze(
        self, repo_path: Path, existing_genome: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract domain concepts.

        Args:
            repo_path: Path to repository root
            existing_genome: Optional existing genome

        Returns:
            Dictionary with concepts
        """
        concepts: Dict[str, Concept] = {}

        if not existing_genome:
            return {"concepts": {}}

        nodes = existing_genome.get("nodes", {})

        # Extract concepts from directory structure
        directory_concepts = self._extract_from_directories(repo_path, nodes)

        # Extract concepts from naming patterns
        naming_concepts = self._extract_from_naming(nodes)

        # Extract concepts from README/docs
        doc_concepts = self._extract_from_docs(repo_path)

        # Merge concepts
        all_concept_names = set(directory_concepts.keys()) | set(
            naming_concepts.keys()
        ) | set(doc_concepts.keys())

        for concept_name in all_concept_names:
            concept_nodes: Set[str] = set()
            descriptions: List[str] = []

            # Merge nodes from all sources
            if concept_name in directory_concepts:
                concept_nodes.update(directory_concepts[concept_name]["nodes"])
                if directory_concepts[concept_name].get("description"):
                    descriptions.append(
                        directory_concepts[concept_name]["description"]
                    )

            if concept_name in naming_concepts:
                concept_nodes.update(naming_concepts[concept_name]["nodes"])
                if naming_concepts[concept_name].get("description"):
                    descriptions.append(
                        naming_concepts[concept_name]["description"]
                    )

            if concept_name in doc_concepts:
                concept_nodes.update(doc_concepts[concept_name]["nodes"])
                if doc_concepts[concept_name].get("description"):
                    descriptions.append(
                        doc_concepts[concept_name]["description"]
                    )

            concepts[concept_name] = Concept(
                nodes=list(concept_nodes),
                description="; ".join(descriptions) if descriptions else None,
            )

        return {"concepts": {k: v.model_dump() for k, v in concepts.items()}}

    def _extract_from_directories(
        self, repo_path: Path, nodes: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract concepts from directory structure."""
        concepts: Dict[str, Dict[str, Any]] = {}

        # Common domain patterns
        domain_patterns = [
            "auth",
            "user",
            "payment",
            "order",
            "product",
            "notification",
            "email",
            "api",
            "database",
            "config",
            "util",
            "model",
            "view",
            "controller",
            "service",
            "handler",
        ]

        # Group nodes by directory
        directory_groups: Dict[str, List[str]] = {}

        for node_id, node_data in nodes.items():
            file_path = node_data.get("file")
            if not file_path:
                continue

            # Extract directory name
            file_path_obj = Path(file_path)
            directory_parts = file_path_obj.parts[:-1]  # Exclude filename

            # Check for domain keywords in directory
            for part in directory_parts:
                part_lower = part.lower()
                for pattern in domain_patterns:
                    if pattern in part_lower:
                        if pattern not in directory_groups:
                            directory_groups[pattern] = []
                        directory_groups[pattern].append(node_id)

        # Create concepts from directory groups
        for domain, node_list in directory_groups.items():
            if len(node_list) >= 2:  # Only create concept if multiple nodes
                concepts[domain] = {
                    "nodes": node_list,
                    "description": f"Domain: {domain}",
                }

        return concepts

    def _extract_from_naming(
        self, nodes: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract concepts from naming patterns."""
        concepts: Dict[str, Dict[str, Any]] = {}

        # Common prefixes/suffixes that indicate domains
        domain_patterns = {
            "auth": [r"auth", r"login", r"logout", r"session", r"token"],
            "user": [r"user", r"account", r"profile"],
            "payment": [r"payment", r"pay", r"billing", r"invoice", r"charge"],
            "order": [r"order", r"purchase", r"checkout"],
            "product": [r"product", r"item", r"catalog"],
            "notification": [r"notification", r"notify", r"alert", r"message"],
            "email": [r"email", r"mail", r"send"],
        }

        for domain, patterns in domain_patterns.items():
            matching_nodes: List[str] = []

            for node_id, node_data in nodes.items():
                # Check node ID and file name
                node_id_lower = node_id.lower()
                file_path = node_data.get("file", "").lower()

                for pattern in patterns:
                    if re.search(pattern, node_id_lower) or re.search(
                        pattern, file_path
                    ):
                        matching_nodes.append(node_id)
                        break

            if matching_nodes:
                concepts[domain] = {
                    "nodes": matching_nodes,
                    "description": f"Domain identified from naming: {domain}",
                }

        return concepts

    def _extract_from_docs(self, repo_path: Path) -> Dict[str, Dict[str, Any]]:
        """Extract concepts from documentation."""
        concepts: Dict[str, Dict[str, Any]] = {}

        # Read README files
        readme_paths = [
            repo_path / "README.md",
            repo_path / "README.txt",
            repo_path / "docs" / "README.md",
        ]

        for readme_path in readme_paths:
            if readme_path.exists():
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        content = f.read().lower()

                    # Extract domain keywords from README
                    domain_keywords = [
                        "authentication",
                        "authorization",
                        "payment",
                        "user",
                        "order",
                        "product",
                    ]

                    for keyword in domain_keywords:
                        if keyword in content:
                            # This is a simplified extraction
                            # Full implementation would map to actual nodes
                            pass

                except Exception:
                    pass

        return concepts

