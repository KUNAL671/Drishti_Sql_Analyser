"""Create tables and load sample data in one go."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.connection import get_engine
from sqlalchemy import text

engine = get_engine()

# Step 1: Create tables from schema.sql
print("Creating tables...")
schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
with open(schema_path, "r") as f:
    schema_sql = f.read()

with engine.begin() as conn:
    conn.execute(text(schema_sql))
print("  Tables created!")

# Step 2: Verify tables exist
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name;"
    ))
    tables = [r[0] for r in result]
    print(f"  Found tables: {tables}")

print("\nDone! Now run:  python scripts/load_data.py --sample 10000")
