"""
upload_page.py — Dataset Upload Page
=======================================
Streamlit page for uploading, profiling, and loading
user datasets into Supabase PostgreSQL.

Workflow:
  1. User uploads a file (CSV/Parquet/Excel)
  2. File is validated and profiled
  3. Quality report is shown
  4. User names the dataset and confirms
  5. Data is loaded into Supabase
  6. Post-load verification
  7. Dataset becomes available for querying
"""

import streamlit as st
import pandas as pd

from app.config import MAX_UPLOAD_SIZE_MB, MAX_UPLOAD_ROWS, SUPPORTED_FILE_TYPES
from app.data.dataset_profiler import (
    read_uploaded_file,
    profile_dataset,
    generate_quality_report,
)
from app.data.dataset_loader import load_dataset, verify_load
from app.data.dataset_registry import register_dataset, update_status
from app.data.schema_generator import generate_suggested_questions


def render_upload_page():
    """Render the complete upload page."""

    st.markdown(
        '<h2 style="text-align:center; color:#667eea;">📤 Upload Your Dataset</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center; color:#888;">'
        'Upload a structured file and start asking questions immediately.'
        '</p>',
        unsafe_allow_html=True,
    )

    # File type info
    st.markdown(
        f"""<div style="
            background: rgba(102,126,234,0.05);
            border: 1px solid rgba(102,126,234,0.2);
            border-radius: 12px; padding: 12px 20px; margin-bottom: 20px;
            text-align: center; color: #aaa; font-size: 0.9rem;">
            Supported: <strong>CSV</strong> · <strong>Parquet</strong> · <strong>Excel (.xlsx)</strong>
            &nbsp;|&nbsp; Max size: {MAX_UPLOAD_SIZE_MB} MB &nbsp;|&nbsp; Max rows: {MAX_UPLOAD_ROWS:,}
        </div>""",
        unsafe_allow_html=True,
    )

    # ---- File Upload ----
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=SUPPORTED_FILE_TYPES,
        key="dataset_upload",
        help=f"Max {MAX_UPLOAD_SIZE_MB} MB, up to {MAX_UPLOAD_ROWS:,} rows",
    )

    if uploaded_file is None:
        _render_empty_state()
        return

    # ---- Read & Validate ----
    if "upload_profile" not in st.session_state or st.session_state.get("upload_filename") != uploaded_file.name:
        with st.spinner("Reading and analyzing file..."):
            df, file_type, error = read_uploaded_file(uploaded_file)

        if error:
            st.error(f"❌ {error}")
            return

        profile = profile_dataset(df, uploaded_file.name, file_type)
        quality_report = generate_quality_report(df, profile)

        # Store in session state
        st.session_state["upload_df"] = df
        st.session_state["upload_profile"] = profile
        st.session_state["upload_quality"] = quality_report
        st.session_state["upload_filename"] = uploaded_file.name

    # Retrieve from session state
    df = st.session_state["upload_df"]
    profile = st.session_state["upload_profile"]
    quality_report = st.session_state["upload_quality"]

    # ---- Profile Summary ----
    _render_profile_summary(profile)

    # ---- Quality Report ----
    _render_quality_report(quality_report)

    # ---- Column Schema ----
    _render_column_schema(profile)

    # ---- Data Preview ----
    _render_data_preview(df)

    # ---- Load Section ----
    st.markdown("---")
    _render_load_section(df, profile, quality_report)


def _render_empty_state():
    """Show a placeholder when no file is uploaded."""
    st.markdown(
        """<div style="
            background: rgba(102,126,234,0.03);
            border: 2px dashed rgba(102,126,234,0.2);
            border-radius: 16px;
            padding: 60px 20px;
            text-align: center;
            color: #666;
            margin: 20px 0;">
            <p style="font-size: 3rem; margin: 0;">📁</p>
            <p style="font-size: 1.1rem; margin: 10px 0 5px;">
                Drag and drop a file here, or click <strong>Browse files</strong>
            </p>
            <p style="font-size: 0.85rem; color: #888;">
                Your data stays in your Supabase database. We never share it.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_profile_summary(profile: dict):
    """Show a card with row count, column count, date range."""
    date_info = profile.get("date_range") or "No date columns detected"

    st.markdown(
        f"""<div style="
            background: rgba(46,204,113,0.05);
            border: 1px solid rgba(46,204,113,0.2);
            border-radius: 12px; padding: 16px 20px; margin: 16px 0;
            display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div>
                <span style="font-size:0.75rem; text-transform:uppercase; color:#888;">File</span><br>
                <strong style="color:#e0e0e0;">{profile['filename']}</strong>
            </div>
            <div>
                <span style="font-size:0.75rem; text-transform:uppercase; color:#888;">Rows</span><br>
                <strong style="color:#e0e0e0;">{profile['row_count']:,}</strong>
            </div>
            <div>
                <span style="font-size:0.75rem; text-transform:uppercase; color:#888;">Columns</span><br>
                <strong style="color:#e0e0e0;">{profile['column_count']}</strong>
            </div>
            <div>
                <span style="font-size:0.75rem; text-transform:uppercase; color:#888;">Date Range</span><br>
                <strong style="color:#e0e0e0;">{date_info}</strong>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_quality_report(quality_report: list):
    """Show the quality checklist."""
    with st.expander("🔍 Data Quality Report", expanded=True):
        for check in quality_report:
            icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(check["status"], "❓")
            st.markdown(f"{icon} **{check['check']}** — {check['detail']}")


def _render_column_schema(profile: dict):
    """Show the detected column schema as a table."""
    with st.expander("📋 Detected Schema", expanded=False):
        schema_data = []
        for col in profile["columns"]:
            schema_data.append({
                "Original Name": col["original_name"],
                "Database Name": col["db_name"],
                "Type": col["col_type"],
                "Nulls": f"{col['null_count']:,} ({col['null_pct']}%)",
                "Unique": f"{col['unique_count']:,}",
            })
        schema_df = pd.DataFrame(schema_data)
        st.dataframe(schema_df, use_container_width=True, hide_index=True)


def _render_data_preview(df: pd.DataFrame):
    """Show first 10 rows of the data."""
    with st.expander("👁️ Data Preview (first 10 rows)", expanded=False):
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)


