"""
STAGE 1: Parquet File Inspector
================================
Inspects the NYC Yellow Taxi Trip Records Parquet file
and reports everything needed to design the Supabase PostgreSQL schema.

Run from the project root:
    python scripts/inspect_parquet.py
"""

import pyarrow.parquet as pq
import pandas as pd
import os
import sys

# Path to the Parquet file
PARQUET_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "yellow_tripdata_2026-01.parquet")
PARQUET_FILE = os.path.abspath(PARQUET_FILE)

if not os.path.exists(PARQUET_FILE):
    print(f"ERROR: File not found: {PARQUET_FILE}")
    print("Make sure yellow_tripdata_2026-01.parquet is in the data/ folder.")
    sys.exit(1)

print("=" * 70)
print("STAGE 1: PARQUET FILE INSPECTION")
print("=" * 70)

# --- 1. File metadata (fast, no full load) ---
pf = pq.ParquetFile(PARQUET_FILE)
schema = pf.schema_arrow

print(f"\nFILE: {PARQUET_FILE}")
print(f"SIZE: {os.path.getsize(PARQUET_FILE) / (1024*1024):.1f} MB")
print(f"ROW GROUPS: {pf.metadata.num_row_groups}")
print(f"TOTAL ROWS: {pf.metadata.num_rows:,}")

# --- 2. Column names and Arrow types ---
print(f"\n{'='*70}")
print("COLUMNS AND DATA TYPES (from Parquet schema)")
print(f"{'='*70}")
print(f"{'#':<4} {'Column Name':<30} {'Arrow Type':<20}")
print("-" * 54)
for i, field in enumerate(schema):
    print(f"{i+1:<4} {field.name:<30} {str(field.type):<20}")
print(f"\nTotal columns: {len(schema)}")

# --- 3. Load into Pandas for deeper analysis ---
print(f"\nLoading data into memory...")
df = pd.read_parquet(PARQUET_FILE)
print(f"Loaded: {len(df):,} rows x {len(df.columns)} columns")

# --- 4. Pandas dtypes ---
print(f"\n{'='*70}")
print("PANDAS DATA TYPES")
print(f"{'='*70}")
print(f"{'Column Name':<30} {'Pandas dtype':<20}")
print("-" * 50)
for col in df.columns:
    print(f"{col:<30} {str(df[col].dtype):<20}")

# --- 5. Missing values ---
print(f"\n{'='*70}")
print("MISSING / NULL VALUES")
print(f"{'='*70}")
print(f"{'Column Name':<30} {'Nulls':>12} {'Percent':>10}")
print("-" * 52)
for col in df.columns:
    nulls = df[col].isnull().sum()
    pct = (nulls / len(df)) * 100
    marker = " <<<" if pct > 0 else ""
    print(f"{col:<30} {nulls:>12,} {pct:>9.2f}%{marker}")

# --- 6. Date range ---
print(f"\n{'='*70}")
print("DATE RANGE")
print(f"{'='*70}")
dt_cols = df.select_dtypes(include=["datetime64", "datetimetz"]).columns
for col in dt_cols:
    print(f"{col}:")
    print(f"  Min: {df[col].min()}")
    print(f"  Max: {df[col].max()}")

# --- 7. Sample records ---
print(f"\n{'='*70}")
print("FIRST 3 ROWS (transposed for readability)")
print(f"{'='*70}")
for idx in range(min(3, len(df))):
    print(f"\n--- Row {idx} ---")
    for col in df.columns:
        val = df.iloc[idx][col]
        print(f"  {col:<30} = {val}")

# --- 8. Statistics for numeric columns ---
print(f"\n{'='*70}")
print("NUMERIC COLUMN STATISTICS")
print(f"{'='*70}")
numeric_cols = df.select_dtypes(include=["number"]).columns
for col in numeric_cols:
    s = df[col].describe()
    print(f"\n  {col}:")
    print(f"    count:  {s['count']:>15,.0f}")
    print(f"    mean:   {s['mean']:>15,.2f}")
    print(f"    std:    {s['std']:>15,.2f}")
    print(f"    min:    {s['min']:>15,.2f}")
    print(f"    25%:    {s['25%']:>15,.2f}")
    print(f"    50%:    {s['50%']:>15,.2f}")
    print(f"    75%:    {s['75%']:>15,.2f}")
    print(f"    max:    {s['max']:>15,.2f}")

