"""
test_upload_feature.py — Tests for the Upload Your Own Dataset feature
========================================================================
Tests file reading, profiling, column sanitization, registry CRUD,
data loading, schema generation, and SQL security.
"""

import io
import json
import pytest
import pandas as pd
from unittest.mock import MagicMock

from app.data.dataset_profiler import (
    read_uploaded_file,
    profile_dataset,
    generate_quality_report,
    sanitize_column_name,
    build_column_mapping,
    detect_column_type,
)
from app.data.dataset_registry import (
    ensure_registry_table,
    register_dataset,
    get_dataset,
    list_datasets,
    update_status,
    delete_dataset,
)
from app.data.dataset_loader import load_dataset, verify_load, drop_dataset_table
from app.data.schema_generator import (
    generate_schema_for_llm,
    generate_dataset_context,
    generate_suggested_questions,
)
from app.agent.sql_validator import validate_sql


# ---- Helper to create fake uploaded files ----

class FakeUploadedFile:
    """Simulates a Streamlit UploadedFile for testing."""

    def __init__(self, name: str, content: bytes):
        self.name = name
        self._buffer = io.BytesIO(content)

    def seek(self, pos, whence=0):
        return self._buffer.seek(pos, whence)

    def tell(self):
        return self._buffer.tell()

    def read(self, n=-1):
        return self._buffer.read(n)

    def readline(self):
        return self._buffer.readline()

    def __iter__(self):
        return iter(self._buffer)


def _make_csv_file(name="test.csv", rows=100):
    """Create a simple CSV file-like object."""
    lines = ["order_date,product,region,quantity,revenue\n"]
    for i in range(rows):
        lines.append(f"2024-01-{(i % 28) + 1:02d},Product_{i % 5},Region_{i % 3},{i * 2},{i * 10.5}\n")
    content = "".join(lines).encode("utf-8")
    return FakeUploadedFile(name, content)


def _make_csv_with_issues(name="issues.csv"):
    """CSV with duplicate columns, nulls, and special characters."""
    lines = [
        "Total Revenue ($),Total Revenue ($),region,,Date Sold\n",
        "100.50,200.25,North,,2024-01-01\n",
        ",,South,,2024-01-02\n",
        "300.00,150.00,,,2024-01-03\n",
    ]
    content = "".join(lines).encode("utf-8")
    return FakeUploadedFile(name, content)


# ============================================================
# TEST 1: CSV Upload — File Reading & Profiling
# ============================================================

class TestCSVUpload:
    def test_read_csv(self):
        """Upload a small CSV → file accepted, schema detected."""
        uploaded = _make_csv_file()
        df, file_type, error = read_uploaded_file(uploaded)

        assert error is None
        assert df is not None
        assert file_type == "csv"
        assert len(df) == 100
        assert len(df.columns) == 5

    def test_profile_csv(self):
        """Profile a CSV → all fields populated."""
        uploaded = _make_csv_file()
        df, file_type, _ = read_uploaded_file(uploaded)
        profile = profile_dataset(df, "test.csv", file_type)

        assert profile["row_count"] == 100
        assert profile["column_count"] == 5
        assert len(profile["columns"]) == 5
        assert profile["filename"] == "test.csv"

        # Check column types
        col_types = {c["db_name"]: c["col_type"] for c in profile["columns"]}
        assert col_types["order_date"] == "date"
        assert col_types["quantity"] in ("integer", "numeric")
        assert col_types["revenue"] == "numeric"

    def test_quality_report_clean(self):
        """Clean CSV produces all-pass quality report."""
        uploaded = _make_csv_file()
        df, file_type, _ = read_uploaded_file(uploaded)
        profile = profile_dataset(df, "test.csv", file_type)
        report = generate_quality_report(df, profile)

        assert len(report) > 0
        statuses = [c["status"] for c in report]
        assert "fail" not in statuses


# ============================================================
# TEST 4: Unsupported File Type
# ============================================================

