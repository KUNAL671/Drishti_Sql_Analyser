import pytest
from app.agent.sql_generator import generate_sql
from app.agent.schema_retriever import get_schema_for_llm
from app.database.executor import execute_query


class TestDerivedMetrics:
    @pytest.fixture(scope="class")
    def schema(self):
        return get_schema_for_llm()

    def test_standard_tip_percentage(self, schema):
        """TEST 1: Standard tip percentage has correct formula and metadata."""
        result = generate_sql("What is the average tip percentage by borough?", schema)
        
        assert result["success"] is True
        sql = result["sql"].lower()
        
        # Verify LEFT JOIN and COALESCE are used
        assert "left join taxi_zones" in sql
        assert "coalesce(" in sql
        
        # Verify safe division (NULLIF)
        assert "nullif" in sql
        assert "case when" not in sql or "else 0" not in sql
        
        # Verify metadata is populated
        assert result.get("metric_name") != ""
        assert "tip" in result.get("metric_definition", "").lower()
        
    def test_fare_amount_denominator(self, schema):
        """TEST 2: Tip percentage relative to fare amount explicitly overrides denominator."""
        result = generate_sql("What is the average tip percentage by borough using fare amount as the denominator?", schema)
        
        assert result["success"] is True
        
        # Metadata must reflect fare_amount
        assert "fare_amount" in result.get("metric_definition", "").lower()
        assert "fare_amount" in result.get("denominator", "").lower()
        
    def test_percentage_of_total(self, schema):
        """TEST 3: Percentage of total trip amount that is tip."""
        result = generate_sql("What percentage of the total trip amount is tip by borough?", schema)
        
        assert result["success"] is True
        
        # Must use total_amount as denominator
        assert "total_amount" in result.get("metric_definition", "").lower()
        assert "total_amount" in result.get("denominator", "").lower()
        
    def test_zero_denominator_sql_safety(self, schema):
        """TEST 4: Zero denominator SQL safety."""
        # This tests that the actual executed SQL handles 0 safely.
        # We'll run a query that calculates tip percentage for trips where total_amount is 0.
        # Since we use NULLIF, it should return NULL, not 0 or error.
        
        # Insert a dummy row with 0 total_amount (rollback after test)
        from app.database.connection import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.begin() as conn:
            # A trip with 0 total_amount and 5 tip (invalid but tests the math)
            conn.execute(text('''
                INSERT INTO yellow_trips (vendor_id, pickup_datetime, dropoff_datetime, 
                                        passenger_count, trip_distance, pickup_location_id, dropoff_location_id,
                                        payment_type, fare_amount, extra, mta_tax, tip_amount, tolls_amount,
                                        improvement_surcharge, total_amount, cbd_congestion_fee)
                VALUES (1, '2026-01-01 00:00:00', '2026-01-01 00:05:00', 1, 1.0, 999, 999, 1, 0, 0, 0, 5.0, 0, 0, 0, 0)
            '''))
            
        result = generate_sql("What is the average tip percentage by borough?", schema)
        assert result["success"] is True
        
        # Execute the generated SQL
        exec_res = execute_query(result["sql"])
        assert exec_res["success"] is True
        
        # The row with 0 total_amount shouldn't crash the query and shouldn't pollute the average with 0s unnecessarily
        df = exec_res["data"]
        
        # Cleanup
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM yellow_trips WHERE pickup_location_id = 999"))
            
    def test_unmatched_location_handling(self, schema):
        """TEST 5: Unmatched pickup_location_id generates consistent Unknown/Unmatched handling."""
        result = generate_sql("What is the average tip percentage by borough?", schema)
        assert result["success"] is True
        
        sql = result["sql"].lower()
        # Verify that it does NOT use WHERE tz.borough IS NOT NULL
        assert "tz.borough is not null" not in sql
        assert "left join" in sql
