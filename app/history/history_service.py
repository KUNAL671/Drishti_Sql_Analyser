"""
history_service.py — Query History Service
==========================================
Manages the 'analysis_history' table in Supabase.
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import text
import logging

from app.database.connection import get_engine

logger = logging.getLogger("drishti.history")

HISTORY_TABLE = "analysis_history"

def ensure_history_table():
    """Create the analysis_history table and necessary indexes if they don't exist."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {HISTORY_TABLE} (
                analysis_id         VARCHAR(50) PRIMARY KEY,
                conversation_id     VARCHAR(50),
                dataset_id          VARCHAR(50),
                dataset_name        VARCHAR(200) NOT NULL,
                question            TEXT NOT NULL,
                sql_query           TEXT,
                sql_explanation     TEXT,
                result_data         JSONB,
                result_columns      JSONB,
                visualization       JSONB,
                explanation         TEXT,
                validation          JSONB,
                retry_history       JSONB,
                rows_returned       INTEGER,
                attempts            INTEGER,
                execution_time_ms   INTEGER,
                status              VARCHAR(20) NOT NULL,
                error_message       TEXT,
                created_at          TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        
        # Indexes for frequent lookup patterns
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_history_dataset ON {HISTORY_TABLE}(dataset_id);"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_history_conversation ON {HISTORY_TABLE}(conversation_id);"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_history_created_at ON {HISTORY_TABLE}(created_at DESC);"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_history_status ON {HISTORY_TABLE}(status);"))
        
        logger.info(f"Ensured table {HISTORY_TABLE} exists.")


def generate_analysis_id() -> str:
    """Generate a unique ID for a historical analysis."""
    return f"ana_{uuid.uuid4().hex[:8]}"


def save_analysis(
    status: str,
    question: str,
    dataset_id: Optional[str] = None,
    dataset_name: str = "Active Dataset",
    conversation_id: Optional[str] = None,
    sql_query: Optional[str] = None,
    sql_explanation: Optional[str] = None,
    result_data: Optional[List[Dict[str, Any]]] = None,
    result_columns: Optional[List[str]] = None,
    visualization: Optional[Dict[str, Any]] = None,
    explanation: Optional[str] = None,
    validation: Optional[Dict[str, Any]] = None,
    retry_history: Optional[List[Dict[str, Any]]] = None,
    rows_returned: Optional[int] = 0,
    attempts: Optional[int] = 0,
    execution_time_ms: Optional[int] = 0,
    error_message: Optional[str] = None
) -> str:
    """Save an analysis attempt (success or failure) to history."""
    
    analysis_id = generate_analysis_id()
    engine = get_engine()
    
    # Cap result_data to avoid massive payloads, though it should be capped at 1000 anyway
    if result_data and len(result_data) > 1000:
        result_data = result_data[:1000]

    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO {HISTORY_TABLE} (
                analysis_id, conversation_id, dataset_id, dataset_name,
                question, sql_query, sql_explanation, result_data,
                result_columns, visualization, explanation, validation,
                retry_history, rows_returned, attempts, execution_time_ms,
                status, error_message
            ) VALUES (
                :analysis_id, :conversation_id, :dataset_id, :dataset_name,
                :question, :sql_query, :sql_explanation, :result_data,
                :result_columns, :visualization, :explanation, :validation,
                :retry_history, :rows_returned, :attempts, :execution_time_ms,
                :status, :error_message
            )
        """), {
            "analysis_id": analysis_id,
            "conversation_id": conversation_id,
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "question": question,
            "sql_query": sql_query,
            "sql_explanation": sql_explanation,
            "result_data": json.dumps(result_data) if result_data else None,
            "result_columns": json.dumps(result_columns) if result_columns else None,
            "visualization": json.dumps(visualization) if visualization else None,
            "explanation": explanation,
            "validation": json.dumps(validation) if validation else None,
            "retry_history": json.dumps(retry_history) if retry_history else None,
            "rows_returned": rows_returned,
            "attempts": attempts,
            "execution_time_ms": execution_time_ms,
            "status": status,
            "error_message": error_message
        })
        
    return analysis_id


def get_history(dataset_id: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """Retrieve history summary for the listing page."""
    engine = get_engine()
    
    # Base query does not select heavy fields like result_data or visualization
    base_query = f"""
        SELECT analysis_id, conversation_id, dataset_id, dataset_name, question, 
               rows_returned, attempts, execution_time_ms, status, error_message, created_at
        FROM {HISTORY_TABLE}
        WHERE 1=1
    """
    
    count_query = f"""
        SELECT COUNT(*) as total FROM {HISTORY_TABLE} WHERE 1=1
    """
    
    params = {"limit": limit, "offset": offset}
    
    if dataset_id and dataset_id.lower() != "all":
        base_query += " AND dataset_id = :dataset_id"
        count_query += " AND dataset_id = :dataset_id"
        params["dataset_id"] = dataset_id
        
    if status and status.lower() != "all":
        base_query += " AND status = :status"
        count_query += " AND status = :status"
        params["status"] = status
        
    if search:
        base_query += " AND question ILIKE :search"
        count_query += " AND question ILIKE :search"
        params["search"] = f"%{search}%"
        
    base_query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    
    with engine.connect() as conn:
        total_rows = conn.execute(text(count_query), params).scalar()
        result = conn.execute(text(base_query), params).mappings().all()
        
    items = []
    for r in result:
        item = dict(r)
        # format timestamp as string
        item["created_at"] = item["created_at"].isoformat() if item["created_at"] else None
        items.append(item)
        
    return {
        "items": items,
        "total": total_rows
    }


def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the full analysis details by ID."""
    engine = get_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {HISTORY_TABLE} WHERE analysis_id = :analysis_id"), {"analysis_id": analysis_id}).mappings().first()
        
    if not result:
        return None
        
    item = dict(result)
    item["created_at"] = item["created_at"].isoformat() if item["created_at"] else None
    
    return item


def delete_analysis(analysis_id: str) -> bool:
    """Delete a specific analysis record."""
    engine = get_engine()
    
    with engine.begin() as conn:
        res = conn.execute(text(f"DELETE FROM {HISTORY_TABLE} WHERE analysis_id = :analysis_id"), {"analysis_id": analysis_id})
        return res.rowcount > 0
