"""
visualizer.py — Visualization Generator
==========================================
Uses Gemini to decide the best chart type for the data,
then generates the actual Plotly chart from structured metadata.

SECURITY: The LLM never generates or executes Python code.
It only returns structured JSON metadata describing the chart,
and this module creates the Plotly chart from that metadata.

Supported chart types:
  - bar: Ranking comparisons
  - line: Trends over time
  - scatter: Relationships between variables
  - histogram: Distributions
  - kpi: Single metric display
  - table: Detailed tabular data
"""

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from pydantic import BaseModel, Field
from typing import Optional, List
from app.config import GEMINI_API_KEY, GEMINI_MODEL


class VisualizationMetadata(BaseModel):
    chart_type: str = Field(description="One of: bar, line, scatter, histogram, kpi, table")
    title: str = Field(description="Descriptive Chart Title")
    x: Optional[str] = Field(None, description="Column name for X axis")
    y: Optional[str] = Field(None, description="Column name for Y axis")
    x_label: Optional[str] = Field(None, description="X Axis Label")
    y_label: Optional[str] = Field(None, description="Y Axis Label")
    color: Optional[str] = Field(None, description="Optional column for color grouping")
    orientation: Optional[str] = Field("v", description="v or h (vertical or horizontal)")
    value_column: Optional[str] = Field(None, description="Column name for KPI value")
    prefix: Optional[str] = Field(None, description="$ or empty for KPI")
    suffix: Optional[str] = Field(None, description="trips or empty for KPI")
    columns: Optional[List[str]] = Field(None, description="List of columns for table view")


# System prompt for visualization selection
VIZ_SYSTEM_PROMPT = """You are a data visualization expert. Given a user question, the SQL query used, and the query results, determine the best visualization type.

Choose from these chart types:
- "bar": For ranking, comparisons, top-N results, categorical data
- "line": For trends over time, time series data
- "scatter": For relationships between two numerical variables
- "histogram": For distribution of a single numerical variable
- "kpi": For a single metric/number (e.g., "What is the total number...", "What is the average fare?"). MUST BE USED if the result is exactly 1 row and 1 column (e.g. from a COUNT(*) query).
- "table": For detailed multi-column results, or when no chart type fits well

IMPORTANT: Use the EXACT column names from the query results. Do NOT invent column names."""


