"""
Postgres connection handling and schema setup.

Reads the connection string from the DATABASE_URL env var so the same code
works against local Docker Postgres, Neon, or CI — only the env var changes.
"""

import logging
import os
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as Connection

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def get_connection() -> Connection:
    """Open a new Postgres connection using DATABASE_URL."""
    database_url = os.environ["DATABASE_URL"]
    return psycopg2.connect(database_url)


def ensure_schema(conn: Connection) -> None:
    """Create the observations table if it doesn't already exist."""
    sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logger.info("Schema ensured (table created if missing)")
