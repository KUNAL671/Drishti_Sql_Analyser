"""
test_validation.py — Automated Tests
=======================================
Tests for the SQL validator and result validator.
These tests do NOT require a database connection or OpenAI API key.

Run with:
    python -m pytest tests/test_validation.py -v
"""

import pytest
import pandas as pd

# We need to handle the case where the database is not available
# by mocking the schema retrieval in the SQL validator
from unittest.mock import patch


# ============================================================
# SQL VALIDATOR TESTS
# ============================================================

class TestSQLValidator:
    """Tests for the SQL safety validator."""

    def _validate(self, sql):
        """Helper: validate SQL with a mocked schema."""
        # Mock the schema to avoid needing a real database
        mock_schema = {
            "yellow_taxi_trips": [
                {"column": "trip_id", "type": "integer", "nullable": False, "default": None},
                {"column": "vendor_id", "type": "smallint", "nullable": False, "default": None},
                {"column": "pickup_datetime", "type": "timestamp", "nullable": False, "default": None},
                {"column": "dropoff_datetime", "type": "timestamp", "nullable": False, "default": None},
                {"column": "passenger_count", "type": "smallint", "nullable": True, "default": None},
                {"column": "trip_distance", "type": "double precision", "nullable": False, "default": None},
                {"column": "pu_location_id", "type": "smallint", "nullable": False, "default": None},
                {"column": "do_location_id", "type": "smallint", "nullable": False, "default": None},
                {"column": "payment_type", "type": "smallint", "nullable": False, "default": None},
                {"column": "fare_amount", "type": "numeric", "nullable": False, "default": None},
                {"column": "total_amount", "type": "numeric", "nullable": False, "default": None},
                {"column": "tip_amount", "type": "numeric", "nullable": False, "default": None},
            ],
            "taxi_zones": [
                {"column": "location_id", "type": "smallint", "nullable": False, "default": None},
                {"column": "borough", "type": "character varying", "nullable": False, "default": None},
                {"column": "zone", "type": "character varying", "nullable": False, "default": None},
                {"column": "service_zone", "type": "character varying", "nullable": False, "default": None},
            ],
        }
        with patch("app.agent.sql_validator.get_schema_info", return_value=mock_schema):
            from app.agent.sql_validator import validate_sql
            return validate_sql(sql)

    # ---- Tests for ALLOWED queries ----

    def test_simple_select(self):
        result = self._validate("SELECT * FROM yellow_taxi_trips LIMIT 10")
        assert result["valid"], f"Expected valid, got errors: {result['errors']}"

    def test_select_with_where(self):
        result = self._validate(
            "SELECT vendor_id, fare_amount FROM yellow_taxi_trips WHERE fare_amount > 50"
        )
        assert result["valid"], f"Expected valid, got errors: {result['errors']}"

    def test_select_with_join(self):
        result = self._validate("""
            SELECT tz.zone, COUNT(*) as trip_count
            FROM yellow_taxi_trips t
            JOIN taxi_zones tz ON t.pu_location_id = tz.location_id
            GROUP BY tz.zone
            ORDER BY trip_count DESC
            LIMIT 5
        """)
        assert result["valid"], f"Expected valid, got errors: {result['errors']}"

    def test_select_with_cte(self):
        result = self._validate("""
            WITH top_zones AS (
                SELECT pu_location_id, COUNT(*) as cnt
                FROM yellow_taxi_trips
                GROUP BY pu_location_id
            )
            SELECT * FROM top_zones ORDER BY cnt DESC LIMIT 5
        """)
        assert result["valid"], f"Expected valid, got errors: {result['errors']}"

    def test_aggregation_query(self):
        result = self._validate(
            "SELECT AVG(fare_amount), MAX(total_amount) FROM yellow_taxi_trips"
        )
        assert result["valid"], f"Expected valid, got errors: {result['errors']}"

    # ---- Tests for FORBIDDEN queries ----

    def test_reject_drop(self):
        result = self._validate("DROP TABLE yellow_taxi_trips")
        assert not result["valid"]
        assert any("DROP" in e for e in result["errors"])

    def test_reject_delete(self):
        result = self._validate("DELETE FROM yellow_taxi_trips")
        assert not result["valid"]
        assert any("DELETE" in e for e in result["errors"])

    def test_reject_update(self):
        result = self._validate("UPDATE yellow_taxi_trips SET fare_amount = 0")
        assert not result["valid"]
        assert any("UPDATE" in e for e in result["errors"])

    def test_reject_insert(self):
        result = self._validate("INSERT INTO yellow_taxi_trips (vendor_id) VALUES (1)")
        assert not result["valid"]
        assert any("INSERT" in e for e in result["errors"])

    def test_reject_truncate(self):
        result = self._validate("TRUNCATE yellow_taxi_trips")
        assert not result["valid"]
        assert any("TRUNCATE" in e for e in result["errors"])

    def test_reject_alter(self):
        result = self._validate("ALTER TABLE yellow_taxi_trips ADD COLUMN test INT")
        assert not result["valid"]
        assert any("ALTER" in e for e in result["errors"])

    def test_reject_create(self):
        result = self._validate("CREATE TABLE hacked (id INT)")
        assert not result["valid"]
        assert any("CREATE" in e for e in result["errors"])

    def test_reject_grant(self):
        result = self._validate("GRANT ALL ON yellow_taxi_trips TO public")
        assert not result["valid"]
        assert any("GRANT" in e for e in result["errors"])

    def test_reject_multiple_statements(self):
        result = self._validate(
            "SELECT 1; DROP TABLE yellow_taxi_trips"
        )
        assert not result["valid"]

    def test_reject_empty_sql(self):
        result = self._validate("")
        assert not result["valid"]

    def test_reject_none_sql(self):
        result = self._validate(None)
        assert not result["valid"]

    # ---- Tests for invalid table references ----

    def test_reject_unknown_table(self):
        result = self._validate("SELECT * FROM nonexistent_table")
        assert not result["valid"]
        assert any("not found" in e.lower() for e in result["errors"])


