"""
main.py — FastAPI Application
================================
REST API that connects the React frontend to the
Drishti AI agent engine. All sensitive operations
(Gemini calls, database queries, SQL execution)
stay server-side.

Run with:
    uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("drishti.api")
logging.basicConfig(level=logging.INFO)


# ---- Lifespan: startup/shutdown ----

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — runs on startup and shutdown."""
    logger.info("DRISHTI API starting up...")

    # Test database connection at startup
    try:
        from app.database.connection import test_connection
        connected, msg = test_connection()
        app.state.db_connected = connected
        app.state.db_message = msg
        if connected:
            logger.info(f"Database connected: {msg}")
        else:
            logger.warning(f"Database NOT connected: {msg}")
    except Exception as e:
        app.state.db_connected = False
        app.state.db_message = str(e)
        logger.error(f"Database connection error: {e}")

    # Ensure dataset registry table exists
    try:
        from app.data.dataset_registry import ensure_registry_table
        ensure_registry_table()
        logger.info("Dataset registry table verified.")
    except Exception as e:
        logger.warning(f"Could not ensure registry table: {e}")

    # Ensure history table exists
    try:
        from app.history.history_service import ensure_history_table
        ensure_history_table()
        logger.info("Analysis history table verified.")
    except Exception as e:
        logger.warning(f"Could not ensure history table: {e}")

    yield

    logger.info("DRISHTI API shutting down...")


# ---- FastAPI App ----

