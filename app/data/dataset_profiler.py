"""
dataset_profiler.py — Dataset Profiler & Quality Analyzer
============================================================
Inspects an uploaded file (CSV, Parquet, Excel) and produces:
  1. A structured profile (types, nulls, stats, date ranges)
  2. A data-quality report (checks with pass/warn/fail status)
  3. Safe column name mapping

This module NEVER modifies the user's data. It only inspects.
"""

import re
import io
import pandas as pd
import numpy as np
from pathlib import Path

from app.config import (
    MAX_UPLOAD_SIZE_MB,
    MAX_UPLOAD_ROWS,
    MAX_UPLOAD_COLUMNS,
    SUPPORTED_FILE_TYPES,
)


# ---- File Reading ----

def read_uploaded_file(uploaded_file) -> tuple:
    """
    Read an uploaded file into a Pandas DataFrame.

    Args:
        uploaded_file: Streamlit UploadedFile object or file-like object

    Returns:
        tuple: (df: DataFrame, file_type: str, error: str or None)
    """
    filename = getattr(uploaded_file, "name", "unknown")
    extension = Path(filename).suffix.lower().lstrip(".")

    if extension not in SUPPORTED_FILE_TYPES:
        return None, extension, (
            f"Unsupported file type: '.{extension}'. "
            f"Supported types: {', '.join(SUPPORTED_FILE_TYPES)}"
        )

    # Check file size
    uploaded_file.seek(0, 2)  # Seek to end
    size_bytes = uploaded_file.tell()
    uploaded_file.seek(0)     # Reset to beginning
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > MAX_UPLOAD_SIZE_MB:
        return None, extension, (
            f"File too large: {size_mb:.1f} MB. "
            f"Maximum allowed: {MAX_UPLOAD_SIZE_MB} MB."
        )

    try:
        if extension == "csv":
            df = pd.read_csv(uploaded_file, nrows=MAX_UPLOAD_ROWS)
        elif extension == "parquet":
            df = pd.read_parquet(uploaded_file)
            if len(df) > MAX_UPLOAD_ROWS:
                df = df.head(MAX_UPLOAD_ROWS)
        elif extension in ("xlsx", "xls"):
            df = pd.read_excel(uploaded_file, nrows=MAX_UPLOAD_ROWS)
        else:
            return None, extension, f"Unsupported file type: '.{extension}'"

    except Exception as e:
        return None, extension, f"Could not read file: {str(e)}"

    if df.empty:
        return None, extension, "File contains no data rows."

    if len(df.columns) > MAX_UPLOAD_COLUMNS:
        return None, extension, (
            f"Too many columns: {len(df.columns)}. "
            f"Maximum allowed: {MAX_UPLOAD_COLUMNS}."
        )

    return df, extension, None


# ---- Column Type Detection ----

def detect_column_type(series: pd.Series) -> str:
    """
    Detect the simplified type of a Pandas Series.

    Returns one of: 'integer', 'numeric', 'text', 'date', 'boolean', 'categorical'
    """
    dtype = series.dtype

    # Boolean
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"

    # Integer
    if pd.api.types.is_integer_dtype(dtype):
        return "integer"

    # Float / Numeric
    if pd.api.types.is_float_dtype(dtype):
        return "numeric"

    # Datetime
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "date"

    # Object / String — try to infer
    if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
        non_null = series.dropna()
        if len(non_null) == 0:
            return "text"

        # Try date parsing on a sample
        sample = non_null.head(50)
        try:
            parsed = pd.to_datetime(sample, format="mixed", dayfirst=False)
            if parsed.notna().sum() >= len(sample) * 0.8:
                return "date"
        except (ValueError, TypeError):
            pass

        # Categorical heuristic: few unique values relative to total
        n_unique = non_null.nunique()
        if n_unique <= 30 or (len(non_null) > 100 and n_unique / len(non_null) < 0.05):
            return "categorical"

        return "text"

    return "text"


def _map_to_pg_type(col_type: str, series: pd.Series) -> str:
    """Map a simplified column type to a PostgreSQL type."""
    mapping = {
        "integer": "BIGINT",
        "numeric": "DOUBLE PRECISION",
        "date": "TIMESTAMP",
        "boolean": "BOOLEAN",
        "categorical": "TEXT",
        "text": "TEXT",
    }
    return mapping.get(col_type, "TEXT")


