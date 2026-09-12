"""
models.py — Pydantic Request/Response Models
===============================================
Typed models for all API endpoints.
These ensure clean JSON serialization and validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any


# ============================================================
# REQUEST MODELS
# ============================================================

class AnalyzeRequest(BaseModel):
    """Request body for POST /api/analyze."""
    question: str = Field(..., description="Natural-language question", min_length=1)
    dataset_id: Optional[str] = Field(None, description="Dataset ID, or null for default taxi")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for follow-ups")


class FollowUpRequest(BaseModel):
    """Request body for POST /api/follow-up."""
    question: str = Field(..., description="Follow-up question", min_length=1)
    dataset_id: Optional[str] = Field(None, description="Dataset ID")
    conversation_id: str = Field(..., description="Conversation ID from prior analysis")


# ============================================================
# RESPONSE MODELS
# ============================================================

class VisualizationInfo(BaseModel):
    """Visualization metadata returned to the frontend."""
    chart_type: str = Field("table", description="bar, line, scatter, histogram, kpi, table")
    title: str = Field("", description="Chart title")
    x: Optional[str] = Field(None, description="Column for X axis")
    y: Optional[str] = Field(None, description="Column for Y axis")
    x_label: Optional[str] = Field(None, description="X axis label")
    y_label: Optional[str] = Field(None, description="Y axis label")
    color: Optional[str] = Field(None, description="Color grouping column")
    orientation: Optional[str] = Field("v", description="v or h")
    value_column: Optional[str] = Field(None, description="Column for KPI value")
    prefix: Optional[str] = Field(None)
    suffix: Optional[str] = Field(None)


class ValidationInfo(BaseModel):
    """Validation status info."""
    sql_safety: str = Field("passed")
    schema_check: str = Field("passed")
    execution: str = Field("passed")
    result_check: str = Field("passed")


class MetricMetadata(BaseModel):
    """Derived metric metadata."""
    metric_name: str = Field("")
    metric_definition: str = Field("")
    numerator: str = Field("")
    denominator: str = Field("")


class RetryAttempt(BaseModel):
    """Info about a retry attempt."""
    attempt: int = Field(0)
    stage: str = Field("")
    error: Optional[str] = Field(None)


class AnalyzeResponse(BaseModel):
    """Response for POST /api/analyze and POST /api/follow-up."""
    success: bool
    conversation_id: str = Field("", description="Conversation ID for follow-ups")
    question: str = Field("")
    dataset_id: Optional[str] = Field(None)

    sql: str = Field("")
    sql_explanation: str = Field("")

    results: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    row_count: int = Field(0)

    visualization: Optional[VisualizationInfo] = None
    explanation: str = Field("")
    validation: Optional[ValidationInfo] = None
    metric_metadata: Optional[MetricMetadata] = None

    attempts: int = Field(0)
    retry_history: list[dict[str, Any]] = Field(default_factory=list)

    needs_clarification: bool = Field(False)
    clarification_question: str = Field("")
    out_of_scope: bool = Field(False)
    out_of_scope_explanation: str = Field("")

    error: Optional[str] = Field(None)

    metadata: dict[str, Any] = Field(default_factory=dict)
    target_schema: list[dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: int = Field(0)


class DatasetInfo(BaseModel):
    """Dataset summary for list endpoints."""
    dataset_id: str
    dataset_name: str
    original_filename: str = Field("")
    table_name: str = Field("")
    file_type: str = Field("")
    row_count: int = Field(0)
    column_count: int = Field(0)
    date_range: Optional[str] = None
    status: str = Field("ready")
    created_at: Optional[str] = None
    schema_metadata: Optional[list[dict[str, Any]]] = None
    quality_report: Optional[list[dict[str, Any]]] = None


class DatasetDetailResponse(BaseModel):
    """Full dataset details for GET /api/datasets/{id}."""
    dataset_id: str
    dataset_name: str
    original_filename: str = Field("")
    table_name: str = Field("")
    file_type: str = Field("")
    row_count: int = Field(0)
    column_count: int = Field(0)
    date_range: Optional[str] = None
    status: str = Field("ready")
    created_at: Optional[str] = None
    schema_metadata: list[dict[str, Any]] = Field(default_factory=list)
    quality_report: Optional[list[dict[str, Any]]] = None
    preview: list[dict[str, Any]] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Response for POST /api/upload."""
    success: bool
    dataset_id: str = Field("")
    dataset_name: str = Field("")
    filename: str = Field("")
    row_count: int = Field(0)
    column_count: int = Field(0)
    status: str = Field("")
    schema: list[dict[str, Any]] = Field(default_factory=list)
    quality_report: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class HistorySummary(BaseModel):
    """A single query history entry summary."""
    analysis_id: str
    conversation_id: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_name: str = Field("")
    question: str
    rows_returned: Optional[int] = Field(0)
    attempts: int = Field(0)
    execution_time_ms: int = Field(0)
    status: str = Field("")
    error_message: Optional[str] = None
    created_at: str = Field("")

class HistoryListResponse(BaseModel):
    items: list[HistorySummary]
    total: int

class HistoryDetailResponse(BaseModel):
    """Full detail of a history item (matches AnalyzeResponse + DB info)."""
    analysis_id: str
    conversation_id: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_name: str = Field("")
    question: str
    sql: str = Field("")
    sql_explanation: str = Field("")
    results: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    visualization: Optional[VisualizationInfo] = None
    explanation: str = Field("")
    validation: Optional[ValidationInfo] = None
    retry_history: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(0)
    attempts: int = Field(0)
    execution_time_ms: int = Field(0)
    status: str = Field("")
    error: Optional[str] = None
    created_at: str = Field("")


class ErrorResponse(BaseModel):
    """Structured error response."""
    success: bool = False
    error: dict[str, str] = Field(default_factory=dict)