class TestUnsupportedFile:
    def test_reject_txt(self):
        """Upload a .txt file → clear rejection."""
        uploaded = FakeUploadedFile("data.txt", b"hello world")
        df, file_type, error = read_uploaded_file(uploaded)

        assert df is None
        assert error is not None
        assert "Unsupported" in error


# ============================================================
# TEST 5: Missing Values
# ============================================================

class TestMissingValues:
    def test_warning_not_corruption(self):
        """Upload CSV with missing values → warning, not silent corruption."""
        uploaded = _make_csv_with_issues()
        df, file_type, error = read_uploaded_file(uploaded)

        assert error is None
        profile = profile_dataset(df, "issues.csv", file_type)
        report = generate_quality_report(df, profile)

        # Should have warnings about missing values
        warn_checks = [c for c in report if c["status"] == "warn"]
        assert len(warn_checks) > 0

        # Data should not be silently modified
        assert df.isna().sum().sum() > 0


# ============================================================
# TEST 6: Duplicate Column Names
# ============================================================

class TestDuplicateColumns:
    def test_safe_normalization(self):
        """Duplicate column names → safe normalization + mapping preserved."""
        uploaded = _make_csv_with_issues()
        df, file_type, _ = read_uploaded_file(uploaded)
        profile = profile_dataset(df, "issues.csv", file_type)

        # Check that column mapping exists and has unique db_names
        db_names = [c["db_name"] for c in profile["column_mapping"]]
        assert len(db_names) == len(set(db_names)), "Duplicate db_names found!"

        # Check that original names are preserved
        original_names = [c["original_name"] for c in profile["column_mapping"]]
        assert "Total Revenue ($)" in original_names


# ============================================================
# TEST 11: Column Name Sanitization
# ============================================================

class TestColumnSanitization:
    def test_special_chars(self):
        assert sanitize_column_name("Total Revenue ($)") == "total_revenue"

    def test_leading_digit(self):
        assert sanitize_column_name("123 Start") == "col_123_start"

    def test_empty_string(self):
        assert sanitize_column_name("") == "unnamed_col"

    def test_normal_name(self):
        assert sanitize_column_name("order_date") == "order_date"

    def test_spaces_and_dashes(self):
        assert sanitize_column_name("First Name - User") == "first_name_user"


# ============================================================
# TEST 12: Protected Table (SQL Security)
# ============================================================

class TestProtectedTable:
    def test_reject_registry_query(self):
        """AI-generated SQL referencing drishti_datasets is rejected."""
        sql = "SELECT * FROM drishti_datasets"
        result = validate_sql(sql)

        assert not result["valid"]
        errors_text = " ".join(result["errors"])
        assert "SECURITY" in errors_text or "protected" in errors_text.lower()


# ============================================================
# Integration Tests (require database connection)
# ============================================================