def _render_load_section(df: pd.DataFrame, profile: dict, quality_report: list):
    """Render the dataset naming and load button."""
    # Check if already loaded in this session
    if st.session_state.get("upload_complete"):
        _render_post_load_summary()
        return

    # Dataset name input
    default_name = profile["filename"].rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    dataset_name = st.text_input(
        "Dataset name:",
        value=default_name,
        key="dataset_name_input",
        help="Give your dataset a descriptive name.",
    )

    # Load button
    if st.button("🚀 Load into Database", type="primary", use_container_width=True):
        if not dataset_name.strip():
            st.error("Please enter a dataset name.")
            return

        _execute_load(df, profile, quality_report, dataset_name.strip())


def _execute_load(df: pd.DataFrame, profile: dict, quality_report: list, dataset_name: str):
    """Execute the full load pipeline with progress tracking."""

    progress_bar = st.progress(0, text="Registering dataset...")

    # Step 1: Register in the dataset table
    try:
        dataset_id, table_name = register_dataset(
            dataset_name=dataset_name,
            original_filename=profile["filename"],
            file_type=profile["file_type"],
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            schema_metadata=profile["column_mapping"],
            quality_report=quality_report,
            date_range=profile.get("date_range"),
        )
    except Exception as e:
        st.error(f"❌ Registration failed: {str(e)}")
        return

    progress_bar.progress(10, text="Creating table and loading data...")

    # Step 2: Load data into Supabase
    def progress_callback(current, total):
        pct = int(10 + (current / total) * 70)
        progress_bar.progress(pct, text=f"Loading rows... {current:,} / {total:,}")

    load_result = load_dataset(
        df=df,
        table_name=table_name,
        column_mapping=profile["column_mapping"],
        progress_callback=progress_callback,
    )

    if not load_result["success"]:
        update_status(dataset_id, "failed")
        st.error(f"❌ Load failed: {load_result['error']}")
        return

    progress_bar.progress(85, text="Verifying load...")

    # Step 3: Verify
    verification = verify_load(table_name, profile["row_count"], profile["column_count"])

    if not verification["success"]:
        update_status(dataset_id, "failed")
        for err in verification["errors"]:
            st.error(f"❌ {err}")
        return

    # Step 4: Mark as ready
    update_status(dataset_id, "ready")
    progress_bar.progress(100, text="✅ Complete!")

    # Store completion state
    st.session_state["upload_complete"] = True
    st.session_state["upload_dataset_id"] = dataset_id
    st.session_state["upload_dataset_name"] = dataset_name
    st.session_state["upload_table_name"] = table_name
    st.session_state["upload_verification"] = verification

    st.rerun()


def _render_post_load_summary():
    """Render the success summary after a dataset is loaded."""
    dataset_id = st.session_state.get("upload_dataset_id", "")
    dataset_name = st.session_state.get("upload_dataset_name", "")
    profile = st.session_state.get("upload_profile", {})
    verification = st.session_state.get("upload_verification", {})

    st.success(f"✅ **Dataset Ready: {dataset_name}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rows Loaded", f"{verification.get('actual_rows', 0):,}")
    with col2:
        st.metric("Columns", f"{verification.get('actual_columns', 0)}")
    with col3:
        date_range = profile.get("date_range", "N/A")
        st.metric("Date Range", date_range if date_range else "N/A")

    # Suggested questions
    try:
        from app.data.dataset_registry import get_dataset
        metadata = get_dataset(dataset_id)
        if metadata:
            suggestions = generate_suggested_questions(metadata)
            st.markdown("**💡 Suggested questions:**")
            for q in suggestions:
                st.markdown(f"- {q}")
    except Exception:
        pass

    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Ask Questions", type="primary", use_container_width=True):
            from app.agent.context_manager import set_active_dataset
            set_active_dataset(dataset_id)
            st.session_state["nav_page"] = "ask"
            # Clear upload state for next upload
            _clear_upload_state()
            st.rerun()
    with col2:
        if st.button("📤 Upload Another", use_container_width=True):
            _clear_upload_state()
            st.rerun()


def _clear_upload_state():
    """Clear upload-related session state for a fresh upload."""
    keys = [
        "upload_df", "upload_profile", "upload_quality",
        "upload_filename", "upload_complete", "upload_dataset_id",
        "upload_dataset_name", "upload_table_name", "upload_verification",
    ]
    for key in keys:
        st.session_state.pop(key, None)