# ---- Column Name Sanitization ----

def sanitize_column_name(name: str) -> str:
    """
    Convert arbitrary column names to safe PostgreSQL identifiers.

    Examples:
        'Total Revenue ($)' -> 'total_revenue'
        '123 Start'         -> 'col_123_start'
        ''                  -> 'unnamed_col'
    """
    if not name or not name.strip():
        return "unnamed_col"

    name = str(name).strip().lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)   # Replace non-alphanumeric
    name = re.sub(r'_+', '_', name)            # Collapse multiple underscores
    name = name.strip('_')

    if not name:
        return "unnamed_col"
    if name[0].isdigit():
        name = 'col_' + name

    return name


def build_column_mapping(df: pd.DataFrame) -> list:
    """
    Build a column mapping from original names to safe database names.
    Handles duplicate names by appending a suffix.

    Returns:
        list of dicts: [{"original_name": str, "db_name": str, "col_type": str, "pg_type": str}, ...]
    """
    mapping = []
    seen_names = {}

    for col in df.columns:
        original = str(col)
        safe = sanitize_column_name(original)

        # Handle duplicates by appending _2, _3, etc.
        if safe in seen_names:
            seen_names[safe] += 1
            safe = f"{safe}_{seen_names[safe]}"
        else:
            seen_names[safe] = 1

        col_type = detect_column_type(df[col])
        pg_type = _map_to_pg_type(col_type, df[col])
        nullable = df[col].isna().any()

        mapping.append({
            "original_name": original,
            "db_name": safe,
            "col_type": col_type,
            "pg_type": pg_type,
            "nullable": bool(nullable),
        })

    return mapping


# ---- Dataset Profiling ----

def profile_dataset(df: pd.DataFrame, filename: str, file_type: str) -> dict:
    """
    Generate a comprehensive profile of a dataset.

    Args:
        df: The DataFrame to profile
        filename: Original filename
        file_type: File extension (csv, parquet, xlsx)

    Returns:
        dict with complete dataset profile
    """
    column_mapping = build_column_mapping(df)

    columns_profile = []
    for i, col_info in enumerate(column_mapping):
        original_name = col_info["original_name"]
        series = df[original_name]
        col_type = col_info["col_type"]

        profile = {
            "original_name": original_name,
            "db_name": col_info["db_name"],
            "col_type": col_type,
            "pg_type": col_info["pg_type"],
            "nullable": col_info["nullable"],
            "null_count": int(series.isna().sum()),
            "null_pct": round(series.isna().mean() * 100, 2),
            "unique_count": int(series.nunique()),
        }

        # Numeric stats
        if col_type in ("integer", "numeric"):
            numeric = pd.to_numeric(series, errors="coerce")
            profile["min"] = float(numeric.min()) if numeric.notna().any() else None
            profile["max"] = float(numeric.max()) if numeric.notna().any() else None
            profile["mean"] = round(float(numeric.mean()), 4) if numeric.notna().any() else None

        # Date stats
        if col_type == "date":
            if pd.api.types.is_datetime64_any_dtype(series):
                dates = series
            else:
                dates = pd.to_datetime(series, errors="coerce", format="mixed")
            if dates.notna().any():
                profile["date_min"] = str(dates.min())
                profile["date_max"] = str(dates.max())

        columns_profile.append(profile)

    # Determine overall date range
    date_columns = [c for c in columns_profile if c["col_type"] == "date"]
    date_range = None
    if date_columns:
        first_date_col = date_columns[0]
        date_range = f"{first_date_col.get('date_min', 'N/A')} to {first_date_col.get('date_max', 'N/A')}"

    return {
        "filename": filename,
        "file_type": file_type,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns_profile,
        "column_mapping": column_mapping,
        "date_range": date_range,
    }


# ---- Data Quality Report ----

