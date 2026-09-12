"""
data_explorer.py — Dataset Explorer & Manager
================================================
Streamlit page for viewing, exploring, and deleting
uploaded datasets.

Shows:
  - List of all uploaded datasets
  - Dataset details (schema, stats, preview)
  - Delete functionality with confirmation
"""

import streamlit as st
import pandas as pd

from app.data.dataset_registry import list_datasets, get_dataset, delete_dataset
from app.data.schema_generator import generate_suggested_questions
from app.agent.context_manager import set_active_dataset, get_active_dataset_id
from app.database.connection import get_engine
from sqlalchemy import text


def render_data_explorer():
    """Render the dataset explorer page."""

    st.markdown(
        '<h2 style="text-align:center; color:#667eea;">📊 My Datasets</h2>',
        unsafe_allow_html=True,
    )

    # Always show the built-in taxi dataset
    _render_default_dataset()

    st.markdown("---")

    # List uploaded datasets
    datasets = list_datasets()
    ready_datasets = [d for d in datasets if d["dataset_status"] == "ready"]

    if not ready_datasets:
        st.info("📁 No uploaded datasets yet. Go to **Upload Dataset** to add one.")
        return

    st.markdown(f"**Uploaded Datasets ({len(ready_datasets)})**")

    for ds in ready_datasets:
        _render_dataset_card(ds)


def _render_default_dataset():
    """Render the built-in NYC Taxi dataset card."""
    from app.config import DATASET_NAME, SOURCE_PERIOD, LOADED_ROW_COUNT, DATASET_MODE

    active_id = get_active_dataset_id()
    is_active = active_id is None

    border_color = "rgba(46,204,113,0.5)" if is_active else "rgba(102,126,234,0.2)"
    badge = '<span style="background:rgba(46,204,113,0.2); color:#2ecc71; padding:2px 8px; border-radius:10px; font-size:0.75rem;">● Active</span>' if is_active else ""

    st.markdown(
        f"""<div style="
            background: rgba(102,126,234,0.05);
            border: 1px solid {border_color};
            border-radius: 12px; padding: 16px 20px; margin: 8px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong style="color:#e0e0e0;">🚕 {DATASET_NAME}</strong> {badge}<br>
                    <span style="color:#888; font-size:0.85rem;">
                        {SOURCE_PERIOD} · {LOADED_ROW_COUNT:,} rows loaded · {DATASET_MODE}
                    </span>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    if not is_active:
        if st.button("Select NYC Taxi Dataset", key="select_taxi"):
            set_active_dataset(None)
            st.session_state["nav_page"] = "ask"
            st.rerun()


def _render_dataset_card(ds: dict):
    """Render a single uploaded dataset card with expand/delete options."""
    dataset_id = ds["dataset_id"]
    active_id = get_active_dataset_id()
    is_active = active_id == dataset_id

    border_color = "rgba(46,204,113,0.5)" if is_active else "rgba(102,126,234,0.2)"
    badge = ' <span style="background:rgba(46,204,113,0.2); color:#2ecc71; padding:2px 8px; border-radius:10px; font-size:0.75rem;">● Active</span>' if is_active else ""

    st.markdown(
        f"""<div style="
            background: rgba(102,126,234,0.05);
            border: 1px solid {border_color};
            border-radius: 12px; padding: 16px 20px; margin: 8px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong style="color:#e0e0e0;">📊 {ds['dataset_name']}</strong>{badge}<br>
                    <span style="color:#888; font-size:0.85rem;">
                        {ds['original_filename']} · {ds['row_count']:,} rows · {ds['column_count']} columns
                        {(' · ' + ds['date_range']) if ds.get('date_range') else ''}
                    </span>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Action buttons
    col1, col2, col3 = st.columns([1.2, 1.2, 1.2])
    with col1:
        if not is_active:
            if st.button("🔍 Select", key=f"select_{dataset_id}", use_container_width=True):
                set_active_dataset(dataset_id)
                st.session_state["nav_page"] = "ask"
                st.rerun()
        else:
            st.button("✅ Active", key=f"active_{dataset_id}", disabled=True, use_container_width=True)

    with col2:
        if st.button("👁️ Preview", key=f"preview_{dataset_id}", use_container_width=True):
            st.session_state[f"show_preview_{dataset_id}"] = not st.session_state.get(f"show_preview_{dataset_id}", False)
            st.rerun()

    with col3:
        if st.button("🗑️ Delete", key=f"delete_{dataset_id}", use_container_width=True):
            st.session_state[f"confirm_delete_{dataset_id}"] = True
            st.rerun()

    # Delete confirmation
    if st.session_state.get(f"confirm_delete_{dataset_id}"):
        st.warning(f"⚠️ Are you sure you want to delete **{ds['dataset_name']}**? This cannot be undone.")
        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            if st.button("Yes, delete", key=f"confirm_yes_{dataset_id}", type="primary"):
                # If this was the active dataset, switch to taxi
                if is_active:
                    set_active_dataset(None)
                delete_dataset(dataset_id)
                st.session_state.pop(f"confirm_delete_{dataset_id}", None)
                st.success(f"✅ Deleted: {ds['dataset_name']}")
                st.rerun()
        with c2:
            if st.button("Cancel", key=f"confirm_no_{dataset_id}"):
                st.session_state.pop(f"confirm_delete_{dataset_id}", None)
                st.rerun()

    # Preview panel
    if st.session_state.get(f"show_preview_{dataset_id}"):
        _render_dataset_preview(ds)


def _render_dataset_preview(ds: dict):
    """Render a detailed preview of a dataset."""
    with st.expander(f"📋 {ds['dataset_name']} — Details", expanded=True):
        # Schema table
        schema_meta = ds.get("schema_metadata", [])
        if schema_meta:
            schema_data = []
            for col in schema_meta:
                schema_data.append({
                    "Column": col.get("db_name", ""),
                    "Original Name": col.get("original_name", ""),
                    "Type": col.get("col_type", ""),
                    "PostgreSQL Type": col.get("pg_type", ""),
                    "Nullable": "Yes" if col.get("nullable") else "No",
                })
            st.dataframe(
                pd.DataFrame(schema_data),
                use_container_width=True,
                hide_index=True,
            )

        # Sample rows from the actual database table
        try:
            engine = get_engine()
            with engine.connect() as conn:
                result = conn.execute(text(
                    f'SELECT * FROM "{ds["table_name"]}" LIMIT 10'
                ))
                rows = result.fetchall()
                columns = list(result.keys())
                sample_df = pd.DataFrame(rows, columns=columns)

            st.markdown("**Sample Data (10 rows)**")
            st.dataframe(sample_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"Could not load preview: {str(e)}")

        # Suggested questions
        try:
            suggestions = generate_suggested_questions(ds)
            st.markdown("**💡 Suggested questions:**")
            for q in suggestions:
                st.markdown(f"- {q}")
        except Exception:
            pass