class TestDatabaseIntegration:
    """These tests require a live Supabase connection."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure the registry table exists."""
        ensure_registry_table()

    def test_full_upload_lifecycle(self):
        """TEST 1 end-to-end: upload CSV → register → load → verify → delete."""
        # 1. Read file
        uploaded = _make_csv_file("lifecycle_test.csv", rows=50)
        df, file_type, error = read_uploaded_file(uploaded)
        assert error is None

        # 2. Profile
        profile = profile_dataset(df, "lifecycle_test.csv", file_type)
        quality = generate_quality_report(df, profile)

        # 3. Register
        dataset_id, table_name = register_dataset(
            dataset_name="Lifecycle Test",
            original_filename="lifecycle_test.csv",
            file_type=file_type,
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            schema_metadata=profile["column_mapping"],
            quality_report=quality,
            date_range=profile.get("date_range"),
        )
        assert dataset_id.startswith("ds_")
        assert table_name.startswith("uploaded_ds_")

        # 4. Load data
        result = load_dataset(df, table_name, profile["column_mapping"])
        assert result["success"]
        assert result["rows_loaded"] == 50

        # 5. Verify
        verification = verify_load(table_name, 50, 5)
        assert verification["success"]
        assert verification["actual_rows"] == 50

        # 6. Mark ready
        update_status(dataset_id, "ready")
        ds = get_dataset(dataset_id)
        assert ds["dataset_status"] == "ready"

        # 7. Generate schema for LLM
        schema_text = generate_schema_for_llm(ds)
        assert table_name in schema_text
        assert "order_date" in schema_text

        # 8. Generate context
        context = generate_dataset_context(ds)
        assert "Lifecycle Test" in context

        # 9. Generate suggestions
        suggestions = generate_suggested_questions(ds)
        assert len(suggestions) >= 4

        # 10. List datasets
        all_ds = list_datasets()
        ds_ids = [d["dataset_id"] for d in all_ds]
        assert dataset_id in ds_ids

        # 11. Delete
        deleted = delete_dataset(dataset_id)
        assert deleted

        ds_after = get_dataset(dataset_id)
        assert ds_after["dataset_status"] == "deleted"

    def test_query_only_uploaded_table(self):
        """TEST 7: SQL against uploaded dataset references ONLY the uploaded table."""
        from app.agent.sql_generator import generate_sql
        from app.agent.schema_retriever import get_schema_for_llm as get_schema

        # Create a small dataset
        uploaded = _make_csv_file("query_test.csv", rows=20)
        df, file_type, _ = read_uploaded_file(uploaded)
        profile = profile_dataset(df, "query_test.csv", file_type)

        dataset_id, table_name = register_dataset(
            dataset_name="Query Test",
            original_filename="query_test.csv",
            file_type=file_type,
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            schema_metadata=profile["column_mapping"],
        )

        result = load_dataset(df, table_name, profile["column_mapping"])
        assert result["success"]
        update_status(dataset_id, "ready")

        try:
            # Get schema for this dataset
            schema = get_schema(dataset_id=dataset_id)
            assert table_name in schema
            # Should NOT define taxi tables
            assert "TABLE: taxi_zones" not in schema
            assert "TABLE: yellow_trips" not in schema

            # Generate SQL
            from app.data.schema_generator import generate_dataset_context
            ds_meta = get_dataset(dataset_id)
            context = generate_dataset_context(ds_meta)

            gen_result = generate_sql(
                "How many records are in the dataset?",
                schema,
                dataset_context=context,
            )
            assert gen_result["success"]
            sql_lower = gen_result["sql"].lower()

            # Should reference the uploaded table, NOT taxi tables
            assert table_name.lower() in sql_lower
            assert "yellow_trips" not in sql_lower
            assert "taxi_zones" not in sql_lower

        finally:
            # Cleanup
            delete_dataset(dataset_id)

    def test_dataset_isolation(self):
        """TEST 9: Two datasets → querying one never references the other."""
        # Create two datasets
        ds_ids = []
        table_names = []
        for i in range(2):
            uploaded = _make_csv_file(f"iso_test_{i}.csv", rows=10)
            df, ft, _ = read_uploaded_file(uploaded)
            profile = profile_dataset(df, f"iso_test_{i}.csv", ft)
            did, tname = register_dataset(
                dataset_name=f"Iso Test {i}",
                original_filename=f"iso_test_{i}.csv",
                file_type=ft,
                row_count=profile["row_count"],
                column_count=profile["column_count"],
                schema_metadata=profile["column_mapping"],
            )
            load_dataset(df, tname, profile["column_mapping"])
            update_status(did, "ready")
            ds_ids.append(did)
            table_names.append(tname)

        try:
            from app.agent.schema_retriever import get_schema_for_llm as get_schema

            # Schema for dataset 0 should not mention dataset 1's table
            schema_0 = get_schema(dataset_id=ds_ids[0])
            assert table_names[0] in schema_0
            assert table_names[1] not in schema_0

            schema_1 = get_schema(dataset_id=ds_ids[1])
            assert table_names[1] in schema_1
            assert table_names[0] not in schema_1

        finally:
            for did in ds_ids:
                delete_dataset(did)
