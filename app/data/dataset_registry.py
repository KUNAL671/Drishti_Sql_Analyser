"""
dataset_registry.py — Dataset Registry (CRUD)
================================================
Manages the 'drishti_datasets' metadata table in Supabase.
Tracks all uploaded datasets: their IDs, table names, schemas,
quality reports, and lifecycle status.

Statuses: 'loading', 'ready', 'failed', 'deleted'
"""

import json
import uuid
from datetime import datetime

from sqlalchemy import text
from app.database.connection import get_engine
from app.config import DATASETS_TABLE


def _generate_dataset_id() -> str:
    """Generate a unique dataset ID like 'ds_a83f21'."""
    return "ds_" + uuid.uuid4().hex[:6]


def _generate_table_name(dataset_id: str) -> str:
    """Generate a safe PostgreSQL table name from a dataset ID."""
    return f"uploaded_ds_{dataset_id}"


def ensure_registry_table():
    """
    Create the drishti_datasets registry table if it doesn't exist.
    Safe to call multiple times.
    """
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DATASETS_TABLE} (
                dataset_id        VARCHAR(20)  PRIMARY KEY,
                dataset_name      VARCHAR(200) NOT NULL,
                original_filename VARCHAR(500) NOT NULL,
                table_name        VARCHAR(100) NOT NULL,
                file_type         VARCHAR(10)  NOT NULL,
                row_count         INTEGER      NOT NULL,
                column_count      INTEGER      NOT NULL,
                schema_metadata   JSONB        NOT NULL,
                quality_report    JSONB,
                date_range        VARCHAR(100),
                dataset_status    VARCHAR(20)  NOT NULL DEFAULT 'loading',
                created_at        TIMESTAMP    NOT NULL DEFAULT NOW()
            );
        """))


def register_dataset(
    dataset_name: str,
    original_filename: str,
    file_type: str,
    row_count: int,
    column_count: int,
    schema_metadata: list,
    quality_report: list = None,
    date_range: str = None,
) -> tuple:
    """
    Register a new dataset in the registry.

    Returns:
        tuple: (dataset_id: str, table_name: str)
    """
    ensure_registry_table()

    dataset_id = _generate_dataset_id()
    table_name = _generate_table_name(dataset_id)

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {DATASETS_TABLE}
                (dataset_id, dataset_name, original_filename, table_name,
                 file_type, row_count, column_count, schema_metadata,
                 quality_report, date_range, dataset_status)
            VALUES
                (:dataset_id, :dataset_name, :original_filename, :table_name,
                 :file_type, :row_count, :column_count, :schema_metadata,
                 :quality_report, :date_range, 'loading')
        """), {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "original_filename": original_filename,
            "table_name": table_name,
            "file_type": file_type,
            "row_count": row_count,
            "column_count": column_count,
            "schema_metadata": json.dumps(schema_metadata),
            "quality_report": json.dumps(quality_report) if quality_report else None,
            "date_range": date_range,
        })

    return dataset_id, table_name


def update_status(dataset_id: str, status: str):
    """Update the status of a dataset ('ready', 'failed', 'deleted')."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            UPDATE {DATASETS_TABLE}
            SET dataset_status = :status
            WHERE dataset_id = :dataset_id
        """), {"dataset_id": dataset_id, "status": status})


def get_dataset(dataset_id: str) -> dict | None:
    """
    Fetch a single dataset's metadata by ID.

    Returns:
        dict or None if not found
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT dataset_id, dataset_name, original_filename, table_name,
                   file_type, row_count, column_count, schema_metadata,
                   quality_report, date_range, dataset_status, created_at
            FROM {DATASETS_TABLE}
            WHERE dataset_id = :dataset_id
        """), {"dataset_id": dataset_id})
        row = result.fetchone()

    if row is None:
        return None

    return _row_to_dict(row)


def list_datasets() -> list:
    """
    List all non-deleted datasets, ordered by creation date descending.

    Returns:
        list of dicts
    """
    ensure_registry_table()

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT dataset_id, dataset_name, original_filename, table_name,
                   file_type, row_count, column_count, schema_metadata,
                   quality_report, date_range, dataset_status, created_at
            FROM {DATASETS_TABLE}
            WHERE dataset_status != 'deleted'
            ORDER BY created_at DESC
        """))
        rows = result.fetchall()

    return [_row_to_dict(row) for row in rows]


def delete_dataset(dataset_id: str) -> bool:
    """
    Soft-delete a dataset: set status to 'deleted' and drop the table.

    Returns:
        bool: True if successful
    """
    ds = get_dataset(dataset_id)
    if ds is None:
        return False

    engine = get_engine()
    table_name = ds["table_name"]

    with engine.begin() as conn:
        # Drop the uploaded data table
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        # Mark as deleted in registry
        conn.execute(text(f"""
            UPDATE {DATASETS_TABLE}
            SET dataset_status = 'deleted'
            WHERE dataset_id = :dataset_id
        """), {"dataset_id": dataset_id})

    return True


def _row_to_dict(row) -> dict:
    """Convert a database row to a dictionary."""
    schema_meta = row[7]
    quality_rep = row[8]

    # Handle JSONB — may already be dict/list or may be a string
    if isinstance(schema_meta, str):
        schema_meta = json.loads(schema_meta)
    if isinstance(quality_rep, str):
        quality_rep = json.loads(quality_rep)

    return {
        "dataset_id": row[0],
        "dataset_name": row[1],
        "original_filename": row[2],
        "table_name": row[3],
        "file_type": row[4],
        "row_count": row[5],
        "column_count": row[6],
        "schema_metadata": schema_meta,
        "quality_report": quality_rep,
        "date_range": row[9],
        "dataset_status": row[10],
        "created_at": str(row[11]),
    }
