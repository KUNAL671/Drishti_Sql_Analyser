import pytest
import pandas as pd
from app.database.executor import execute_query

class TestDataQuality:
    
    def test_all_valid_boroughs(self):
        """Test 1: All valid boroughs"""
        sql = "SELECT DISTINCT borough FROM taxi_zones WHERE borough IS NOT NULL AND borough != 'Unknown'"
        res = execute_query(sql)
        assert res["success"], res.get("error", "Unknown error")
        boroughs = set(res["data"]["borough"].tolist())
        expected_valid = {"Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island", "EWR"}
        # Ensure all expected boroughs are present
        assert expected_valid.issubset(boroughs), f"Missing boroughs: {expected_valid - boroughs}"
        
    def test_null_borough_handling(self):
        """Test 2: NULL borough handling"""
        # We check if there are any NULLs.
        # taxi_zones.borough is NOT NULL in the schema, so this should always return 0 rows.
        sql = "SELECT location_id FROM taxi_zones WHERE borough IS NULL"
        res = execute_query(sql)
        assert res["success"], res.get("error", "Unknown Error")
        assert len(res["data"]) == 0

    def test_unknown_borough_handling(self):
        """Test 3: Unknown borough handling"""
        # We expect location 264 and 265 to have 'Unknown' borough.
        sql = "SELECT location_id FROM taxi_zones WHERE borough = 'Unknown'"
        res = execute_query(sql)
        assert res["success"], res.get("error", "Unknown Error")
        unknown_locations = res["data"]["location_id"].tolist()
        assert 264 in unknown_locations
        assert 265 in unknown_locations

    def test_unmatched_pickup_location_id(self):
        """Test 4: Unmatched pickup_location_id"""
        sql = '''
            SELECT yt.pickup_location_id, COUNT(*) AS trip_count 
            FROM yellow_trips yt 
            LEFT JOIN taxi_zones tz ON yt.pickup_location_id = tz.location_id 
            WHERE tz.location_id IS NULL 
            GROUP BY yt.pickup_location_id
        '''
        res = execute_query(sql)
        assert res["success"], res.get("error", "Unknown error")
        assert len(res["data"]) == 0, "There should be NO unmatched pickup_location_ids"

    def test_duplicate_location_id(self):
        """Test 5: Duplicate location_id"""
        sql = '''
            SELECT location_id, COUNT(*) AS count 
            FROM taxi_zones 
            GROUP BY location_id 
            HAVING COUNT(*) > 1
        '''
        res = execute_query(sql)
        assert res["success"], res.get("error", "Unknown error")
        assert len(res["data"]) == 0, "There should be NO duplicate location_ids in taxi_zones"

    def test_average_fare_by_borough(self):
        """Test 6: Average fare by borough"""
        sql = '''
            SELECT tz.borough, AVG(yt.fare_amount) AS average_fare
            FROM yellow_trips yt
            JOIN taxi_zones tz ON yt.pickup_location_id = tz.location_id
            GROUP BY tz.borough
        '''
        res = execute_query(sql)
        assert res["success"], res.get("error", "Unknown error")
        boroughs = res["data"]["borough"].tolist()
        assert 'NaN' not in boroughs, "'NaN' should no longer exist in the grouped output"
        assert 'Unknown' in boroughs, "'Unknown' should exist due to location 264 and 265"

    def test_pickup_timestamp_preserves_time(self):
        """Test 7: Pickup timestamp preserves hour/minute/second"""
        sql = '''
            SELECT COUNT(*) AS exact_midnight_count
            FROM yellow_trips
            WHERE pickup_datetime::time = '00:00:00'
        '''
        res = execute_query(sql)
        assert res["success"], res.get("error", "Unknown error")
        # We expect 0 exact midnights in the sample (or very few)
        assert res["data"]["exact_midnight_count"].iloc[0] == 0, "Time components were lost!"

    def test_hour_distribution_realistic(self):
        """Test 8: Hour distribution is not artificially collapsed"""
        sql = '''
            SELECT EXTRACT(HOUR FROM pickup_datetime) AS pickup_hour, COUNT(*) AS trip_count
            FROM yellow_trips
            GROUP BY EXTRACT(HOUR FROM pickup_datetime)
            ORDER BY trip_count DESC
        '''
        res = execute_query(sql)
        assert res["success"], res.get("error", "Unknown error")
        df = res["data"]
        
        # Ensure we have trips across multiple hours
        assert len(df) > 10, "Hour distribution is artificially collapsed"
        
        # Ensure the top hour does not contain > 90% of all trips (sampling bias)
        total_trips = df["trip_count"].sum()
        max_trips = df["trip_count"].max()
        assert (max_trips / total_trips) < 0.9, f"Sampling bias detected: 1 hour has {max_trips/total_trips*100}% of trips"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
