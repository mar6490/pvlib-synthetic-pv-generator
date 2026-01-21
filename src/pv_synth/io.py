"""I/O helpers for synthetic PV generation.

These functions focus on loading the input data (weather CSV and site metadata)
with strict validation so that downstream PV modeling can rely on clean inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REQUIRED_WEATHER_COLUMNS = {"time", "ghi", "dhi", "t_luft", "v_wind"}
REQUIRED_META_KEYS = {"lat", "lon", "tz"}


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


def load_weather(path: str | Path, tz: str) -> pd.DataFrame:
    """Load weather CSV, validate columns, and localize to timezone.

    The weather file is expected to contain local timestamps (no UTC offset).
    We localize to the provided timezone (e.g. Europe/Berlin) so pvlib can
    calculate solar geometry correctly.
    """
    weather_path = Path(path)
    if not weather_path.exists():
        raise FileNotFoundError(f"Weather CSV not found: {weather_path}")

    # Read the CSV as-is; validation happens below.
    weather = pd.read_csv(weather_path)
    missing = REQUIRED_WEATHER_COLUMNS - set(weather.columns)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Weather data missing required columns: {missing_str}")

    # Parse timestamps; invalid strings become NaT and are rejected below.
    weather["time"] = pd.to_datetime(weather["time"], errors="coerce")
    if weather["time"].isna().any():
        raise ValueError("Weather data contains invalid timestamps in 'time' column")

    # Localize timestamps to the site timezone. Handling for DST transitions:
    # - ambiguous="infer": let pandas infer repeated hour when DST ends
    # - nonexistent="shift_forward": shift forward for missing hour when DST starts
    try:
        localized = weather["time"].dt.tz_localize(
            tz, ambiguous="infer", nonexistent="shift_forward"
        )
    except Exception:
        # If inference fails (e.g., repeated hour cannot be resolved), mark
        # ambiguous timestamps as NaT and drop them below with a clear error.
        localized = weather["time"].dt.tz_localize(
            tz, ambiguous="NaT", nonexistent="shift_forward"
        )
    if localized.isna().any():
        raise ValueError("Weather data timestamps could not be localized")

    # Use time as the index for easier alignment in pvlib calculations.
    weather = weather.set_index(localized).drop(columns=["time"])
    weather.index.name = "time"

    return weather
