"""Cross-call context memory for persistent context sessions."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionMemory:
    """Manages persistent context sessions across MCP calls."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize session memory.
        
        Args:
            storage_dir: Optional storage directory for sessions
        """
        self.storage_dir = storage_dir or Path(".cache/context_sessions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(
        self,
        session_id: str,
        goal: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new context session.
        
        Args:
            session_id: Session identifier
            goal: Task goal
            initial_context: Optional initial context
            
        Returns:
            Session ID
        """
        session = {
            "session_id": session_id,
            "goal": goal,
            "context": initial_context or {},
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "call_count": 0,
        }
        
        self.active_sessions[session_id] = session
        self._save_session(session_id)
        
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session dictionary or None
        """
        # Try active sessions first
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["last_accessed"] = datetime.utcnow().isoformat()
            session["call_count"] = session.get("call_count", 0) + 1
            return session
        
        # Try loading from disk
        session = self._load_session(session_id)
        if session:
            self.active_sessions[session_id] = session
            session["last_accessed"] = datetime.utcnow().isoformat()
            session["call_count"] = session.get("call_count", 0) + 1
        
        return session

    def update_session(
        self,
        session_id: str,
        context: Dict[str, Any],
    ):
        """
        Update session with new context.
        
        Args:
            session_id: Session identifier
            context: Updated context
        """
        if session_id not in self.active_sessions:
            # Create new session if it doesn't exist
            self.create_session(session_id, context.get("goal", "unknown"), context)
            return
        
        session = self.active_sessions[session_id]
        session["context"] = context
        session["last_accessed"] = datetime.utcnow().isoformat()
        
        self._save_session(session_id)

    def list_sessions(self) -> List[str]:
        """
        List all session IDs.
        
        Returns:
            List of session IDs
        """
        # Get from active sessions
        session_ids = set(self.active_sessions.keys())
        
        # Get from disk
        for session_file in self.storage_dir.glob("*.json"):
            session_id = session_file.stem
            session_ids.add(session_id)
        
        return sorted(list(session_ids))

    def delete_session(self, session_id: str):
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
        """
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Delete from disk
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

    def _save_session(self, session_id: str):
        """Save session to disk."""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session_file = self.storage_dir / f"{session_id}.json"
        
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")

    def _load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session from disk."""
        session_file = self.storage_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

