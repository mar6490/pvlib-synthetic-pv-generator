"""I/O helpers for synthetic PV generation.

These functions focus on loading the input data (weather CSV and site metadata)
with strict validation so that downstream PV modeling can rely on clean inputs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REQUIRED_WEATHER_COLUMNS = ["time", "ghi", "dhi", "t_luft", "v_wind"]
REQUIRED_META_KEYS = {"lat", "lon", "tz"}
TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
EXPECTED_HEADER = "time;ghi;dhi;t_luft;v_wind"
EXAMPLE_TIMESTAMP = "2025-01-01 00:00:00+01:00"


def load_site_meta(path: str | Path) -> dict:
    """Load site metadata from JSON with validation.

    The metadata must include latitude, longitude, and timezone, which are
    required by pvlib to compute solar position and localize timestamps.
    """
    meta_path = Path(path)
    if not meta_path.exists():
        raise FileNotFoundError(f"Site metadata file not found: {meta_path}")

    with meta_path.open("r", encoding="utf-8") as handle:
        meta = json.load(handle)

    missing = REQUIRED_META_KEYS - set(meta.keys())
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Site metadata missing required keys: {missing_str}")

    return meta


def _invalid_time_examples(time_series: pd.Series, mask: pd.Series) -> str:
    examples = time_series.loc[mask].astype(str).head(5).tolist()
    return ", ".join(examples)


def load_weather(path: str | Path, tz: str) -> pd.DataFrame:
    """Load weather CSV, validate columns, and return timezone-aware data.

    Only one strict format is accepted:
    - Semicolon-separated CSV with header: time;ghi;dhi;t_luft;v_wind
    - Time strings formatted as YYYY-MM-DD HH:MM:SS±HH:MM (timezone offset required)
    - 15-minute continuous resolution
    """
    weather_path = Path(path)
    if not weather_path.exists():
        raise FileNotFoundError(f"Weather CSV not found: {weather_path}")

    try:
        weather = pd.read_csv(weather_path, sep=";")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            "Expected a semicolon-separated CSV (sep=';') with header: "
            f"{EXPECTED_HEADER}"
        ) from exc

    if list(weather.columns) != REQUIRED_WEATHER_COLUMNS:
        found = ", ".join(weather.columns)
        raise ValueError(
            "Weather data columns do not match expected header. "
            f"Found: {found}. Expected: {EXPECTED_HEADER}"
        )

    if "time" not in weather.columns:
        raise ValueError(
            "Weather data missing 'time' column. Expected header: "
            f"{EXPECTED_HEADER}"
        )

    time_series = weather["time"].astype(str)
    invalid_mask = ~time_series.str.match(TIME_PATTERN)
    if invalid_mask.any():
        invalid_count = int(invalid_mask.sum())
        examples = _invalid_time_examples(time_series, invalid_mask)
        raise ValueError(
            "Weather data contains timestamps that do not match the required format. "
            f"Invalid count: {invalid_count}. Examples: {examples}. "
            "Expected format: YYYY-MM-DD HH:MM:SS±HH:MM, "
            f"e.g. {EXAMPLE_TIMESTAMP}."
        )

    # Parse all timestamp strings as timezone-aware datetimes in UTC first.
    # Parsing in UTC is robust because all inputs include an explicit offset.
    timestamps = pd.to_datetime(time_series, utc=True, errors="coerce")
    nat_mask = timestamps.isna()
    if nat_mask.any():
        invalid_count = int(nat_mask.sum())
        examples = _invalid_time_examples(time_series, nat_mask)
        raise ValueError(
            "Weather data contains unparsable timestamps after UTC conversion. "
            f"Invalid count: {invalid_count}. Examples: {examples}. "
            "Expected format: YYYY-MM-DD HH:MM:SS±HH:MM, "
            f"e.g. {EXAMPLE_TIMESTAMP}."
        )

    weather = weather.set_index(timestamps)
    weather.index.name = "time"

    # Convert the index to the site timezone from metadata.
    # This keeps local-clock interpretation intuitive for users and tests.
    weather.index = weather.index.tz_convert(tz)
    weather = weather.sort_index()

    duplicate_mask = weather.index.duplicated(keep=False)
    if duplicate_mask.any():
        duplicate_count = int(duplicate_mask.sum())
        examples = ", ".join(weather.index[duplicate_mask].astype(str).unique()[:5])
        raise ValueError(
            "Weather data contains duplicate timestamps. "
            f"Duplicate count: {duplicate_count}. Examples: {examples}."
        )

    time_diffs = weather.index.to_series().diff().dropna()
    expected_step = pd.Timedelta(minutes=15)
    irregular_mask = time_diffs != expected_step
    if irregular_mask.any():
        irregular_indices = time_diffs[irregular_mask].index
        examples = []
        for current in irregular_indices[:5]:
            previous = current - time_diffs.loc[current]
            examples.append(f"{previous} -> {current}")
        raise ValueError(
            "Weather data has irregular time steps. "
            f"Irregular count: {int(irregular_mask.sum())}. "
            f"Examples: {', '.join(examples)}. "
            "Expected resolution is exactly 15 minutes."
        )

    return weather
