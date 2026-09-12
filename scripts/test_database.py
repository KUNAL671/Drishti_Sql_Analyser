"""
test_database.py — Test Supabase Connection
=============================================
Tests that Python can connect to your Supabase PostgreSQL database.

Run from the project root:
    python scripts/test_database.py

What it checks:
  1. Can we connect to the database?
  2. Do the tables exist?
  3. How many rows are in each table?
"""

import sys
import os

# Add the project root to the Python path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import SUPABASE_DB_HOST, SUPABASE_DB_PORT, SUPABASE_DB_NAME, SUPABASE_DB_USER
from app.database.connection import test_connection, get_engine
from sqlalchemy import text

print("=" * 60)
print("SUPABASE CONNECTION TEST")
print("=" * 60)

# Show connection info (hiding the password)
print(f"\nHost:     {SUPABASE_DB_HOST}")
print(f"Port:     {SUPABASE_DB_PORT}")
print(f"Database: {SUPABASE_DB_NAME}")
print(f"User:     {SUPABASE_DB_USER}")

# ---- Test 1: Basic connection ----
print(f"\n--- Test 1: Connection ---")
success, message = test_connection()
if success:
    print(f"  PASS: {message}")
else:
    print(f"  FAIL: {message}")
    print("\nTroubleshooting:")
    print("  1. Check that .env exists in the project root")
    print("  2. Check SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD in .env")
    print("  3. Make sure your Supabase project is running")
    print("  4. Check if your IP is allowed in Supabase network settings")
    sys.exit(1)

# ---- Test 2: Check if tables exist ----
print(f"\n--- Test 2: Tables ---")
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """))
    tables = [row[0] for row in result]

if tables:
    print(f"  Found {len(tables)} table(s): {', '.join(tables)}")
else:
    print("  No tables found yet.")
    print("  Run the schema.sql in Supabase SQL Editor to create them.")

# ---- Test 3: Row counts ----
print(f"\n--- Test 3: Row counts ---")
with engine.connect() as conn:
    for table in tables:
        result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}";'))
        count = result.scalar()
        print(f"  {table}: {count:,} rows")

# ---- Test 4: Quick query ----
if "taxi_zones" in tables:
    print(f"\n--- Test 4: Sample taxi_zones data ---")
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT location_id, borough, zone FROM taxi_zones LIMIT 5;"
        ))
        rows = result.fetchall()
        for row in rows:
            print(f"  ID={row[0]}, Borough={row[1]}, Zone={row[2]}")
elif "yellow_trips" in tables:
    print(f"\n--- Test 4: Sample yellow_trips data ---")
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT trip_id, pickup_datetime, total_amount FROM yellow_trips LIMIT 3;"
        ))
        rows = result.fetchall()
        for row in rows:
            print(f"  ID={row[0]}, Pickup={row[1]}, Total=${row[2]}")

print(f"\n{'='*60}")
print("ALL TESTS PASSED!" if success else "SOME TESTS FAILED")
print(f"{'='*60}")
