"""
load_data.py — Load Data into Supabase PostgreSQL
====================================================
Loads taxi zones and yellow taxi trips into Supabase.

Usage:
    # Load taxi zones + 10,000 sample trip rows (for testing)
    python scripts/load_data.py --sample 10000

    # Load taxi zones + ALL 3.7M trip rows (full dataset)
    python scripts/load_data.py --full

    # Load only taxi zones (no trip data)
    python scripts/load_data.py --zones-only

Features:
    - Batch inserts for efficiency
    - Progress reporting
    - Duplicate prevention (clears table before loading)
    - Graceful error handling with batch-level reporting
"""

import argparse
import sys
import os
import time

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import pyarrow.parquet as pq
from sqlalchemy import text
from app.config import PARQUET_FILE, TAXI_ZONES_CSV
from app.database.connection import get_engine, test_connection


# Mapping: Parquet column names → database column names
COLUMN_RENAME = {
    "VendorID": "vendor_id",
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "passenger_count": "passenger_count",
    "trip_distance": "trip_distance",
    "RatecodeID": "rate_code_id",
    "store_and_fwd_flag": "store_and_fwd_flag",
    "PULocationID": "pickup_location_id",
    "DOLocationID": "dropoff_location_id",
    "payment_type": "payment_type",
    "fare_amount": "fare_amount",
    "extra": "extra",
    "mta_tax": "mta_tax",
    "tip_amount": "tip_amount",
    "tolls_amount": "tolls_amount",
    "improvement_surcharge": "improvement_surcharge",
    "total_amount": "total_amount",
    "congestion_surcharge": "congestion_surcharge",
    "Airport_fee": "airport_fee",
    "cbd_congestion_fee": "cbd_congestion_fee",
}

# Database columns in insert order (matches schema.sql, excludes trip_id)
DB_COLUMNS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime",
    "passenger_count", "trip_distance", "rate_code_id",
    "store_and_fwd_flag", "pickup_location_id", "dropoff_location_id",
    "payment_type", "fare_amount", "extra", "mta_tax",
    "tip_amount", "tolls_amount", "improvement_surcharge",
    "total_amount", "congestion_surcharge", "airport_fee",
    "cbd_congestion_fee",
]


