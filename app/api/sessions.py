"""
sessions.py — In-Memory Session Manager
==========================================
Replaces st.session_state for managing conversation context
in the FastAPI backend. Stores conversation history per
conversation_id so follow-up questions work correctly.

NOTE: This is in-memory storage. Sessions are lost on server restart.
For production, swap to Redis or a database-backed store.
"""

import uuid
import time
import pandas as pd
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ConversationSession:
    """A single conversation's state."""
    conversation_id: str
    dataset_id: str | None = None
    history: list = field(default_factory=list)
    results: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


class SessionManager:
    """
    Thread-safe in-memory session manager.
    Manages conversation state for multiple concurrent users.
    """

    def __init__(self, max_sessions: int = 1000, ttl_seconds: int = 3600):
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = Lock()
        self._max_sessions = max_sessions
        self._ttl = ttl_seconds

    def create_session(self, dataset_id: str | None = None) -> str:
        """Create a new conversation session and return its ID."""
        conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        session = ConversationSession(
            conversation_id=conversation_id,
            dataset_id=dataset_id,
        )

        with self._lock:
            self._cleanup_expired()
            self._sessions[conversation_id] = session

        return conversation_id

    def get_session(self, conversation_id: str) -> ConversationSession | None:
        """Get an existing session by ID."""
        with self._lock:
            session = self._sessions.get(conversation_id)
            if session:
                session.last_active = time.time()
            return session

    def add_turn(self, conversation_id: str, result: dict):
        """
        Add a completed analysis turn to the conversation history.

        Args:
            conversation_id: The conversation ID
            result: The orchestrator result dict
        """
        with self._lock:
            session = self._sessions.get(conversation_id)
            if not session:
                return

            session.last_active = time.time()

            # Store a summary of each turn (not the full result to save memory)
            df = result.get("data")
            result_summary = ""
            if df is not None and not df.empty:
                # Store up to 20 rows max in memory, though we may send fewer to LLM
                limited_df = df.head(20)
                result_summary = limited_df.to_string(index=False)

            turn = {
                "question": result.get("question", ""),
                "sql": result.get("sql", ""),
                "row_count": result.get("row_count", 0),
                "columns": result.get("columns", []),
                "success": result.get("success", False),
                "result_summary": result_summary,
            }
            session.history.append(turn)
            session.results.append(result)

    def get_context_for_llm(self, conversation_id: str, dataset_id: str | None = None) -> str | None:
        """
        Build a conversation context string for the LLM,
        matching the format used by the Streamlit context_manager.

        Returns:
            str or None if no prior turns exist or dataset changed
        """
        with self._lock:
            session = self._sessions.get(conversation_id)
            if not session or not session.history:
                return None

            # Prevent cross-dataset contamination
            if session.dataset_id != dataset_id:
                # Dataset changed! Discard context to prevent leakage.
                session.history = []
                session.results = []
                session.dataset_id = dataset_id
                return None

            context_parts = []
            for i, turn in enumerate(session.history, 1):
                context_parts.append(
                    f"Turn {i}:\n"
                    f"  Question: {turn['question']}\n"
                    f"  SQL: {turn['sql']}\n"
                    f"  Rows returned: {turn['row_count']}\n"
                    f"  Columns: {', '.join(turn['columns'])}"
                )
                if turn.get('result_summary'):
                    summary_lines = turn['result_summary'].strip().split('\n')
                    # Send header + up to 10 rows to LLM
                    limited_lines = summary_lines[:11]
                    context_parts.append("  Data Sample:")
                    context_parts.append("    " + "\n    ".join(limited_lines))
                    if len(summary_lines) > 11:
                        context_parts.append(f"    ... ({turn['row_count']} total rows)")

            return "\n\n".join(context_parts)

    def is_followup(self, conversation_id: str) -> bool:
        """Check if there is prior conversation history."""
        with self._lock:
            session = self._sessions.get(conversation_id)
            return bool(session and session.history)

    def delete_session(self, conversation_id: str):
        """Remove a session."""
        with self._lock:
            self._sessions.pop(conversation_id, None)

    def _cleanup_expired(self):
        """Remove expired sessions (called while holding the lock)."""
        now = time.time()
        expired = [
            cid for cid, session in self._sessions.items()
            if now - session.last_active > self._ttl
        ]
        for cid in expired:
            del self._sessions[cid]

        # Also enforce max sessions by removing oldest
        if len(self._sessions) >= self._max_sessions:
            oldest = sorted(
                self._sessions.items(),
                key=lambda x: x[1].last_active,
            )
            # Remove the oldest 10%
            to_remove = max(1, len(oldest) // 10)
            for cid, _ in oldest[:to_remove]:
                del self._sessions[cid]


# Global session manager instance
session_manager = SessionManager()
