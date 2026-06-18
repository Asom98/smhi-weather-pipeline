"""
Pull raw observation data from the SMHI Open Data API.

SMHI API pattern:
  /parameter/{param_id}/station/{station_id}/period/latest-day/data.json
Returns hourly measurements for the last 24 h — no API key required.
"""

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

SMHI_BASE = "https://opendata-download-metobs.smhi.se/api/version/latest"
REQUEST_TIMEOUT = 30  # seconds


@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _fetch(url: str) -> dict[str, Any]:
    """GET a JSON URL with automatic retries on transient failures."""
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def fetch_observations(station_id: int, parameter_id: int) -> dict[str, Any]:
    """
    Fetch the latest-day observations for one station / parameter combination.

    Returns the raw SMHI JSON dict so callers can inspect it or pass it to transform.
    Raises httpx.HTTPStatusError if the station/parameter combo doesn't exist (404).
    """
    url = (
        f"{SMHI_BASE}/parameter/{parameter_id}"
        f"/station/{station_id}/period/latest-day/data.json"
    )
    logger.info("Fetching SMHI data: station=%s parameter=%s", station_id, parameter_id)
    data = _fetch(url)
    n = len(data.get("value", []))
    logger.info("  → %d observation(s) received", n)
    return data


def fetch_all(
    station_ids: list[int], parameter_ids: list[int]
) -> list[dict[str, Any]]:
    """
    Fetch observations for every (station, parameter) combination.

    Skips pairs that return a 404 (some stations don't measure all parameters)
    and logs a warning instead of crashing the whole pipeline.
    """
    results = []
    for station_id in station_ids:
        for parameter_id in parameter_ids:
            try:
                results.append(fetch_observations(station_id, parameter_id))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.warning(
                        "Station %s / parameter %s not found — skipping",
                        station_id,
                        parameter_id,
                    )
                else:
                    raise
    return results
