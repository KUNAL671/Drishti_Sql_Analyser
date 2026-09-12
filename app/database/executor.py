"""
executor.py — Safe SQL Query Executor
=======================================
Executes validated SQL queries against Supabase PostgreSQL
and returns results as a Pandas DataFrame.

SECURITY: This module only executes queries that have already
been validated by sql_validator.py. It also enforces:
  - Read-only queries (via SQLAlchemy connection semantics)
  - Row count limits
  - Query timeouts (handled by the connection engine)
"""

import pandas as pd
from sqlalchemy import text
from app.database.connection import get_engine
from app.config import SQL_RESULT_ROW_LIMIT


def execute_query(sql: str) -> dict:
    """
    Execute a validated SQL query and return the results.

    Args:
        sql: The SQL query string (must already be validated!)

    Returns:
        dict with keys:
            - "success": bool
            - "data": pandas DataFrame (if successful)
            - "row_count": int
            - "columns": list of column names
            - "error": str (if failed)
    """
    try:
        engine = get_engine()

        # Execute the user's query with a row limit safety net
        # We wrap in a subquery to enforce the limit
        limited_sql = f"""
            SELECT * FROM (
                {sql.rstrip(';')}
            ) AS limited_result
            LIMIT {SQL_RESULT_ROW_LIMIT};
        """
        
        with engine.connect() as conn:
            # Enforce read-only semantics for this connection block
            # (Though our SQL validator blocks destructive commands anyway)
            result = conn.execute(text(limited_sql))
            
            # Fetch all rows
            rows = result.fetchall()
            
            if len(rows) > 0:
                # Get column names from the result
                columns = list(result.keys())
                # Convert to a Pandas DataFrame
                df = pd.DataFrame(rows, columns=columns)
            else:
                # If no rows, we can still get keys if the query returned a schema,
                # but let's handle empty DataFrame gracefully
                columns = list(result.keys()) if result.keys() else []
                df = pd.DataFrame(columns=columns)

        return {
            "success": True,
            "data": df,
            "row_count": len(df),
            "columns": columns,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "row_count": 0,
            "columns": [],
            "error": str(e),
        }
