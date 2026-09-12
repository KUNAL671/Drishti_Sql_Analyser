"""
loader.py — Data Loader
=========================
Loads the Parquet file and taxi zone CSV into PostgreSQL.
Handles column renaming and batch inserts for efficiency.

Usage (run from project root):
    python -m app.database.loader
"""

import pandas as pd
import pyarrow.parquet as pq
from app.database.connection import get_connection
from app.database.schema import create_tables
from app.config import PARQUET_FILE, TAXI_ZONES_CSV


# Mapping from Parquet column names → PostgreSQL column names
COLUMN_RENAME_MAP = {
    "VendorID": "vendor_id",
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "passenger_count": "passenger_count",
    "trip_distance": "trip_distance",
    "RatecodeID": "rate_code_id",
    "store_and_fwd_flag": "store_and_fwd_flag",
    "PULocationID": "pu_location_id",
    "DOLocationID": "do_location_id",
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

# The columns we insert (in order) — matches schema.sql
DB_COLUMNS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime",
    "passenger_count", "trip_distance", "rate_code_id",
    "store_and_fwd_flag", "pu_location_id", "do_location_id",
    "payment_type", "fare_amount", "extra", "mta_tax",
    "tip_amount", "tolls_amount", "improvement_surcharge",
    "total_amount", "congestion_surcharge", "airport_fee",
    "cbd_congestion_fee",
]


def load_taxi_zones():
    """
    Load the taxi zone lookup data from CSV into PostgreSQL.

    The CSV file has columns: LocationID, Borough, Zone, service_zone
    """
    print("Loading taxi zones...")

    # Read the CSV file
    df = pd.read_csv(TAXI_ZONES_CSV)

    # Rename columns to match our database schema
    df = df.rename(columns={"LocationID": "location_id", "Borough": "borough", "Zone": "zone"})

    # Replace NaN with appropriate string defaults since schema is NOT NULL
    df['borough'] = df['borough'].fillna('Unknown')
    df['zone'] = df['zone'].fillna('Unknown')
    df['service_zone'] = df['service_zone'].fillna('N/A')

    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing data (safe because this is setup, not user-facing)
    cursor.execute("DELETE FROM taxi_zones;")

    # Insert each zone
    for _, row in df.iterrows():
        cursor.execute(
            """
            INSERT INTO taxi_zones (location_id, borough, zone, service_zone)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (location_id) DO NOTHING;
            """,
            (int(row["location_id"]), row["borough"], row["zone"], row["service_zone"]),
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"  Loaded {len(df)} taxi zones.")


def load_trip_data(batch_size: int = 50000):
    """
    Load the Yellow Taxi trip data from Parquet into PostgreSQL.
    Uses batch inserts for efficiency.

    Args:
        batch_size: Number of rows to insert per batch (default 50,000)
    """
    print(f"Loading trip data from: {PARQUET_FILE}")
    print("  This may take several minutes for 3.7M rows...")

    # Read the Parquet file
    df = pd.read_parquet(PARQUET_FILE)
    total_rows = len(df)
    print(f"  Read {total_rows:,} rows from Parquet file.")

    # Rename columns to match our database schema
    df = df.rename(columns=COLUMN_RENAME_MAP)

    # Convert NaN to None for proper NULL handling in PostgreSQL
    df = df.where(pd.notnull(df), None)

    conn = get_connection()
    cursor = conn.cursor()

    # Build the INSERT statement with placeholders
    placeholders = ", ".join(["%s"] * len(DB_COLUMNS))
    columns_str = ", ".join(DB_COLUMNS)
    insert_sql = f"INSERT INTO yellow_taxi_trips ({columns_str}) VALUES ({placeholders})"

    # Insert in batches for efficiency and progress tracking
    inserted = 0
    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)
        batch = df.iloc[start:end]

        # Convert each row to a tuple of values
        values_list = []
        for _, row in batch.iterrows():
            values = []
            for col in DB_COLUMNS:
                val = row[col]
                # Convert pandas types to Python native types
                if val is None:
                    values.append(None)
                elif hasattr(val, "item"):  # numpy scalar
                    values.append(val.item())
                elif pd.isna(val):
                    values.append(None)
                else:
                    values.append(val)
            values_list.append(tuple(values))

        # Use executemany for batch insert
        cursor.executemany(insert_sql, values_list)
        conn.commit()

        inserted += len(batch)
        pct = (inserted / total_rows) * 100
        print(f"  Inserted {inserted:>10,} / {total_rows:,} rows ({pct:.1f}%)")

    cursor.close()
    conn.close()
    print(f"  Done! Loaded {inserted:,} rows into yellow_taxi_trips.")


def load_all():
    """
    Complete data loading pipeline:
    1. Create tables
    2. Load taxi zones
    3. Load trip data
    """
    print("=" * 60)
    print("DATA LOADING PIPELINE")
    print("=" * 60)

    # Step 1: Create tables
    print("\nStep 1: Creating tables...")
    success, msg = create_tables()
    print(f"  {msg}")
    if not success:
        print("  ABORTING: Could not create tables.")
        return

    # Step 2: Load taxi zones
    print("\nStep 2: Loading taxi zones...")
    load_taxi_zones()

    # Step 3: Check if trip data already exists
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM yellow_taxi_trips;")
    existing_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    if existing_count > 0:
        print(f"\nStep 3: Trip data already loaded ({existing_count:,} rows).")
        print("  Skipping data load. Delete rows first if you want to reload.")
    else:
        print("\nStep 3: Loading trip data...")
        load_trip_data()

    print("\n" + "=" * 60)
    print("DATA LOADING COMPLETE!")
    print("=" * 60)


# Allow running this file directly: python -m app.database.loader
if __name__ == "__main__":
    load_all()