def generate_quality_report(df: pd.DataFrame, profile: dict) -> list:
    """
    Generate a list of data-quality checks.

    Returns:
        list of dicts: [{"check": str, "status": "pass"|"warn"|"fail", "detail": str}, ...]
    """
    checks = []

    # 1. File readable
    checks.append({
        "check": "File readable",
        "status": "pass",
        "detail": f"Successfully read {profile['row_count']:,} rows.",
    })

    # 2. Column names valid
    empty_names = [c["original_name"] for c in profile["columns"] if not str(c["original_name"]).strip()]
    if empty_names:
        checks.append({
            "check": "Column names valid",
            "status": "warn",
            "detail": f"{len(empty_names)} column(s) have empty names. They will be renamed to 'unnamed_col'.",
        })
    else:
        checks.append({
            "check": "Column names valid",
            "status": "pass",
            "detail": "All column names are non-empty.",
        })

    # 3. Duplicate column names
    original_names = [str(c) for c in df.columns]
    duplicates = [n for n in set(original_names) if original_names.count(n) > 1]
    if duplicates:
        checks.append({
            "check": "Duplicate column names",
            "status": "warn",
            "detail": f"Duplicate column names detected: {', '.join(duplicates)}. Suffixes will be added.",
        })
    else:
        checks.append({
            "check": "Duplicate column names",
            "status": "pass",
            "detail": "No duplicate column names.",
        })

    # 4. All-null columns
    all_null_cols = [c["original_name"] for c in profile["columns"] if c["null_pct"] == 100.0]
    if all_null_cols:
        checks.append({
            "check": "All-null columns",
            "status": "warn",
            "detail": f"{len(all_null_cols)} column(s) are entirely NULL: {', '.join(all_null_cols[:5])}.",
        })
    else:
        checks.append({
            "check": "All-null columns",
            "status": "pass",
            "detail": "No columns are entirely NULL.",
        })

    # 5. Missing values
    cols_with_nulls = [c for c in profile["columns"] if c["null_count"] > 0 and c["null_pct"] < 100]
    if cols_with_nulls:
        high_null = [c for c in cols_with_nulls if c["null_pct"] > 50]
        if high_null:
            checks.append({
                "check": "Missing values",
                "status": "warn",
                "detail": (
                    f"{len(cols_with_nulls)} column(s) contain missing values. "
                    f"{len(high_null)} column(s) have >50% nulls: "
                    f"{', '.join(c['original_name'] for c in high_null[:5])}."
                ),
            })
        else:
            checks.append({
                "check": "Missing values",
                "status": "warn",
                "detail": f"{len(cols_with_nulls)} column(s) contain missing values (all below 50%).",
            })
    else:
        checks.append({
            "check": "Missing values",
            "status": "pass",
            "detail": "No missing values detected.",
        })

    # 6. Date column detected
    date_cols = [c for c in profile["columns"] if c["col_type"] == "date"]
    if date_cols:
        checks.append({
            "check": "Date column detected",
            "status": "pass",
            "detail": f"Date column(s): {', '.join(c['original_name'] for c in date_cols)}.",
        })
    else:
        checks.append({
            "check": "Date column detected",
            "status": "pass",
            "detail": "No date columns detected (this is fine for non-temporal data).",
        })

    # 7. Numeric columns detected
    numeric_cols = [c for c in profile["columns"] if c["col_type"] in ("integer", "numeric")]
    if numeric_cols:
        checks.append({
            "check": "Numeric columns detected",
            "status": "pass",
            "detail": f"Numeric column(s): {', '.join(c['original_name'] for c in numeric_cols)}.",
        })
    else:
        checks.append({
            "check": "Numeric columns detected",
            "status": "warn",
            "detail": "No numeric columns detected.",
        })

    # 8. Duplicate rows (sampled check for large datasets)
    sample_size = min(len(df), 10000)
    sample_df = df.head(sample_size)
    dup_count = sample_df.duplicated().sum()
    if dup_count > 0:
        pct = round(dup_count / sample_size * 100, 1)
        checks.append({
            "check": "Duplicate rows",
            "status": "warn",
            "detail": f"~{pct}% duplicate rows detected (sampled {sample_size:,} rows).",
        })
    else:
        checks.append({
            "check": "Duplicate rows",
            "status": "pass",
            "detail": "No duplicate rows detected.",
        })

    return checks
