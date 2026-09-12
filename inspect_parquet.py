"""
STAGE 1: Parquet File Inspector
================================
This script inspects the Yellow Taxi Trip Records Parquet file
and reports everything we need to know before designing the database.

What it does:
1. Opens the Parquet file
2. Shows all column names and their data types
3. Shows how many rows (trips) are in the file
4. Shows missing/null values per column
5. Shows the date range of trips
6. Shows sample records
7. Shows basic statistics to catch suspicious values
"""

import pyarrow.parquet as pq  # For reading the Parquet file efficiently
import pandas as pd           # For data analysis

# ---------- CONFIGURATION ----------
# Path to the Parquet file (update this if your file is in a different location)
PARQUET_FILE = r"d:\sql analyst\yellow_tripdata_2026-01.parquet"

# ---------- STEP 1: Read Parquet metadata without loading all data ----------
print("=" * 70)
print("STAGE 1: PARQUET FILE INSPECTION")
print("=" * 70)

# Read just the schema (column info) from the Parquet file — very fast
parquet_file = pq.ParquetFile(PARQUET_FILE)
schema = parquet_file.schema_arrow

print("\n📄 FILE INFO")
print(f"   File: {PARQUET_FILE}")
print(f"   Number of row groups: {parquet_file.metadata.num_row_groups}")
print(f"   Total rows (from metadata): {parquet_file.metadata.num_rows:,}")

# ---------- STEP 2: Show all columns and their data types ----------
print("\n📋 COLUMNS AND DATA TYPES")
print("-" * 50)
for i, field in enumerate(schema):
    print(f"   {i+1:2d}. {field.name:<30s}  →  {field.type}")
print(f"\n   Total columns: {len(schema)}")

# ---------- STEP 3: Load data into a Pandas DataFrame ----------
print("\n⏳ Loading data into memory (this may take a moment)...")
df = pd.read_parquet(PARQUET_FILE)
print(f"✅ Loaded {len(df):,} rows × {len(df.columns)} columns")

# ---------- STEP 4: Missing/null values ----------
print("\n🔍 MISSING VALUES PER COLUMN")
print("-" * 50)
null_counts = df.isnull().sum()
for col in df.columns:
    null_count = null_counts[col]
    null_pct = (null_count / len(df)) * 100
    status = "⚠️" if null_pct > 0 else "✅"
    print(f"   {status} {col:<30s}  {null_count:>10,} nulls  ({null_pct:.2f}%)")

# ---------- STEP 5: Date range ----------
print("\n📅 DATE RANGE")
print("-" * 50)
# Try to find datetime columns automatically
datetime_cols = df.select_dtypes(include=["datetime64", "datetimetz"]).columns.tolist()
if datetime_cols:
    for col in datetime_cols:
        min_val = df[col].min()
        max_val = df[col].max()
        print(f"   {col}: {min_val}  →  {max_val}")
else:
    print("   No datetime columns found. Checking for timestamp-like columns...")
    for col in df.columns:
        if "datetime" in col.lower() or "time" in col.lower() or "date" in col.lower():
            print(f"   {col}: dtype={df[col].dtype}, min={df[col].min()}, max={df[col].max()}")

# ---------- STEP 6: Sample records ----------
print("\n📝 FIRST 5 SAMPLE RECORDS")
print("-" * 50)
# Set display options so all columns are visible
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 30)
print(df.head(5).to_string())

print("\n📝 LAST 5 SAMPLE RECORDS")
print("-" * 50)
print(df.tail(5).to_string())

# ---------- STEP 7: Basic statistics ----------
print("\n📊 BASIC STATISTICS (Numerical Columns)")
print("-" * 50)
# Show statistics: count, mean, min, max, etc.
numeric_stats = df.describe().T  # Transpose for readability
# Select key stats
for col in numeric_stats.index:
    stats = numeric_stats.loc[col]
    print(f"\n   {col}:")
    print(f"      Count:  {stats['count']:>15,.0f}")
    print(f"      Mean:   {stats['mean']:>15,.2f}")
    print(f"      Std:    {stats['std']:>15,.2f}")
    print(f"      Min:    {stats['min']:>15,.2f}")
    print(f"      25%:    {stats['25%']:>15,.2f}")
    print(f"      50%:    {stats['50%']:>15,.2f}")
    print(f"      75%:    {stats['75%']:>15,.2f}")
    print(f"      Max:    {stats['max']:>15,.2f}")

# ---------- STEP 8: Suspicious values check ----------
print("\n⚠️  SUSPICIOUS VALUES CHECK")
print("-" * 50)

# Check for negative fares
for col in ["fare_amount", "total_amount", "tip_amount", "trip_distance"]:
    if col in df.columns:
        neg_count = (df[col] < 0).sum()
        if neg_count > 0:
            print(f"   🚨 {col}: {neg_count:,} negative values found!")
        else:
            print(f"   ✅ {col}: No negative values")

# Check for zero passenger counts
if "passenger_count" in df.columns:
    zero_pax = (df["passenger_count"] == 0).sum()
    print(f"   {'🚨' if zero_pax > 0 else '✅'} passenger_count: {zero_pax:,} trips with 0 passengers")

# Check for extreme trip distances
if "trip_distance" in df.columns:
    extreme_dist = (df["trip_distance"] > 200).sum()
    print(f"   {'🚨' if extreme_dist > 0 else '✅'} trip_distance: {extreme_dist:,} trips > 200 miles")

# Check for extreme fares
if "total_amount" in df.columns:
    extreme_fare = (df["total_amount"] > 1000).sum()
    print(f"   {'🚨' if extreme_fare > 0 else '✅'} total_amount: {extreme_fare:,} trips > $1,000")

# Check for trips outside expected date range
if datetime_cols:
    for col in datetime_cols:
        out_of_range = ((df[col].dt.year < 2024) | (df[col].dt.year > 2027)).sum()
        print(f"   {'🚨' if out_of_range > 0 else '✅'} {col}: {out_of_range:,} records outside 2024-2027 range")

# ---------- STEP 9: Unique values for categorical columns ----------
print("\n🏷️  UNIQUE VALUES FOR CATEGORICAL COLUMNS")
print("-" * 50)
for col in ["VendorID", "vendor_id", "RatecodeID", "rate_code_id",
            "store_and_fwd_flag", "payment_type", "Payment_type"]:
    if col in df.columns:
        unique_vals = df[col].dropna().unique()
        print(f"   {col}: {sorted(unique_vals)}")

# ---------- STEP 10: Data types summary ----------
print("\n🔧 PANDAS DATA TYPES")
print("-" * 50)
for col in df.columns:
    print(f"   {col:<30s}  →  {df[col].dtype}")

print("\n" + "=" * 70)
print("INSPECTION COMPLETE!")
print("=" * 70)
print("\nNext step: Share the output above so we can design the database schema.")
