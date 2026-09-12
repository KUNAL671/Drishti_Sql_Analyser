"""
connection.py — Supabase PostgreSQL Connection
================================================
Manages the connection to the Supabase PostgreSQL database
using SQLAlchemy for cleaner connection management.

Other modules use get_engine() for SQLAlchemy operations
or get_connection() for raw psycopg2 connections.
"""

from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

# Create a reusable SQLAlchemy engine (connection pool)
# pool_pre_ping=True tests the connection before using it
_engine = None


def get_engine():
    """
    Get the SQLAlchemy engine (creates it on first call).
    The engine manages a pool of database connections.

    Returns:
        sqlalchemy.engine.Engine
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,    # Test connection health before use
            pool_size=5,           # Max connections in the pool
            max_overflow=2,        # Extra connections allowed when pool is full
            pool_timeout=30,       # Seconds to wait for a connection
            connect_args={
                "connect_timeout": 10,           # 10s connection timeout
                "options": "-c statement_timeout=30000",  # 30s query timeout
            },
        )
    return _engine


def test_connection():
    """
    Test whether we can connect to the Supabase PostgreSQL database.

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            return True, f"Connected to Supabase! PostgreSQL: {version}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"