def select_visualization(question: str, sql: str, df: pd.DataFrame) -> dict:
    """
    Use the LLM to select the best visualization for the result.
    Applies deterministic rules for unambiguous result shapes first.

    Args:
        question: The user's original question
        sql: The SQL query that was executed
        df: The result DataFrame

    Returns:
        dict: Visualization metadata (chart_type, x, y, title, etc.)
    """
    # ---- Deterministic Rules ----
    if df is not None and not df.empty:
        num_rows = len(df)
        num_cols = len(df.columns)
        
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c]) or 'date' in c.lower() or 'time' in c.lower() or 'day' in c.lower() or 'month' in c.lower() or 'year' in c.lower()]
        categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]

        # 1. KPI: 1 row + 1 numeric value
        if num_rows == 1 and num_cols == 1 and len(numeric_cols) == 1:
            return {
                "chart_type": "kpi",
                "title": df.columns[0].replace("_", " ").upper(),
                "value_column": df.columns[0]
            }
        
        # 2. Histogram: 1 numeric column, many rows
        if num_cols == 1 and len(numeric_cols) == 1 and num_rows > 1:
            return {
                "chart_type": "histogram",
                "title": f"Distribution of {numeric_cols[0]}".replace("_", " ").title(),
                "x": numeric_cols[0]
            }

        # 3. 2-column rules
        if num_cols == 2:
            # Date/time + numeric -> Line chart
            if len(datetime_cols) == 1 and len(numeric_cols) == 1:
                return {
                    "chart_type": "line",
                    "title": f"{numeric_cols[0]} over Time".replace("_", " ").title(),
                    "x": datetime_cols[0],
                    "y": numeric_cols[0]
                }
            
            # Categorical + numeric -> Bar chart
            if len(categorical_cols) == 1 and len(numeric_cols) == 1:
                return {
                    "chart_type": "bar",
                    "title": f"{numeric_cols[0]} by {categorical_cols[0]}".replace("_", " ").title(),
                    "x": categorical_cols[0],
                    "y": numeric_cols[0]
                }
            
            # 2 numeric columns -> Scatter plot
            if len(numeric_cols) == 2:
                return {
                    "chart_type": "scatter",
                    "title": f"{numeric_cols[1]} vs {numeric_cols[0]}".replace("_", " ").title(),
                    "x": numeric_cols[0],
                    "y": numeric_cols[1]
                }

    # ---- Fallback to LLM for complex shapes ----
    # Prepare a summary of the result data for the LLM
    columns_info = ", ".join([f"{col} ({df[col].dtype})" for col in df.columns])
    sample_data = df.head(5).to_string(index=False)

    user_prompt = f"""USER QUESTION: {question}

SQL QUERY: {sql}

RESULT COLUMNS: {columns_info}
RESULT ROWS: {len(df)}

SAMPLE DATA:
{sample_data}

What visualization should I use?"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config={
                "system_instruction": VIZ_SYSTEM_PROMPT,
                "temperature": 0.1,
                "response_mime_type": "application/json",
                "response_schema": VisualizationMetadata,
            }
        )

        viz_meta = json.loads(response.text)
        return viz_meta

    except Exception as e:
        # Fallback: Use a simple table if LLM fails
        return {
            "chart_type": "table",
            "title": "Query Results",
            "columns": list(df.columns),
        }


def create_chart(df: pd.DataFrame, viz_meta: dict):
    """
    Create a Plotly chart from the visualization metadata.

    Args:
        df: The result DataFrame
        viz_meta: Visualization metadata from select_visualization()

    Returns:
        plotly figure object, or None for table/kpi types
    """
    chart_type = viz_meta.get("chart_type", "table")
    title = viz_meta.get("title", "Query Results")

    try:
        if chart_type == "bar":
            return _create_bar_chart(df, viz_meta)
        elif chart_type == "line":
            return _create_line_chart(df, viz_meta)
        elif chart_type == "scatter":
            return _create_scatter_chart(df, viz_meta)
        elif chart_type == "histogram":
            return _create_histogram(df, viz_meta)
        elif chart_type == "kpi":
            return _create_kpi(df, viz_meta)
        else:
            # "table" or unknown — no chart needed
            return None

    except Exception as e:
        # If chart creation fails, return None (UI will show table instead)
        return None


def _create_bar_chart(df: pd.DataFrame, meta: dict):
    """Create a bar chart."""
    x = meta.get("x", df.columns[0])
    y = meta.get("y", df.columns[-1])
    color = meta.get("color")
    orientation = meta.get("orientation", "v")

    # Validate columns exist
    if x not in df.columns:
        x = df.columns[0]
    if y not in df.columns:
        y = df.columns[-1] if len(df.columns) > 1 else df.columns[0]

    if orientation == "h":
        fig = px.bar(
            df, x=y, y=x,
            orientation="h",
            title=meta.get("title", ""),
            labels={y: meta.get("y_label", y), x: meta.get("x_label", x)},
            color=color if color and color in df.columns else None,
        )
    else:
        fig = px.bar(
            df, x=x, y=y,
            title=meta.get("title", ""),
            labels={x: meta.get("x_label", x), y: meta.get("y_label", y)},
            color=color if color and color in df.columns else None,
        )

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        title_font_size=18,
    )
    return fig


def _create_line_chart(df: pd.DataFrame, meta: dict):
    """Create a line chart."""
    x = meta.get("x", df.columns[0])
    y = meta.get("y", df.columns[-1])
    color = meta.get("color")

    if x not in df.columns:
        x = df.columns[0]
    if y not in df.columns:
        y = df.columns[-1] if len(df.columns) > 1 else df.columns[0]

    fig = px.line(
        df, x=x, y=y,
        title=meta.get("title", ""),
        labels={x: meta.get("x_label", x), y: meta.get("y_label", y)},
        color=color if color and color in df.columns else None,
        markers=True,
    )
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        title_font_size=18,
    )
    return fig


def _create_scatter_chart(df: pd.DataFrame, meta: dict):
    """Create a scatter plot."""
    x = meta.get("x", df.columns[0])
    y = meta.get("y", df.columns[-1])
    color = meta.get("color")

    if x not in df.columns:
        x = df.columns[0]
    if y not in df.columns:
        y = df.columns[-1] if len(df.columns) > 1 else df.columns[0]

    fig = px.scatter(
        df, x=x, y=y,
        title=meta.get("title", ""),
        labels={x: meta.get("x_label", x), y: meta.get("y_label", y)},
        color=color if color and color in df.columns else None,
    )
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        title_font_size=18,
    )
    return fig


def _create_histogram(df: pd.DataFrame, meta: dict):
    """Create a histogram."""
    x = meta.get("x", df.columns[0])

    if x not in df.columns:
        x = df.columns[0]

    fig = px.histogram(
        df, x=x,
        title=meta.get("title", ""),
        labels={x: meta.get("x_label", x)},
    )
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14),
        title_font_size=18,
    )
    return fig


def _create_kpi(df: pd.DataFrame, meta: dict):
    """Create a KPI indicator chart."""
    value_column = meta.get("value_column", df.columns[0])

    if value_column not in df.columns:
        value_column = df.columns[0]

    value = df[value_column].iloc[0]
    prefix = meta.get("prefix", "")
    suffix = meta.get("suffix", "")

    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="number",
        value=float(value) if not pd.isna(value) else 0,
        title={"text": meta.get("title", "Metric"), "font": {"size": 24}},
        number={
            "prefix": prefix,
            "suffix": f" {suffix}" if suffix else "",
            "font": {"size": 60},
            "valueformat": ",.2f" if isinstance(value, float) else ",",
        },
    ))
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=300,
    )
    return fig
