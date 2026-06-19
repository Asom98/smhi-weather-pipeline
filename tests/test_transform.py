from datetime import datetime, timezone

from src.transform import parse_observations, transform_all


def make_raw(values):
    """Build a minimal fake SMHI response shape for testing."""
    return {
        "station": {"key": "52350", "name": "Malmö A"},
        "parameter": {"key": "1", "name": "Lufttemperatur", "unit": "celsius"},
        "value": values,
    }


def test_parse_observations_happy_path():
    raw = make_raw([{"date": 1781776800000, "value": "20.9", "quality": "G"}])

    rows = parse_observations(raw)

    assert rows == [
        {
            "station_id": 52350,
            "station_name": "Malmö A",
            "parameter_id": 1,
            "metric": "Lufttemperatur",
            "unit": "celsius",
            "timestamp": datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
            "value": 20.9,
            "quality": "G",
        }
    ]


def test_parse_observations_skips_malformed_entries():
    raw = make_raw(
        [
            {"date": 1781776800000, "value": "20.9", "quality": "G"},
            {"date": 1781780400000, "value": None, "quality": "Y"},  # missing value
            {"date": 1781784000000, "value": "not-a-number", "quality": "G"},
        ]
    )

    rows = parse_observations(raw)

    assert len(rows) == 1
    assert rows[0]["value"] == 20.9


def test_transform_all_flattens_multiple_responses():
    raw_one = make_raw([{"date": 1781776800000, "value": "20.9", "quality": "G"}])
    raw_two = make_raw([{"date": 1781780400000, "value": "21.5", "quality": "G"}])

    rows = transform_all([raw_one, raw_two])

    assert len(rows) == 2
    assert [r["value"] for r in rows] == [20.9, 21.5]
