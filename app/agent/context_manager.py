"""
context_manager.py — Conversation Context Manager
=====================================================
Manages conversation state for follow-up questions using
Streamlit session state.

Stores per-turn data with sensible size limits so that
follow-up questions can reference previous analyses without
sending unlimited history to Gemini.

Size limits:
  - Max 5 turns stored in conversation history
  - Max 50 rows stored per turn (for context, not display)
  - Max 10 rows sent to Gemini per previous turn
  - Older turns beyond 5 are discarded
"""

import streamlit as st
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# ---- Configuration ----
MAX_CONVERSATION_TURNS = 5     # Max turns kept in history
MAX_ROWS_PER_TURN = 50         # Max result rows stored per turn
MAX_ROWS_FOR_LLM = 10          # Max result rows sent to Gemini per turn


@dataclass
class ConversationTurn:
    """Stores the data for a single analysis turn."""
    turn_number: int
    question: str
    sql: str = ""
    sql_explanation: str = ""
    columns: list = field(default_factory=list)
    result_summary: str = ""          # Text representation of result (limited rows)
    row_count: int = 0
    explanation: str = ""
    viz_meta: dict = field(default_factory=dict)
    retry_history: list = field(default_factory=list)


def init_conversation():
    """
    Initialize conversation state in Streamlit session state.
    Call this once at app startup. Safe to call multiple times.
    """
    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []
    if "conversation_results" not in st.session_state:
        # Stores full result dicts for rendering history
        st.session_state["conversation_results"] = []
    if "active_dataset_id" not in st.session_state:
        st.session_state["active_dataset_id"] = None  # None = default taxi


def clear_conversation():
    """
    Clear all conversation history. Called when user clicks 'New Analysis'.
    """
    st.session_state["conversation_history"] = []
    st.session_state["conversation_results"] = []
    st.session_state.pop("result", None)


def set_active_dataset(dataset_id: str):
    """
    Switch the active dataset. Clears all conversation context
    to prevent cross-dataset contamination.

    Args:
        dataset_id: The dataset ID, or None for the default taxi dataset
    """
    current = st.session_state.get("active_dataset_id")
    if current != dataset_id:
        clear_conversation()
        st.session_state["active_dataset_id"] = dataset_id


def get_active_dataset_id() -> str | None:
    """
    Get the currently active dataset ID.

    Returns:
        str or None: Dataset ID, or None if using the default taxi dataset
    """
    return st.session_state.get("active_dataset_id", None)


def is_followup() -> bool:
    """
    Returns True if there is at least one prior turn in the conversation.
    """
    return len(st.session_state.get("conversation_history", [])) > 0


def get_turn_count() -> int:
    """
    Returns the number of turns completed so far.
    """
    return len(st.session_state.get("conversation_history", []))


def add_turn(result: dict):
    """
    Add a completed analysis turn to conversation history.

    Args:
        result: The full result dict from orchestrator.process_question()
    """
    init_conversation()

    history = st.session_state["conversation_history"]
    results = st.session_state["conversation_results"]

    turn_number = len(history) + 1

    # Build a compact text summary of the result data
    df = result.get("data")
    result_summary = _summarize_dataframe(df)
    columns = result.get("columns", [])

    turn = ConversationTurn(
        turn_number=turn_number,
        question=result.get("question", ""),
        sql=result.get("sql", ""),
        sql_explanation=result.get("sql_explanation", ""),
        columns=columns,
        result_summary=result_summary,
        row_count=result.get("row_count", 0),
        explanation=result.get("explanation", ""),
        viz_meta=result.get("viz_meta", {}),
        retry_history=result.get("retry_history", []),
    )

    history.append(turn)
    results.append(result)

    # Enforce max turns — discard oldest
    if len(history) > MAX_CONVERSATION_TURNS:
        st.session_state["conversation_history"] = history[-MAX_CONVERSATION_TURNS:]
        st.session_state["conversation_results"] = results[-MAX_CONVERSATION_TURNS:]


def get_conversation_results() -> list:
    """
    Returns the list of full result dicts for rendering conversation history.
    """
    return st.session_state.get("conversation_results", [])


def get_context_for_llm() -> Optional[str]:
    """
    Build a text context string from recent conversation history
    for inclusion in the Gemini prompt.

    Returns:
        str or None: The context string, or None if no history exists.
    """
    history = st.session_state.get("conversation_history", [])
    if not history:
        return None

    parts = []
    parts.append("CONVERSATION CONTEXT (previous analyses in this session):")
    parts.append("=" * 60)

    for turn in history:
        parts.append(f"\n--- Turn {turn.turn_number} ---")
        parts.append(f"User question: {turn.question}")
        parts.append(f"SQL used:\n{turn.sql}")
        parts.append(f"Result columns: {', '.join(turn.columns)}")
        parts.append(f"Result ({turn.row_count} rows):")

        # Include limited rows for context
        if turn.result_summary:
            # Limit to MAX_ROWS_FOR_LLM lines of data
            summary_lines = turn.result_summary.strip().split("\n")
            # First line is the header
            limited_lines = summary_lines[:MAX_ROWS_FOR_LLM + 1]
            parts.append("\n".join(limited_lines))
            if len(summary_lines) > MAX_ROWS_FOR_LLM + 1:
                parts.append(f"  ... ({turn.row_count} total rows)")
        else:
            parts.append("  (empty result)")

        if turn.explanation:
            # Include a brief excerpt of the explanation
            explanation_excerpt = turn.explanation[:500]
            if len(turn.explanation) > 500:
                explanation_excerpt += "..."
            parts.append(f"AI explanation excerpt: {explanation_excerpt}")

    parts.append("\n" + "=" * 60)
    return "\n".join(parts)


def _summarize_dataframe(df: pd.DataFrame) -> str:
    """
    Create a compact text summary of a DataFrame for storage.
    Limits to MAX_ROWS_PER_TURN rows.

    Args:
        df: The result DataFrame

    Returns:
        str: Text representation of the data
    """
    if df is None or df.empty:
        return ""

    # Limit rows
    limited_df = df.head(MAX_ROWS_PER_TURN)
    result_text = limited_df.to_string(index=False)

    return result_text
