"""Semantic folding for code compression without information loss.

Converts raw code into semantic deltas (preconditions, postconditions, failure modes).
"""

import ast
import logging
import re
from typing import Any, Dict, List, Optional

from repogenome.core.schema import Node, NodeType

logger = logging.getLogger(__name__)


class SemanticFolder:
    """Folds code into semantic summaries to reduce token usage."""

    def __init__(self):
        """Initialize semantic folder."""
        self.supported_languages = ["python", "typescript", "javascript", "java", "go", "rust"]

    def fold_node(self, node: Node, node_id: str, source_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Fold a node into semantic summary.
        
        Args:
            node: Node to fold
            node_id: Node ID
            source_code: Optional source code for the node
            
        Returns:
            Semantic summary dictionary
        """
        if node.type.value != "function":
            # For non-functions, return basic summary
            return {
                "name": node_id.split(".")[-1] if "." in node_id else node_id,
                "type": node.type.value,
                "summary": node.summary or "",
            }
        
        semantic = {
            "name": node_id.split(".")[-1] if "." in node_id else node_id,
            "preconditions": [],
            "postconditions": [],
            "failure_modes": [],
        }
        
        # Extract from summary if available
        if node.summary:
            semantic.update(self._extract_from_summary(node.summary))
        
        # Extract from source code if available
        if source_code:
            semantic.update(self._extract_from_code(source_code, node.language))
        
        return semantic
    
    def _extract_from_summary(self, summary: str) -> Dict[str, Any]:
        """Extract semantic information from summary text."""
        result = {
            "preconditions": [],
            "postconditions": [],
            "failure_modes": [],
        }
        
        # Look for common patterns in summaries
        summary_lower = summary.lower()
        
        # Preconditions (requires, needs, expects)
        precond_patterns = [
            r"requires?\s+([^\.]+)",
            r"needs?\s+([^\.]+)",
            r"expects?\s+([^\.]+)",
            r"assumes?\s+([^\.]+)",
        ]
        for pattern in precond_patterns:
            matches = re.finditer(pattern, summary_lower, re.IGNORECASE)
            for match in matches:
                cond = match.group(1).strip()
                if cond and len(cond) < 100:
                    result["preconditions"].append(cond)
        
        # Postconditions (returns, sets, updates)
        postcond_patterns = [
            r"returns?\s+([^\.]+)",
            r"sets?\s+([^\.]+)",
            r"updates?\s+([^\.]+)",
            r"creates?\s+([^\.]+)",
        ]
        for pattern in postcond_patterns:
            matches = re.finditer(pattern, summary_lower, re.IGNORECASE)
            for match in matches:
                cond = match.group(1).strip()
                if cond and len(cond) < 100:
                    result["postconditions"].append(cond)
        
        # Failure modes (throws, errors, fails)
        failure_patterns = [
            r"throws?\s+([^\.]+)",
            r"errors?\s+([^\.]+)",
            r"fails?\s+([^\.]+)",
            r"raises?\s+([^\.]+)",
        ]
        for pattern in failure_patterns:
            matches = re.finditer(pattern, summary_lower, re.IGNORECASE)
            for match in matches:
                cond = match.group(1).strip()
                if cond and len(cond) < 100:
                    result["failure_modes"].append(cond)
        
        return result
    
    def _extract_from_code(self, source_code: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Extract semantic information from source code."""
        result = {
            "preconditions": [],
            "postconditions": [],
            "failure_modes": [],
        }
        
        if not language:
            return result
        
        lang_lower = language.lower()
        
        if lang_lower == "python":
            result.update(self._extract_python_semantics(source_code))
        elif lang_lower in ["typescript", "javascript"]:
            result.update(self._extract_js_semantics(source_code))
        # Add more language extractors as needed
        
        return result
    
    def _extract_python_semantics(self, code: str) -> Dict[str, Any]:
        """Extract semantic information from Python code."""
        result = {
            "preconditions": [],
            "postconditions": [],
            "failure_modes": [],
        }
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Extract assertions as preconditions
                if isinstance(node, ast.Assert):
                    if node.test:
                        precond = ast.unparse(node.test) if hasattr(ast, 'unparse') else str(node.test)
                        if len(precond) < 100:
                            result["preconditions"].append(precond)
                
                # Extract raise statements as failure modes
                if isinstance(node, ast.Raise):
                    if node.exc:
                        failure = ast.unparse(node.exc) if hasattr(ast, 'unparse') else str(node.exc)
                        if len(failure) < 100:
                            result["failure_modes"].append(failure)
                
                # Extract return type hints as postconditions
                if isinstance(node, ast.FunctionDef):
                    if node.returns:
                        postcond = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                        if len(postcond) < 100:
                            result["postconditions"].append(f"returns {postcond}")
        except SyntaxError as e:
            logger.debug(f"Failed to parse Python code for semantic extraction: {e}")
        except Exception as e:
            logger.debug(f"Error extracting Python semantics: {e}")
        
        return result
    
    def _extract_js_semantics(self, code: str) -> Dict[str, Any]:
        """Extract semantic information from JavaScript/TypeScript code."""
        result = {
            "preconditions": [],
            "postconditions": [],
            "failure_modes": [],
        }
        
        # Extract throw statements
        throw_pattern = r"throw\s+([^;]+)"
        for match in re.finditer(throw_pattern, code):
            failure = match.group(1).strip()
            if len(failure) < 100:
                result["failure_modes"].append(failure)
        
        # Extract return type annotations (TypeScript)
        return_type_pattern = r":\s*([A-Za-z<>\[\]|&]+)\s*=>"
        for match in re.finditer(return_type_pattern, code):
            postcond = match.group(1).strip()
            if len(postcond) < 100:
                result["postconditions"].append(f"returns {postcond}")
        
        return result
    
    def fold_nodes(self, nodes: Dict[str, Node], source_map: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fold multiple nodes into semantic summaries.
        
        Args:
            nodes: Dictionary of node_id -> Node
            source_map: Optional mapping of node_id -> source_code
            
        Returns:
            Dictionary of node_id -> semantic_summary
        """
        folded = {}
        
        for node_id, node in nodes.items():
            source_code = source_map.get(node_id) if source_map else None
            folded[node_id] = self.fold_node(node, node_id, source_code)
        
        return folded