# ============================================================
# RESULT VALIDATOR TESTS
# ============================================================

class TestResultValidator:
    """Tests for the query result validator."""

    def test_invalid_empty_result(self):
        from app.agent.result_validator import validate_result
        result = {
            "success": True,
            "data": pd.DataFrame(),
            "row_count": 0,
            "columns": [],
            "error": None,
        }
        validation = validate_result(result, "How many trips from Manhattan?", "SELECT COUNT(*) FROM trips WHERE zone='X'")
        assert not validation["valid"]
        assert validation["status"] == "INVALID_EMPTY_RESULT"
        assert any("no results" in e.lower() for e in validation["errors"])

    def test_valid_empty_result(self):
        from app.agent.result_validator import validate_result
        result = {
            "success": True,
            "data": pd.DataFrame(),
            "row_count": 0,
            "columns": [],
            "error": None,
        }
        validation = validate_result(result, "Are there any trips over 1000 miles?", "SELECT * FROM trips WHERE trip_distance > 1000")
        assert validation["valid"]
        assert validation["status"] == "VALID_EMPTY_RESULT"

    def test_valid_no_match(self):
        from app.agent.result_validator import validate_result
        result = {
            "success": True,
            "data": pd.DataFrame(),
            "row_count": 0,
            "columns": [],
            "error": None,
        }
        validation = validate_result(result, "Which borough has both the highest volume and highest fare?", "WITH rank AS (...) SELECT * FROM rank WHERE r1=1 AND r2=1")
        assert validation["valid"]
        assert validation["status"] == "VALID_NO_MATCH"

    def test_ranking_comparison_different_entities(self):
        from app.agent.result_validator import validate_result
        result = {
            "success": True,
            "data": pd.DataFrame({"borough": ["Manhattan", "Brooklyn"], "vol_rank": [1, 2], "fare_rank": [2, 1]}),
            "row_count": 2,
            "columns": ["borough", "vol_rank", "fare_rank"],
            "error": None,
        }
        validation = validate_result(result, "Which borough has both the highest volume and highest fare?", "SELECT ...")
        assert validation["valid"]
        assert validation["status"] == "SUCCESS"

    def test_ranking_comparison_same_entity(self):
        from app.agent.result_validator import validate_result
        result = {
            "success": True,
            "data": pd.DataFrame({"borough": ["Manhattan"], "vol_rank": [1], "fare_rank": [1]}),
            "row_count": 1,
            "columns": ["borough", "vol_rank", "fare_rank"],
            "error": None,
        }
        validation = validate_result(result, "Which borough has both the highest volume and highest fare?", "SELECT ...")
        assert validation["valid"]
        assert validation["status"] == "SUCCESS"

    def test_execution_failure(self):
        from app.agent.result_validator import validate_result
        result = {
            "success": False,
            "data": None,
            "row_count": 0,
            "columns": [],
            "error": "relation does not exist",
        }
        validation = validate_result(result, "How many trips?", "SELECT * FROM trips")
        assert not validation["valid"]

    def test_valid_result(self):
        from app.agent.result_validator import validate_result
        result = {
            "success": True,
            "data": pd.DataFrame({"zone": ["A", "B", "C"], "count": [100, 200, 300]}),
            "row_count": 3,
            "columns": ["zone", "count"],
            "error": None,
        }
        validation = validate_result(result, "Top 3 zones", "SELECT zone, count FROM zones LIMIT 3")
        assert validation["valid"]

    def test_top_n_warning(self):
        from app.agent.result_validator import validate_result
        result = {
            "success": True,
            "data": pd.DataFrame({"zone": list(range(20)), "count": list(range(20))}),
            "row_count": 20,
            "columns": ["zone", "count"],
            "error": None,
        }
        validation = validate_result(result, "Top 5 zones", "SELECT zone, count FROM zones")
        # Should have a warning about row count
        assert len(validation["warnings"]) > 0