# --- 9. Unique values for categorical columns ---
print(f"\n{'='*70}")
print("UNIQUE VALUES (categorical / low-cardinality columns)")
print(f"{'='*70}")
for col in ["VendorID", "RatecodeID", "store_and_fwd_flag", "payment_type"]:
    if col in df.columns:
        uniques = sorted(df[col].dropna().unique().tolist())
        print(f"  {col}: {uniques}")

# --- 10. Suspicious values ---
print(f"\n{'='*70}")
print("SUSPICIOUS VALUES CHECK")
print(f"{'='*70}")

checks = {
    "fare_amount < 0": (df["fare_amount"] < 0).sum() if "fare_amount" in df.columns else 0,
    "total_amount < 0": (df["total_amount"] < 0).sum() if "total_amount" in df.columns else 0,
    "tip_amount < 0": (df["tip_amount"] < 0).sum() if "tip_amount" in df.columns else 0,
    "trip_distance < 0": (df["trip_distance"] < 0).sum() if "trip_distance" in df.columns else 0,
    "trip_distance > 200 miles": (df["trip_distance"] > 200).sum() if "trip_distance" in df.columns else 0,
    "total_amount > $1,000": (df["total_amount"] > 1000).sum() if "total_amount" in df.columns else 0,
    "passenger_count == 0": (df["passenger_count"] == 0).sum() if "passenger_count" in df.columns else 0,
}

for desc, count in checks.items():
    marker = " !!!" if count > 0 else ""
    print(f"  {desc:<35} {count:>10,}{marker}")

# Date range checks
for col in dt_cols:
    out = ((df[col].dt.year < 2024) | (df[col].dt.year > 2027)).sum()
    marker = " !!!" if out > 0 else ""
    print(f"  {col} outside 2024-2027: {out:>5,}{marker}")

# --- 11. Recommended PostgreSQL types ---
print(f"\n{'='*70}")
print("RECOMMENDED POSTGRESQL COLUMN MAPPING")
print(f"{'='*70}")

pg_mapping = {
    "VendorID":               ("vendor_id",             "SMALLINT",           "NOT NULL"),
    "tpep_pickup_datetime":   ("pickup_datetime",       "TIMESTAMP",          "NOT NULL"),
    "tpep_dropoff_datetime":  ("dropoff_datetime",      "TIMESTAMP",          "NOT NULL"),
    "passenger_count":        ("passenger_count",       "SMALLINT",           "NULL     -- 29% nulls"),
    "trip_distance":          ("trip_distance",         "DOUBLE PRECISION",   "NOT NULL"),
    "RatecodeID":             ("rate_code_id",          "SMALLINT",           "NULL     -- 29% nulls"),
    "store_and_fwd_flag":     ("store_and_fwd_flag",    "CHAR(1)",            "NULL     -- 29% nulls"),
    "PULocationID":           ("pickup_location_id",    "SMALLINT",           "NOT NULL"),
    "DOLocationID":           ("dropoff_location_id",   "SMALLINT",           "NOT NULL"),
    "payment_type":           ("payment_type",          "SMALLINT",           "NOT NULL"),
    "fare_amount":            ("fare_amount",           "NUMERIC(10,2)",      "NOT NULL"),
    "extra":                  ("extra",                 "NUMERIC(10,2)",      "NOT NULL"),
    "mta_tax":                ("mta_tax",               "NUMERIC(10,2)",      "NOT NULL"),
    "tip_amount":             ("tip_amount",            "NUMERIC(10,2)",      "NOT NULL"),
    "tolls_amount":           ("tolls_amount",          "NUMERIC(10,2)",      "NOT NULL"),
    "improvement_surcharge":  ("improvement_surcharge", "NUMERIC(10,2)",      "NOT NULL"),
    "total_amount":           ("total_amount",          "NUMERIC(10,2)",      "NOT NULL"),
    "congestion_surcharge":   ("congestion_surcharge",  "NUMERIC(10,2)",      "NULL     -- 29% nulls"),
    "Airport_fee":            ("airport_fee",           "NUMERIC(10,2)",      "NULL     -- 29% nulls"),
    "cbd_congestion_fee":     ("cbd_congestion_fee",    "NUMERIC(10,2)",      "NOT NULL"),
}

print(f"{'Parquet Column':<28} {'DB Column':<25} {'PG Type':<20} {'Nullable'}")
print("-" * 95)
for parquet_col, (db_col, pg_type, nullable) in pg_mapping.items():
    print(f"{parquet_col:<28} {db_col:<25} {pg_type:<20} {nullable}")

print(f"\n{'='*70}")
print("INSPECTION COMPLETE")
print(f"{'='*70}")
