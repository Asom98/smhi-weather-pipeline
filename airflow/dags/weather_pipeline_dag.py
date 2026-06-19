"""
Airflow DAG that runs the same extract -> transform -> load pipeline as
src/pipeline.py, but as three separate, dependent tasks.

This is an orchestration showcase, run locally — it imports and calls the
exact same functions GitHub Actions uses, so the ETL logic itself lives in
one place (src/) and is never duplicated.
"""

from __future__ import annotations

import os
from datetime import datetime

from airflow.decorators import dag, task


@dag(
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["weather"],
)
def weather_pipeline():
    @task
    def extract() -> list[dict]:
        from src.extract import fetch_all

        station_ids = [int(s) for s in os.environ["SMHI_STATION_IDS"].split(",")]
        parameter_ids = [int(p) for p in os.environ["SMHI_PARAMETER_IDS"].split(",")]
        return fetch_all(station_ids, parameter_ids)

    @task
    def transform(raw_results: list[dict]) -> list[dict]:
        from src.transform import transform_all

        rows = transform_all(raw_results)
        # XCom serializes task output to JSON, which can't handle datetime
        # objects directly — convert to ISO strings for the hop to load().
        for row in rows:
            row["timestamp"] = row["timestamp"].isoformat()
        return rows

    @task
    def load(rows: list[dict]) -> None:
        from src.db import ensure_schema, get_connection
        from src.load import load_rows

        for row in rows:
            row["timestamp"] = datetime.fromisoformat(row["timestamp"])

        conn = get_connection()
        try:
            ensure_schema(conn)
            load_rows(conn, rows)
        finally:
            conn.close()

    load(transform(extract()))


weather_pipeline()
