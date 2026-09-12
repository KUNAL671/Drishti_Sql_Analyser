"""
schema.py — Database Schema Utilities
=======================================
Provides functions to retrieve the current Supabase PostgreSQL schema
(tables, columns, types, row counts) using SQLAlchemy.
"""

from sqlalchemy import text
from app.database.connection import get_engine


def get_schema_info():
    """
    Retrieve the complete schema of all user tables in the database.
    This is sent to the LLM so it knows what tables/columns are available.

    Returns:
        dict: Schema information
    """
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]

        schema = {}
        for table in tables:
            result = conn.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                ORDER BY ordinal_position;
            """), {"table_name": table})

            columns = []
            for row in result:
                columns.append({
                    "column": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                })
            schema[table] = columns

    return schema


def get_table_row_counts():
    """Get the number of rows in each table."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]

        counts = {}
        for table in tables:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}";'))
            counts[table] = result.scalar()

    return counts
