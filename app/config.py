"""
config.py — Central Configuration
===================================
Loads all settings from the .env file.
Every other module imports settings from here.

IMPORTANT: Never hard-code passwords or API keys.
           Always use environment variables via .env.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load the .env file from the project root
# Path(__file__) = this file (config.py)
# .parent       = app/
# .parent       = project root (sql-analyst/)
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# ---- Supabase PostgreSQL Connection ----
SUPABASE_DB_HOST = os.getenv("SUPABASE_DB_HOST", "")
SUPABASE_DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
SUPABASE_DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")
SUPABASE_DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")

# Full connection URL for SQLAlchemy
DATABASE_URL = (
    f"postgresql+psycopg2://{SUPABASE_DB_USER}:{SUPABASE_DB_PASSWORD}"
    f"@{SUPABASE_DB_HOST}:{SUPABASE_DB_PORT}/{SUPABASE_DB_NAME}"
)

# ---- Gemini AI Configuration ----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# ---- Data Files ----
DATA_DIR = PROJECT_ROOT / "data"
PARQUET_FILE = DATA_DIR / "yellow_tripdata_2026-01.parquet"
TAXI_ZONES_CSV = DATA_DIR / "taxi_zones.csv"
SQL_DIR = PROJECT_ROOT / "sql"

# ---- Dataset Metadata ----
DATASET_NAME = "NYC Yellow Taxi Trip Records"
SOURCE_FILE = "yellow_tripdata_2026-01.parquet"
SOURCE_PERIOD = "January 2026"
SOURCE_ROW_COUNT = 3724889  # Total rows in the parquet file
LOADED_ROW_COUNT = 5000     # Rows currently loaded into the DB
DATASET_MODE = "Development sample"

# ---- Agent Configuration ----
MAX_RETRY_ATTEMPTS = 3         # Maximum SQL regeneration attempts
SQL_RESULT_ROW_LIMIT = 1000   # Max rows returned per query

# ---- Upload Configuration ----
MAX_UPLOAD_SIZE_MB = 200       # Maximum upload file size in MB
MAX_UPLOAD_ROWS = 500_000      # Maximum rows per uploaded dataset
MAX_UPLOAD_COLUMNS = 100       # Maximum columns per uploaded dataset
SUPPORTED_FILE_TYPES = ["csv", "parquet", "xlsx", "xls"]
DATASETS_TABLE = "drishti_datasets"
