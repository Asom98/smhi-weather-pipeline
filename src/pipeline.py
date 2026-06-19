"""
Orchestrates the full extract -> transform -> load run.

Entry point: `python -m src.pipeline`
Reads station/parameter selection and DATABASE_URL from environment
variables (loaded from .env locally, or from GitHub Secrets in CI).
"""

import logging
import os

from dotenv import load_dotenv

from src.db import ensure_schema, get_connection
from src.extract import fetch_all
from src.load import load_rows
from src.transform import transform_all

logger = logging.getLogger(__name__)


def _parse_int_list(env_value: str) -> list[int]:
    return [int(item.strip()) for item in env_value.split(",") if item.strip()]


def run() -> None:
    station_ids = _parse_int_list(os.environ["SMHI_STATION_IDS"])
    parameter_ids = _parse_int_list(os.environ["SMHI_PARAMETER_IDS"])

    logger.info(
        "Starting pipeline run: stations=%s parameters=%s", station_ids, parameter_ids
    )

    raw_results = fetch_all(station_ids, parameter_ids)
    rows = transform_all(raw_results)

    conn = get_connection()
    try:
        ensure_schema(conn)
        load_rows(conn, rows)
    finally:
        conn.close()

    logger.info("Pipeline run complete: %d row(s) processed", len(rows))


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    run()


if __name__ == "__main__":
    main()