# ============================================================
# EXTRACT TOP-N TESTS
# ============================================================

class TestExtractTopN:
    """Tests for the top-N extraction utility."""

    def test_top_5(self):
        from app.agent.result_validator import _extract_top_n
        assert _extract_top_n("which are the top 5 zones") == 5

    def test_first_10(self):
        from app.agent.result_validator import _extract_top_n
        assert _extract_top_n("show the first 10 results") == 10

    def test_5_most(self):
        from app.agent.result_validator import _extract_top_n
        assert _extract_top_n("which 5 most popular zones") == 5

    def test_3_busiest(self):
        from app.agent.result_validator import _extract_top_n
        assert _extract_top_n("the 3 busiest hours") == 3

    def test_no_number(self):
        from app.agent.result_validator import _extract_top_n
        assert _extract_top_n("what is the average fare") is None


# ============================================================
# TABLE EXTRACTION TESTS
# ============================================================

class TestTableExtraction:
    """Tests for extracting tables from SQL queries."""

    def _validate(self, sql):
        mock_schema = {
            "yellow_trips": [
                {"column": "pickup_datetime", "type": "timestamp"}
            ],
            "taxi_zones": [
                {"column": "location_id", "type": "smallint"}
            ],
        }
        from unittest.mock import patch
        with patch("app.agent.sql_validator.get_schema_info", return_value=mock_schema):
            from app.agent.sql_validator import validate_sql
            return validate_sql(sql)

    def test_simple_select(self):
        result = self._validate("SELECT COUNT(*) FROM yellow_trips;")
        assert result["valid"]

    def test_select_with_function(self):
        result = self._validate(
            "SELECT DATE(pickup_datetime) AS trip_date, COUNT(*) AS trip_count "
            "FROM yellow_trips GROUP BY DATE(pickup_datetime) ORDER BY trip_date;"
        )
        assert result["valid"]

    def test_select_with_join_and_alias(self):
        result = self._validate(
            "SELECT z.zone, COUNT(*) AS trip_count FROM yellow_trips t "
            "JOIN taxi_zones z ON t.pickup_location_id = z.location_id "
            "GROUP BY z.zone ORDER BY trip_count DESC LIMIT 5;"
        )
        assert result["valid"]

    def test_select_with_extract_function(self):
        result = self._validate(
            "SELECT EXTRACT(HOUR FROM pickup_datetime) AS pickup_hour, COUNT(*) AS trip_count "
            "FROM yellow_trips GROUP BY EXTRACT(HOUR FROM pickup_datetime) ORDER BY pickup_hour;"
        )
        assert result["valid"]

    def test_select_with_cte(self):
        result = self._validate(
            "WITH daily_trips AS ( "
            "SELECT DATE(pickup_datetime) AS trip_date, COUNT(*) AS trip_count "
            "FROM yellow_trips GROUP BY DATE(pickup_datetime) "
            ") SELECT * FROM daily_trips ORDER BY trip_date;"
        )
        assert result["valid"]

    def test_reject_invalid_table(self):
        result = self._validate("SELECT * FROM fake_table;")
        assert not result["valid"]
        assert any("fake_table" in e for e in result["errors"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
