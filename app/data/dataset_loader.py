"""
dataset_loader.py — Dataset Loader
=====================================
Handles safe table creation in Supabase PostgreSQL and
batch data insertion for uploaded datasets.

SECURITY: Only this module creates/drops uploaded dataset tables.
The AI agent NEVER has permission to execute DDL.
"""

import pandas as pd
from sqlalchemy import text
from app.database.connection import get_engine


def load_dataset(
    df: pd.DataFrame,
    table_name: str,
    column_mapping: list,
    progress_callback=None,
) -> dict:
    """
    Create a PostgreSQL table and load the DataFrame into it.

    Args:
        df: The source DataFrame
        table_name: The safe table name (e.g., 'uploaded_ds_ds_a83f21')
        column_mapping: List of column info dicts from the profiler
        progress_callback: Optional callback(current_rows, total_rows)

    Returns:
        dict: {"success": bool, "rows_loaded": int, "error": str or None}
    """
    engine = get_engine()

    try:
        # Step 1: Rename DataFrame columns to safe database names
        rename_map = {}
        for col_info in column_mapping:
            rename_map[col_info["original_name"]] = col_info["db_name"]

        df_safe = df.rename(columns=rename_map)

        # Step 2: Convert date columns before loading
        for col_info in column_mapping:
            if col_info["col_type"] == "date":
                db_name = col_info["db_name"]
                if db_name in df_safe.columns:
                    df_safe[db_name] = pd.to_datetime(
                        df_safe[db_name], errors="coerce", format="mixed"
                    )

        # Step 3: Drop table if it exists (safety for re-uploads)
        with engine.begin() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))

        # Step 4: Build CREATE TABLE statement for precise type control
        col_defs = []
        for col_info in column_mapping:
            nullable = "NULL" if col_info["nullable"] else "NOT NULL"
            col_defs.append(
                f'    "{col_info["db_name"]}" {col_info["pg_type"]} {nullable}'
            )

        create_sql = f'CREATE TABLE "{table_name}" (\n{",".join(col_defs)}\n);'

        with engine.begin() as conn:
            conn.execute(text(create_sql))

        # Step 5: Batch insert using pandas to_sql
        chunk_size = 5000
        total_rows = len(df_safe)

        # Use method='multi' for efficient batch inserts
        # We insert in chunks to allow progress tracking
        rows_loaded = 0
        for start in range(0, total_rows, chunk_size):
            chunk = df_safe.iloc[start:start + chunk_size]
            chunk.to_sql(
                name=table_name,
                con=engine,
                if_exists="append",
                index=False,
                method="multi",
            )
            rows_loaded += len(chunk)
            if progress_callback:
                progress_callback(rows_loaded, total_rows)

        return {
            "success": True,
            "rows_loaded": rows_loaded,
            "error": None,
        }

    except Exception as e:
        # Try to clean up the table if creation partially succeeded
        try:
            with engine.begin() as conn:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        except Exception:
            pass

        return {
            "success": False,
            "rows_loaded": 0,
            "error": str(e),
        }


def verify_load(table_name: str, expected_rows: int, expected_columns: int) -> dict:
    """
    Verify that a dataset was loaded correctly.

    Args:
        table_name: The database table name
        expected_rows: Expected number of rows
        expected_columns: Expected number of columns

    Returns:
        dict: {"success": bool, "actual_rows": int, "actual_columns": int,
               "sample": DataFrame, "errors": list}
    """
    engine = get_engine()
    errors = []

    try:
        with engine.connect() as conn:
            # Check row count
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            actual_rows = result.scalar()

            # Check column count
            result = conn.execute(text(f"""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
            """), {"table_name": table_name})
            actual_columns = result.scalar()

            # Sample rows
            result = conn.execute(text(
                f'SELECT * FROM "{table_name}" ORDER BY RANDOM() LIMIT 5'
            ))
            rows = result.fetchall()
            columns = list(result.keys())
            sample = pd.DataFrame(rows, columns=columns)

        if actual_rows != expected_rows:
            errors.append(
                f"Row count mismatch: expected {expected_rows:,}, got {actual_rows:,}."
            )

        if actual_columns != expected_columns:
            errors.append(
                f"Column count mismatch: expected {expected_columns}, got {actual_columns}."
            )

        return {
            "success": len(errors) == 0,
            "actual_rows": actual_rows,
            "actual_columns": actual_columns,
            "sample": sample,
            "errors": errors,
        }

    except Exception as e:
        return {
            "success": False,
            "actual_rows": 0,
            "actual_columns": 0,
            "sample": pd.DataFrame(),
            "errors": [f"Verification failed: {str(e)}"],
        }


def drop_dataset_table(table_name: str) -> bool:
    """
    Drop an uploaded dataset table. Only callable from application code.

    Args:
        table_name: The table name to drop

    Returns:
        bool: True if successful
    """
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        return True
    except Exception:
        return False
