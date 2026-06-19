"""
Transform raw SMHI observation JSON into tidy rows ready for loading.

A "tidy row" here is a flat dict: one row per (station, parameter, timestamp)
measurement, matching the eventual Postgres table shape.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def parse_observations(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert one raw SMHI response (one station/parameter combo) into tidy rows.

    Skips individual readings that are missing or malformed instead of
    failing the whole batch — SMHI occasionally returns blank values.
    """
    station_id = int(raw["station"]["key"])
    station_name = raw["station"]["name"]
    parameter_id = int(raw["parameter"]["key"])
    metric = raw["parameter"]["name"]
    unit = raw["parameter"]["unit"]

    rows = []
    for entry in raw.get("value", []):
        try:
            timestamp = datetime.fromtimestamp(entry["date"] / 1000, tz=timezone.utc)
            value = float(entry["value"])
        except (KeyError, TypeError, ValueError):
            logger.warning(
                "Skipping malformed observation for station=%s parameter=%s: %r",
                station_id,
                parameter_id,
                entry,
            )
            continue

        rows.append(
            {
                "station_id": station_id,
                "station_name": station_name,
                "parameter_id": parameter_id,
                "metric": metric,
                "unit": unit,
                "timestamp": timestamp,
                "value": value,
                "quality": entry.get("quality"),
            }
        )
    return rows


def transform_all(raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten a list of raw SMHI responses into one list of tidy rows."""
    rows: list[dict[str, Any]] = []
    for raw in raw_results:
        rows.extend(parse_observations(raw))
    logger.info("Transformed %d raw response(s) into %d row(s)", len(raw_results), len(rows))
    return rows
