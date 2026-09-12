"""
main.py — Streamlit Application Entry Point
==============================================
This is the main file that runs the DRISHTI AI Data Analyst.

To run the application:
    streamlit run app/main.py

This file:
  1. Sets up the Streamlit page with multi-page navigation
  2. Routes between Ask Questions, Upload Dataset, and My Datasets
  3. Handles user input (new questions AND follow-ups)
  4. Calls the orchestrator to process questions
  5. Manages conversation context and dataset switching
  6. Displays the results and conversation history
"""

import streamlit as st
from app.ui.dashboard import (
    setup_page,
    render_header,
    render_question_input,
    render_status_pipeline,
    render_results,
    render_conversation_history,
    render_followup_input,
    render_dataset_metadata,
)
from app.agent.orchestrator import process_question
from app.agent.context_manager import (
    init_conversation,
    clear_conversation,
    is_followup,
    add_turn,
    get_context_for_llm,
    get_conversation_results,
    get_active_dataset_id,
    set_active_dataset,
)
from app.database.connection import test_connection


def _run_pipeline(question: str, conversation_context: str = None):
    """
    Run the analysis pipeline for a question (new or follow-up).

    Args:
        question: The user's question
        conversation_context: Optional context string for follow-ups
    """
    # Create a status container for the pipeline display
    status_container = st.empty()
    result_container = st.container()

    # Status callback — updates the pipeline display in real-time
    def update_status(stage, details=""):
        with status_container.container():
            render_status_pipeline(stage)
            if details and stage != "Complete":
                st.caption(f"_{details}_")

    # Get the active dataset
    dataset_id = get_active_dataset_id()

    # Run the full agent pipeline
    with st.spinner("Processing your question..."):
        result = process_question(
            question,
            status_callback=update_status,
            conversation_context=conversation_context,
            dataset_id=dataset_id,
        )

    # Store result in session state for persistence
    st.session_state["result"] = result

    # Show final status
    with status_container.container():
        if result.get("needs_clarification") or result.get("out_of_scope"):
            render_status_pipeline("Complete")
        elif result["success"]:
            render_status_pipeline("Complete")
        else:
            render_status_pipeline("Failed")

    # If the result is a real analysis (not clarification/out-of-scope), save it
    if (result["success"]
            and not result.get("needs_clarification")
            and not result.get("out_of_scope")):
        add_turn(result)


def _get_active_dataset_meta():
    """
    Get the metadata dict for the active dataset, or None for the default taxi dataset.
    """
    dataset_id = get_active_dataset_id()
    if dataset_id is None:
        return None

    try:
        from app.data.dataset_registry import get_dataset
        return get_dataset(dataset_id)
    except Exception:
        return None


