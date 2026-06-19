"""
Load tidy observation rows into Postgres.

Uses an upsert (INSERT ... ON CONFLICT ... DO UPDATE) so re-running the
pipeline over overlapping data is idempotent: no duplicate rows, and
unchanged measurements are simply rewritten with the same values.
"""

import logging
from typing import Any

from psycopg2.extensions import connection as Connection
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

COLUMNS = [
    "station_id",
    "station_name",
    "parameter_id",
    "metric",
    "unit",
    "timestamp",
    "value",
    "quality",
]

UPSERT_SQL = f"""
    INSERT INTO observations ({", ".join(COLUMNS)})
    VALUES %s
    ON CONFLICT (station_id, parameter_id, timestamp)
    DO UPDATE SET
        station_name = EXCLUDED.station_name,
        metric = EXCLUDED.metric,
        unit = EXCLUDED.unit,
        value = EXCLUDED.value,
        quality = EXCLUDED.quality
"""


def load_rows(conn: Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert tidy rows into the observations table. Returns the row count."""
    if not rows:
        logger.info("No rows to load")
        return 0

    values = [[row[col] for col in COLUMNS] for row in rows]
    with conn.cursor() as cur:
        execute_values(cur, UPSERT_SQL, values)
    conn.commit()
    logger.info("Upserted %d row(s)", len(rows))
    return len(rows)