app = FastAPI(
    title="DRISHTI — AI Data Analyst API",
    description="REST API for the Drishti AI-powered data analysis engine.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---- CORS Middleware ----

# Allow frontend origins for local development
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ENDPOINTS
# ============================================================

from typing import List
from fastapi import UploadFile, File, HTTPException

from app.api.models import (
    AnalyzeRequest, 
    AnalyzeResponse,
    DatasetInfo,
    UploadResponse,
    HistoryListResponse,
    HistoryDetailResponse
)
from app.data.dataset_registry import (
    list_datasets, 
    register_dataset, 
    update_status, 
    get_dataset,
    delete_dataset
)
from app.data.dataset_profiler import (
    read_uploaded_file, 
    profile_dataset, 
    generate_quality_report
)
from app.data.dataset_loader import load_dataset, verify_load
from app.agent.orchestrator import process_question
from app.api.sessions import session_manager


# ---- 1. Health Check ----

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    Returns backend status and database connectivity.
    """
    db_connected = getattr(app.state, "db_connected", False)
    db_message = getattr(app.state, "db_message", "Not checked")

    return {
        "status": "ok" if db_connected else "degraded",
        "service": "drishti",
        "database": {
            "connected": db_connected,
            "message": db_message,
        },
    }


# ---- 2. List Datasets ----

@app.get("/api/datasets", response_model=List[DatasetInfo])
async def get_datasets_api():
    """Return available datasets."""
    datasets = list_datasets()
    return datasets


# ---- 3. Upload Dataset ----

class FileWrapper:
    """Wrapper to make FastAPI UploadFile behave like Streamlit UploadedFile for read_uploaded_file."""
    def __init__(self, upload_file: UploadFile):
        self.file = upload_file.file
        self.name = upload_file.filename

    def seek(self, offset, whence=0):
        return self.file.seek(offset, whence)

    def tell(self):
        return self.file.tell()

    def read(self, size=-1):
        return self.file.read(size)


@app.post("/api/upload", response_model=UploadResponse)
async def upload_dataset_api(file: UploadFile = File(...)):
    """Upload, profile, and load a dataset into Supabase."""
    try:
        wrapped_file = FileWrapper(file)
        
        # 1. Read & Validate
        df, file_type, error = read_uploaded_file(wrapped_file)
        if error:
            return UploadResponse(success=False, error=error)

        profile = profile_dataset(df, file.filename, file_type)
        quality_report = generate_quality_report(df, profile)

        dataset_name = profile["filename"].rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

        # 2. Register
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

        # 3. Load
        load_result = load_dataset(
            df=df,
            table_name=table_name,
            column_mapping=profile["column_mapping"]
        )

        if not load_result["success"]:
            update_status(dataset_id, "failed")
            return UploadResponse(success=False, error=f"Load failed: {load_result['error']}")

        # 4. Verify
        verification = verify_load(table_name, profile["row_count"], profile["column_count"])
        if not verification["success"]:
            update_status(dataset_id, "failed")
            return UploadResponse(success=False, error=f"Verification failed: {verification['errors']}")

        # 5. Mark as ready
        update_status(dataset_id, "ready")

        return UploadResponse(
            success=True,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            filename=file.filename,
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            status="ready",
            schema=profile["column_mapping"],
            quality_report=quality_report
        )

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return UploadResponse(success=False, error=str(e))


# ---- 4. Analyze Question ----

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_question(request: AnalyzeRequest):
    """Process a natural language question and return SQL + visualizations."""
    try:
        conversation_context = None
        conversation_id = request.conversation_id

        if conversation_id:
            # Existing conversation, get context
            conversation_context = session_manager.get_context_for_llm(conversation_id, request.dataset_id)
        else:
            # New conversation
            conversation_id = session_manager.create_session(request.dataset_id)

        result = process_question(
            question=request.question,
            dataset_id=request.dataset_id,
            conversation_context=conversation_context
        )
        
        # Add result to session history if successful
        if result.get("success"):
            session_manager.add_turn(conversation_id, result)
        
        # Serialize DataFrame to dict records
        data_records = []
        if result.get("data") is not None and not result["data"].empty:
            import pandas as pd
            # Fill NaNs with None to avoid JSON serialization issues
            df = result["data"].replace({float('nan'): None})
            data_records = df.to_dict(orient="records")

        # Map to proper response model
        response_dict = {
            "success": result["success"],
            "conversation_id": conversation_id,
            "question": result["question"],
            "dataset_id": request.dataset_id,
            "sql": result.get("sql", ""),
            "sql_explanation": result.get("sql_explanation", ""),
            "results": data_records,
            "columns": result.get("columns", []),
            "row_count": result.get("row_count", 0),
            "explanation": result.get("explanation", ""),
            "attempts": result.get("attempts", 0),
            "retry_history": result.get("retry_history", []),
            "needs_clarification": result.get("needs_clarification", False),
            "clarification_question": result.get("clarification_question", ""),
            "out_of_scope": result.get("out_of_scope", False),
            "out_of_scope_explanation": result.get("out_of_scope_explanation", ""),
            "error": result.get("error"),
            "target_schema": result.get("target_schema", []),
            "execution_time_ms": result.get("execution_time_ms", 0)
        }

        # Add visualization if present
        if result.get("viz_meta"):
            response_dict["visualization"] = result["viz_meta"]

        # Save to history
        try:
            from app.history.history_service import save_analysis
            dataset_name = "NYC Yellow Taxi"
            if request.dataset_id:
                ds = get_dataset(request.dataset_id)
                if ds:
                    dataset_name = ds.get("dataset_name", dataset_name)
                    
            status_str = "success" if result["success"] else "failed"
            save_analysis(
                status=status_str,
                question=result["question"],
                dataset_id=request.dataset_id,
                dataset_name=dataset_name,
                conversation_id=conversation_id,
                sql_query=result.get("sql"),
                sql_explanation=result.get("sql_explanation"),
                result_data=data_records,
                result_columns=result.get("columns"),
                visualization=result.get("viz_meta"),
                explanation=result.get("explanation"),
                validation=result.get("validation"),
                retry_history=result.get("retry_history"),
                rows_returned=result.get("row_count"),
                attempts=result.get("attempts"),
                execution_time_ms=result.get("execution_time_ms"),
                error_message=result.get("error")
            )
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

        return AnalyzeResponse(**response_dict)

    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        return AnalyzeResponse(success=False, error=str(e))


# ---- 5. History ----

from typing import Optional
from app.history.history_service import get_history, get_analysis, delete_analysis

@app.get("/api/history", response_model=HistoryListResponse)
async def get_history_api(dataset_id: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None, limit: int = 20, offset: int = 0):
    """List historical queries."""
    return get_history(dataset_id=dataset_id, status=status, search=search, limit=limit, offset=offset)

@app.get("/api/history/{analysis_id}", response_model=HistoryDetailResponse)
async def get_analysis_history_api(analysis_id: str):
    """Get a specific historical query with all details."""
    res = get_analysis(analysis_id)
    if not res:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return HistoryDetailResponse(
        analysis_id=res["analysis_id"],
        conversation_id=res.get("conversation_id"),
        dataset_id=res.get("dataset_id"),
        dataset_name=res.get("dataset_name", ""),
        question=res.get("question", ""),
        sql=res.get("sql_query") or "",
        sql_explanation=res.get("sql_explanation") or "",
        results=res.get("result_data") or [],
        columns=res.get("result_columns") or [],
        visualization=res.get("visualization"),
        explanation=res.get("explanation") or "",
        validation=res.get("validation"),
        retry_history=res.get("retry_history") or [],
        row_count=res.get("rows_returned") or 0,
        attempts=res.get("attempts") or 0,
        execution_time_ms=res.get("execution_time_ms") or 0,
        status=res.get("status", ""),
        error=res.get("error_message"),
        created_at=res.get("created_at", "")
    )

@app.delete("/api/history/{analysis_id}")
async def delete_history_api(analysis_id: str):
    """Delete a specific historical query."""
    success = delete_analysis(analysis_id)
    if not success:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"success": True}