def _render_ask_page():
    """Render the Ask Questions page."""
    dataset_meta = _get_active_dataset_meta()

    # Render header and metadata based on active dataset
    if dataset_meta:
        render_header(dataset_name=dataset_meta["dataset_name"])
        render_dataset_metadata(dataset_meta=dataset_meta)

        # Generate suggested questions
        try:
            from app.data.schema_generator import generate_suggested_questions
            suggestions = generate_suggested_questions(dataset_meta)
        except Exception:
            suggestions = None
    else:
        render_header()
        render_dataset_metadata()
        suggestions = None

    # ---- Question Input ----
    question, ask_clicked = render_question_input(suggested_questions=suggestions)

    # ---- Process NEW Question ----
    if ask_clicked and question.strip():
        # Clear previous conversation — this is a brand new question
        clear_conversation()

        # Store the question in session state
        st.session_state["question_input"] = question

        # Run the pipeline
        _run_pipeline(question)

    # ---- Display Conversation History ----
    conv_results = get_conversation_results()
    if len(conv_results) > 1:
        # Show all turns EXCEPT the latest (which is rendered by render_results)
        render_conversation_history(conv_results[:-1])

    # ---- Display Latest Result ----
    if "result" in st.session_state and st.session_state["result"]:
        result = st.session_state["result"]

        # Show turn indicator for follow-ups
        if len(conv_results) > 1:
            turn_num = len(conv_results)
            st.markdown(
                f'<div class="card-header">📍 Turn {turn_num}: {result.get("question", "")}</div>',
                unsafe_allow_html=True,
            )
        elif len(conv_results) == 1:
            st.markdown(
                f'<div class="card-header">📍 {result.get("question", "")}</div>',
                unsafe_allow_html=True,
            )

        render_results(result)

        # ---- Follow-up Section ----
        # Show follow-up input if we have a successful result (or clarification/out-of-scope)
        if result.get("success") or result.get("needs_clarification") or result.get("out_of_scope"):
            followup_q, followup_clicked, new_analysis_clicked = render_followup_input()

            # Handle New Analysis
            if new_analysis_clicked:
                clear_conversation()
                st.session_state["result"] = None
                st.session_state["question_input"] = ""
                st.rerun()

            # Handle Follow-up Question
            if followup_clicked and followup_q.strip():
                # Build conversation context from history
                context = get_context_for_llm()

                # Run the pipeline with context
                _run_pipeline(followup_q, conversation_context=context)

                # Rerun to refresh the page with new results
                st.rerun()


def main():
    """Main application function."""

    # ---- Page Setup ----
    setup_page()

    # ---- Initialize Conversation ----
    init_conversation()

    # ---- Database Connection Check ----
    if "db_connected" not in st.session_state:
        with st.spinner("Checking database connection..."):
            connected, msg = test_connection()
            st.session_state["db_connected"] = connected
            st.session_state["db_message"] = msg

    if not st.session_state["db_connected"]:
        st.error(
            f"⚠️ **Database Not Connected**\n\n"
            f"{st.session_state['db_message']}\n\n"
            f"Please make sure PostgreSQL is running and the `.env` file is configured correctly. "
            f"See the README for setup instructions."
        )
        st.stop()

    # ---- Sidebar Navigation ----
    st.sidebar.success("✅ Database connected")
    st.sidebar.caption(st.session_state["db_message"])

    st.sidebar.markdown("---")

    # Navigation
    default_page = st.session_state.get("nav_page", "ask")
    page_options = ["🔍 Ask Questions", "📤 Upload Dataset", "📊 My Datasets"]
    page_index = {"ask": 0, "upload": 1, "datasets": 2}.get(default_page, 0)

    page = st.sidebar.radio(
        "Navigation",
        page_options,
        index=page_index,
        key="nav_radio",
    )

    # Show active dataset in sidebar
    st.sidebar.markdown("---")
    dataset_id = get_active_dataset_id()
    if dataset_id:
        try:
            from app.data.dataset_registry import get_dataset
            ds = get_dataset(dataset_id)
            if ds:
                st.sidebar.info(f"📊 **Active:** {ds['dataset_name']}")
            else:
                st.sidebar.info("🚕 **Active:** NYC Yellow Taxi")
        except Exception:
            st.sidebar.info("🚕 **Active:** NYC Yellow Taxi")
    else:
        st.sidebar.info("🚕 **Active:** NYC Yellow Taxi")

    # Show conversation turn count
    conv_results = get_conversation_results()
    if conv_results:
        st.sidebar.caption(f"💬 Conversation: {len(conv_results)} turn(s)")

    # ---- Page Routing ----
    if page == "🔍 Ask Questions":
        st.session_state["nav_page"] = "ask"
        _render_ask_page()

    elif page == "📤 Upload Dataset":
        st.session_state["nav_page"] = "upload"
        from app.ui.upload_page import render_upload_page
        render_upload_page()

    elif page == "📊 My Datasets":
        st.session_state["nav_page"] = "datasets"
        from app.ui.data_explorer import render_data_explorer
        render_data_explorer()


# Run the app
if __name__ == "__main__":
    main()