def load_taxi_zones(engine):
    """Load the 265 NYC taxi zones from CSV into the taxi_zones table."""
    print("\n--- Loading Taxi Zones ---")

    if not os.path.exists(str(TAXI_ZONES_CSV)):
        print(f"  ERROR: File not found: {TAXI_ZONES_CSV}")
        return False

    df = pd.read_csv(str(TAXI_ZONES_CSV))
    print(f"  Read {len(df)} zones from CSV")

    # Rename columns to match our schema
    df = df.rename(columns={
        "LocationID": "location_id",
        "Borough": "borough",
        "Zone": "zone",
    })

    # Replace NaN with appropriate string defaults since schema is NOT NULL
    df['borough'] = df['borough'].fillna('Unknown')
    df['zone'] = df['zone'].fillna('Unknown')
    df['service_zone'] = df['service_zone'].fillna('N/A')

    with engine.begin() as conn:
        # Clear existing data to prevent duplicates
        conn.execute(text("DELETE FROM taxi_zones;"))

        # Insert each zone
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO taxi_zones (location_id, borough, zone, service_zone)
                    VALUES (:loc_id, :borough, :zone, :svc_zone)
                """),
                {
                    "loc_id": int(row["location_id"]),
                    "borough": row["borough"],
                    "zone": row["zone"],
                    "svc_zone": row["service_zone"],
                },
            )

    print(f"  Loaded {len(df)} taxi zones.")
    return True


def load_trip_data(engine, max_rows=None, batch_size=5000):
    """
    Load yellow taxi trip data from Parquet into the yellow_trips table.

    Args:
        engine: SQLAlchemy engine
        max_rows: If set, only load this many rows (sample mode).
                  If None, load all rows (full mode).
        batch_size: Rows per INSERT batch (default 5000)
    """
    mode = f"sample ({max_rows:,} rows)" if max_rows else "FULL (all rows)"
    print(f"\n--- Loading Trip Data [{mode}] ---")

    if not os.path.exists(str(PARQUET_FILE)):
        print(f"  ERROR: File not found: {PARQUET_FILE}")
        return False

    # Read the Parquet file
    print(f"  Reading Parquet file...")
    df = pd.read_parquet(str(PARQUET_FILE))
    total_available = len(df)
    print(f"  File contains {total_available:,} rows")

    # Apply row limit for sample mode
    if max_rows and max_rows < total_available:
        df = df.sample(n=max_rows, random_state=42)
        print(f"  Using random {max_rows:,} rows (sample mode)")

    total_to_load = len(df)

    # Rename columns to match database schema
    df = df.rename(columns=COLUMN_RENAME)

    # Replace NaN with None for proper NULL handling
    df = df.where(pd.notnull(df), None)

    # Clear existing data to prevent duplicates
    print(f"  Clearing existing trip data...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE yellow_trips RESTART IDENTITY;"))

    # Use pandas to_sql for fast insertion
    start_time = time.time()
    try:
        df.to_sql("yellow_trips", engine, if_exists="append", index=False, method="multi", chunksize=1000)
        inserted = len(df)
    except Exception as e:
        print(f"  ERROR inserting data: {e}")
        return False

    elapsed = time.time() - start_time
    print(f"\n  Done! Loaded {inserted:,} rows in {elapsed:.1f} seconds")
    return True


def verify_data(engine, source_total_rows=3724889):
    """Run verification and anomaly detection queries after loading."""
    print("\n--- Verifying Loaded Data ---")

    with engine.connect() as conn:
        # Row counts
        zones = conn.execute(text("SELECT COUNT(*) FROM taxi_zones")).scalar()
        trips = conn.execute(text("SELECT COUNT(*) FROM yellow_trips")).scalar()
        print(f"  taxi_zones:   {zones:>12,} rows")
        print(f"  yellow_trips: {trips:>12,} rows")
        print(f"  source file:  {source_total_rows:>12,} rows")

        # Date range & Anomalies
        if trips > 0:
            result = conn.execute(text("""
                SELECT
                    MIN(pickup_datetime) AS min_pickup,
                    MAX(pickup_datetime) AS max_pickup,
                    MIN(dropoff_datetime) AS min_dropoff,
                    MAX(dropoff_datetime) AS max_dropoff,
                    COUNT(*) FILTER (WHERE pickup_datetime::time = '00:00:00') AS midnight_pickups,
                    COUNT(*) FILTER (WHERE pickup_datetime IS NULL) AS null_pickups,
                    (SELECT MAX(c) FROM (SELECT COUNT(*) AS c FROM yellow_trips GROUP BY EXTRACT(HOUR FROM pickup_datetime)) sub) AS max_hour_count
                FROM yellow_trips
            """))
            row = result.fetchone()
            
            print(f"  Pickup range:  {row[0]} -> {row[1]}")
            print(f"  Dropoff range: {row[2]} -> {row[3]}")
            
            midnight_pct = (row[4] / trips) * 100
            null_pct = (row[5] / trips) * 100
            max_hour_pct = (row[6] / trips) * 100
            
            print(f"  Midnight Pickups: {row[4]} ({midnight_pct:.2f}%)")
            print(f"  NULL Pickups:     {row[5]} ({null_pct:.2f}%)")
            print(f"  Peak Hour Concn:  {max_hour_pct:.2f}% of trips in one hour")
            
            # Anomaly Warnings
            if midnight_pct > 1.0:
                print(f"  [!] WARNING: {midnight_pct:.1f}% of pickup timestamps occur exactly at midnight. Verify timestamp loading.")
            if max_hour_pct > 50.0:
                print(f"  [!] WARNING: {max_hour_pct:.1f}% of pickups occurred in a single hour! Verify sampling strategy.")
            if null_pct > 0:
                print(f"  [!] WARNING: {null_pct:.1f}% of pickup timestamps are NULL.")

            # Sample query: top 3 pickup zones
            result = conn.execute(text("""
                SELECT tz.zone, COUNT(*) AS trips
                FROM yellow_trips yt
                JOIN taxi_zones tz ON yt.pickup_location_id = tz.location_id
                GROUP BY tz.zone
                ORDER BY trips DESC
                LIMIT 3
            """))
            print(f"\n  Top 3 pickup zones:")
            for row in result:
                print(f"    {row[0]}: {row[1]:,} trips")


def main():
    parser = argparse.ArgumentParser(
        description="Load NYC Yellow Taxi data into Supabase PostgreSQL"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--sample", type=int, metavar="N",
        help="Load N sample rows (e.g., --sample 10000)"
    )
    group.add_argument(
        "--full", action="store_true",
        help="Load ALL rows (3.7M — takes 10-30 minutes)"
    )
    group.add_argument(
        "--zones-only", action="store_true",
        help="Load only taxi zones (no trip data)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("DATA LOADER — AI Taxi Database Analyst")
    print("=" * 60)

    # Test connection first
    print("\nTesting Supabase connection...")
    success, msg = test_connection()
    if not success:
        print(f"  FAILED: {msg}")
        print("  Fix your .env file and try again.")
        sys.exit(1)
    print(f"  OK: {msg}")

    engine = get_engine()

    # Load taxi zones if explicitly requested, but do not force it for trip samples
    if args.zones_only:
        if not load_taxi_zones(engine):
            print("  Failed to load taxi zones. Aborting.")
            sys.exit(1)
        print("\n  Zones-only mode — skipping trip data.")
    elif args.sample:
        if not load_trip_data(engine, max_rows=args.sample):
            sys.exit(1)
    elif args.full:
        print("\n  WARNING: Full load will insert ~3.7M rows.")
        print("  This may take 10-30 minutes depending on your connection.")
        if not load_trip_data(engine, max_rows=None):
            sys.exit(1)

    # Verify
    verify_data(engine)

    print(f"\n{'='*60}")
    print("LOADING COMPLETE!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
