"""
dashboard.py — Streamlit UI Components
=========================================
Contains all the UI rendering functions for the
AI Taxi Database Analyst application.

This module is imported by main.py and provides:
  - Page configuration and styling
  - Question input section
  - Processing status display
  - Results display (SQL, table, chart, explanation)
  - Error/retry information display
  - Conversation history display
  - Follow-up question input
  - New analysis button
"""

import streamlit as st
import pandas as pd


def setup_page():
    """Configure the Streamlit page settings and apply custom CSS."""
    st.set_page_config(
        page_title="AI Taxi Database Analyst",
        page_icon="🚕",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Custom CSS for a premium dark theme look
    st.markdown("""
    <style>
        /* ---- Import Google Font ---- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* ---- Global Styles ---- */
        .stApp {
            font-family: 'Inter', sans-serif;
        }

        /* ---- Main Title ---- */
        .main-title {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2.8rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 0;
            letter-spacing: -0.5px;
        }

        .subtitle {
            text-align: center;
            color: #888;
            font-size: 1.1rem;
            margin-top: -10px;
            margin-bottom: 20px;
            font-weight: 300;
        }

        /* ---- Dataset Metadata Card ---- */
        .dataset-meta {
            background: rgba(102,126,234,0.05);
            border: 1px solid rgba(102,126,234,0.2);
            border-radius: 12px;
            padding: 15px 20px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }

        .meta-item {
            display: flex;
            flex-direction: column;
        }

        .meta-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #888;
            margin-bottom: 4px;
        }

        .meta-value {
            font-size: 0.95rem;
            font-weight: 500;
            color: #e0e0e0;
        }

        .meta-status {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            background: rgba(243,156,18,0.15);
            border: 1px solid rgba(243,156,18,0.3);
            color: #f39c12;
            font-size: 0.8rem;
            font-weight: 600;
        }

        /* ---- Card Styles ---- */
        .result-card {
            background: linear-gradient(135deg, rgba(102,126,234,0.08) 0%, rgba(118,75,162,0.08) 100%);
            border: 1px solid rgba(102,126,234,0.2);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
        }

        .card-header {
            font-size: 1.1rem;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* ---- Status Pipeline ---- */
        .status-step {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin: 3px 4px;
            font-weight: 500;
        }

        .status-active {
            background: rgba(102,126,234,0.2);
            border: 1px solid rgba(102,126,234,0.4);
            color: #667eea;
            animation: pulse 1.5s infinite;
        }

        .status-done {
            background: rgba(46,204,113,0.15);
            border: 1px solid rgba(46,204,113,0.3);
            color: #2ecc71;
        }

        .status-pending {
            background: rgba(150,150,150,0.1);
            border: 1px solid rgba(150,150,150,0.2);
            color: #666;
        }

        .status-error {
            background: rgba(231,76,60,0.15);
            border: 1px solid rgba(231,76,60,0.3);
            color: #e74c3c;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }

        /* ---- SQL Code Block ---- */
        .sql-display {
            background: #1a1b2e;
            border: 1px solid rgba(102,126,234,0.3);
            border-radius: 12px;
            padding: 20px;
            font-family: 'Fira Code', 'Courier New', monospace;
            font-size: 0.9rem;
            overflow-x: auto;
            color: #e0e0e0;
        }

        /* ---- KPI Display ---- */
        .kpi-container {
            text-align: center;
            padding: 30px;
        }

        .kpi-value {
            font-size: 3.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .kpi-label {
            font-size: 1.2rem;
            color: #888;
            margin-top: 5px;
        }

        /* ---- Retry Badge ---- */
        .retry-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
            background: rgba(243,156,18,0.15);
            border: 1px solid rgba(243,156,18,0.3);
            color: #f39c12;
        }

        /* ---- Divider ---- */
        .section-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(102,126,234,0.3), transparent);
            margin: 30px 0;
        }

        /* ---- Example Questions ---- */
        .example-btn {
            background: rgba(102,126,234,0.1);
            border: 1px solid rgba(102,126,234,0.2);
            border-radius: 8px;
            padding: 8px 16px;
            color: #667eea;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.85rem;
        }

        .example-btn:hover {
            background: rgba(102,126,234,0.2);
            border-color: rgba(102,126,234,0.4);
        }

        /* ---- Conversation History ---- */
        .conversation-turn {
            background: linear-gradient(135deg, rgba(102,126,234,0.05) 0%, rgba(118,75,162,0.05) 100%);
            border: 1px solid rgba(102,126,234,0.15);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 16px;
        }

        .conversation-turn-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
        }

        .turn-number {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 50%;
            width: 28px;
            height: 28px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: 600;
            flex-shrink: 0;
        }

        .turn-question {
            font-weight: 500;
            color: #ccc;
            font-size: 0.95rem;
        }

        /* ---- Follow-up Section ---- */
        .followup-section {
            background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%);
            border: 1px solid rgba(102,126,234,0.25);
            border-radius: 16px;
            padding: 24px;
            margin-top: 20px;
        }

        .followup-header {
            font-size: 1.1rem;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* ---- Clarification / Out of Scope Cards ---- */
        .clarification-card {
            background: linear-gradient(135deg, rgba(243,156,18,0.1) 0%, rgba(241,196,15,0.05) 100%);
            border: 1px solid rgba(243,156,18,0.3);
            border-radius: 12px;
            padding: 20px;
            margin: 16px 0;
        }

        .out-of-scope-card {
            background: linear-gradient(135deg, rgba(231,76,60,0.1) 0%, rgba(192,57,43,0.05) 100%);
            border: 1px solid rgba(231,76,60,0.3);
            border-radius: 12px;
            padding: 20px;
            margin: 16px 0;
        }
    </style>
    """, unsafe_allow_html=True)


def render_header(dataset_name: str = None):
    """Render the application header."""
    if dataset_name:
        st.markdown(
            f'<h1 class="main-title">✨ DRISHTI — AI Data Analyst</h1>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="subtitle">Analyzing: {dataset_name}</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<h1 class="main-title">🚕 DRISHTI — AI Taxi Analyst</h1>', unsafe_allow_html=True)
        st.markdown(
            '<p class="subtitle">Ask questions about NYC Yellow Taxi trips in plain English — '
            'powered by AI and 3.7M trip records</p>',
            unsafe_allow_html=True,
        )


def render_dataset_metadata(dataset_meta: dict = None):
    """Render the dataset metadata card below the header."""
    if dataset_meta:
        # Uploaded dataset
        name = dataset_meta.get("dataset_name", "Dataset")
        row_count = dataset_meta.get("row_count", 0)
        col_count = dataset_meta.get("column_count", 0)
        date_range = dataset_meta.get("date_range", "N/A")
        status = dataset_meta.get("dataset_status", "ready")

        html = f"""
        <div class="dataset-meta">
            <div class="meta-item">
                <span class="meta-label">Dataset</span>
                <span class="meta-value">📊 {name}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Rows</span>
                <span class="meta-value">📊 {row_count:,}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Columns</span>
                <span class="meta-value">📋 {col_count}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Date Range</span>
                <span class="meta-value">📅 {date_range or 'N/A'}</span>
            </div>
        </div>
        """
    else:
        # Default taxi dataset
        from app.config import (
            DATASET_NAME,
            SOURCE_PERIOD,
            LOADED_ROW_COUNT,
            DATASET_MODE
        )

        html = f"""
        <div class="dataset-meta">
            <div class="meta-item">
                <span class="meta-label">Dataset</span>
                <span class="meta-value">🚕 {DATASET_NAME}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Period</span>
                <span class="meta-value">📅 {SOURCE_PERIOD}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Rows Loaded</span>
                <span class="meta-value">📊 {LOADED_ROW_COUNT:,}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Status</span>
                <span class="meta-status">⚠️ {DATASET_MODE}</span>
            </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)


def render_question_input(suggested_questions: list = None):
    """
    Render the question input section with example questions.

    Args:
        suggested_questions: Optional list of suggested questions for uploaded datasets.
                            If None, uses default taxi examples.

    Returns:
        tuple: (question: str, ask_clicked: bool)
    """
    # Example questions
    if suggested_questions:
        examples = suggested_questions[:6]
    else:
        examples = [
            "Which five pickup zones had the most taxi trips?",
            "What is the average fare amount by payment type?",
            "Show the busiest hours of the day for taxi pickups",
            "What is the average tip percentage by borough?",
            "How do trip distances vary across different boroughs?",
            "What were the total trips per day in January 2026?",
        ]

    # Example question buttons
    st.markdown("**💡 Try an example question:**")
    cols = st.columns(3)
    for i, example in enumerate(examples):
        with cols[i % 3]:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                st.session_state["question_input"] = example

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Question input
    question = st.text_area(
        "Ask a question about your data:",
        value=st.session_state.get("question_input", ""),
        height=80,
        placeholder="e.g., What is the total revenue by region?",
        key="question_text_area",
    )

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        ask_clicked = st.button("🔍 Ask", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state["question_input"] = ""
            st.session_state["result"] = None
            st.rerun()

    return question, ask_clicked


# Pipeline stage definitions
PIPELINE_STAGES = [
    ("Understanding question", "🧠"),
    ("Finding schema", "📋"),
    ("Generating SQL", "⚙️"),
    ("Validating SQL", "🔒"),
    ("Executing query", "▶️"),
    ("Validating result", "✅"),
    ("Generating visualization", "📊"),
    ("Writing explanation", "💬"),
    ("Complete", "🎉"),
]


def render_status_pipeline(current_stage: str):
    """
    Render the processing pipeline with stage indicators.

    Args:
        current_stage: The name of the currently active stage
    """
    stage_names = [s[0] for s in PIPELINE_STAGES]

    if current_stage in stage_names:
        current_idx = stage_names.index(current_stage)
    else:
        current_idx = -1

    html_parts = []
    for i, (name, icon) in enumerate(PIPELINE_STAGES):
        if i < current_idx:
            css_class = "status-done"
            display_icon = "✓"
        elif i == current_idx:
            css_class = "status-active"
            display_icon = icon
        else:
            css_class = "status-pending"
            display_icon = icon

        html_parts.append(
            f'<span class="status-step {css_class}">{display_icon} {name}</span>'
        )

    st.markdown(" ".join(html_parts), unsafe_allow_html=True)


def render_conversation_history(conversation_results: list):
    """
    Render previous conversation turns in a scrollable history.
    Does NOT render the latest turn — that is rendered by render_results().

    Args:
        conversation_results: List of result dicts from previous turns
    """
    if not conversation_results:
        return

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card-header">💬 Conversation History</div>', unsafe_allow_html=True)

    for i, result in enumerate(conversation_results):
        turn_num = i + 1

        with st.expander(f"Turn {turn_num}: {result.get('question', '')}", expanded=False):
            # Show the question
            st.markdown(f"**Question:** {result.get('question', '')}")

            # Show the chart if available
            if result.get("chart") is not None:
                st.plotly_chart(result["chart"], use_container_width=True, key=f"history_chart_{i}")

            # Show the data table (collapsed)
            df = result.get("data")
            if df is not None and not df.empty:
                st.dataframe(df, use_container_width=True, height=min(200, 40 + len(df) * 35),
                             key=f"history_df_{i}")

            # Show explanation excerpt
            if result.get("explanation"):
                explanation = result["explanation"]
                if len(explanation) > 400:
                    st.markdown(explanation[:400] + "...")
                else:
                    st.markdown(explanation)

            # Show the SQL
            if result.get("sql"):
                st.code(result["sql"], language="sql")


def render_results(result: dict):
    """
    Render the complete results section for the LATEST turn.

    Args:
        result: The result dict from orchestrator.process_question()
    """
    if not result:
        return

    # ---- Handle clarification requests ----
    if result.get("needs_clarification"):
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="clarification-card">'
            f'<strong>🤔 I need a bit more detail</strong><br><br>'
            f'{result.get("clarification_question", "Could you be more specific about what you would like to know?")}'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    # ---- Handle out-of-scope questions ----
    if result.get("out_of_scope"):
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="out-of-scope-card">'
            f'<strong>🌍 Outside Database Scope</strong><br><br>'
            f'{result.get("out_of_scope_explanation", "This question references data not available in the NYC taxi database.")}'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    if not result["success"]:
        render_error(result)
        return

    # ---- SQL Section ----
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="card-header">⚙️ Generated SQL</div>', unsafe_allow_html=True)
    with col2:
        if result["attempts"] > 1:
            st.markdown(
                f'<span class="retry-badge">🔄 {result["attempts"]} attempts</span>',
                unsafe_allow_html=True,
            )

    st.code(result["sql"], language="sql")

    if result.get("sql_explanation"):
        st.caption(f"💡 {result['sql_explanation']}")

    # ---- Data Table Section ----
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    if result.get("status") == "VALID_NO_MATCH":
        st.success("✓ Analysis completed — no single entity ranks highest on both metrics.")
    elif result.get("status") == "VALID_EMPTY_RESULT":
        st.info("ℹ️ Analysis completed — no records matched the requested criteria.")
        
    st.markdown(
        f'<div class="card-header">📊 Results ({result["row_count"]:,} rows)</div>',
        unsafe_allow_html=True,
    )

    df = result["data"]
    
    # Check for anomalies and unknowns
    has_anomaly = False
    has_unknown = False
    if df is not None and not df.empty:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                min_date = df[col].min()
                max_date = df[col].max()
                if pd.notna(min_date) and pd.notna(max_date):
                    if min_date < pd.Timestamp("2026-01-01") or max_date >= pd.Timestamp("2026-02-01"):
                        has_anomaly = True
            elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]):
                if df[col].isin(["Unknown", "None", "NaN", "N/A"]).any() or df[col].isna().any():
                    has_unknown = True
    
    if has_anomaly:
        st.warning("⚠ Data quality note: records outside the expected dataset date range were detected. Verify timestamp handling.")
        
    if has_unknown:
        st.info("ℹ️ Note: The results contain 'Unknown' or unmapped location categories based on the official taxi zones dataset.")

    st.dataframe(df, use_container_width=True, height=min(400, 40 + len(df) * 35))

    # ---- Visualization Section ----
    if result.get("chart") is not None:
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="card-header">📈 Visualization</div>', unsafe_allow_html=True)
        st.plotly_chart(result["chart"], use_container_width=True)

    # ---- Explanation Section ----
    if result.get("explanation"):
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="card-header">💬 AI Explanation</div>', unsafe_allow_html=True)
        st.markdown(result["explanation"])

    # ---- Retry History (if any retries occurred) ----
    if result["attempts"] > 1 and result.get("retry_history"):
        render_retry_history(result["retry_history"])


def render_followup_input():
    """
    Render the follow-up question input section below results.

    Returns:
        tuple: (followup_question: str, followup_clicked: bool, new_analysis_clicked: bool)
    """
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="followup-header">💬 Ask a follow-up question</div>',
        unsafe_allow_html=True,
    )

    # Show context hint
    history = st.session_state.get("conversation_history", [])
    if history:
        latest_turn = history[-1]
        st.caption(
            f"📌 Previous question: _{latest_turn.question}_ "
            f"({latest_turn.row_count} rows returned)"
        )

    followup_question = st.text_input(
        "Follow-up question:",
        value="",
        placeholder="e.g., What was their average fare?",
        key="followup_input",
        label_visibility="collapsed",
    )

    col1, col2, col3 = st.columns([1.2, 1.2, 3.6])
    with col1:
        followup_clicked = st.button(
            "💬 Ask Follow-up", type="primary", use_container_width=True
        )
    with col2:
        new_analysis_clicked = st.button(
            "🔄 New Analysis", use_container_width=True
        )

    return followup_question, followup_clicked, new_analysis_clicked


def render_error(result: dict):
    """Render an error message."""
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.error(f"❌ **Query Failed:** {result.get('error', 'Unknown error')}")

    if result.get("retry_history"):
        render_retry_history(result["retry_history"])


def render_retry_history(history: list):
    """Render the retry attempt history in a collapsible section."""
    with st.expander("🔄 Retry History (click to expand)"):
        for attempt in history:
            stage = attempt.get("stage", "Unknown")
            error = attempt.get("error", "")
            attempt_num = attempt.get("attempt", "?")

            if stage == "Success":
                st.success(f"**Attempt {attempt_num}:** ✅ Success ({attempt.get('row_count', 0)} rows)")
            else:
                st.warning(f"**Attempt {attempt_num}** — Failed at: {stage}")
                if error:
                    st.caption(error[:300])
