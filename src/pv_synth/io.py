"""I/O helpers for synthetic PV generation."""

from __future__ import annotations

from datetime import timedelta, timezone
import json
from pathlib import Path
import re

import pandas as pd

REQUIRED_WEATHER_COLUMNS = ["time", "ghi", "dhi", "t_luft", "v_wind"]
REQUIRED_META_KEYS = {"lat", "lon", "tz"}
TIME_PATTERN_WITH_OFFSET = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
TIME_PATTERN_NAIVE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
EXPECTED_HEADER = "time;ghi;dhi;t_luft;v_wind"
DEFAULT_FIXED_OFFSET_MINUTES = 60
DEFAULT_FIXED_TZ = timezone(timedelta(minutes=DEFAULT_FIXED_OFFSET_MINUTES))
DEFAULT_TZ_NAME = "UTC+01:00"


def load_site_meta(path: str | Path) -> dict:
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


def parse_weather_time(
    series: pd.Series,
    weather_timestamp: str,
    fixed_offset_minutes: int,
) -> pd.DatetimeIndex:
    """Parse weather timestamps into fixed UTC+offset timezone-aware index."""
    if weather_timestamp not in {"with_offset", "naive"}:
        raise ValueError("weather_timestamp must be 'with_offset' or 'naive'.")

    fixed_tz = timezone(timedelta(minutes=fixed_offset_minutes))

    if weather_timestamp == "with_offset":
        invalid_mask = ~series.str.match(TIME_PATTERN_WITH_OFFSET)
        if invalid_mask.any():
            raise ValueError(
                "Timestamps must include an explicit offset (±HH:MM) when "
                "--weather-timestamp=with_offset."
            )
        timestamps_utc = pd.to_datetime(series, errors="raise", utc=True)
        return pd.DatetimeIndex(timestamps_utc).tz_convert(fixed_tz)

    invalid_mask = ~series.str.match(TIME_PATTERN_NAIVE)
    if invalid_mask.any():
        raise ValueError(
            "Timestamps must be naive format YYYY-MM-DD HH:MM:SS when "
            "--weather-timestamp=naive."
        )

    naive = pd.to_datetime(series, errors="raise")
    localized = naive.dt.tz_localize(fixed_tz)
    return pd.DatetimeIndex(localized)


def _validate_time_regular(weather: pd.DataFrame) -> None:
    duplicate_mask = weather.index.duplicated(keep=False)
    if duplicate_mask.any():
        raise ValueError("Weather data contains duplicate timestamps.")

    time_diffs = weather.index.to_series().diff().dropna()
    if time_diffs.empty:
        return

    reference_step = time_diffs.mode().iloc[0]
    irregular_mask = time_diffs != reference_step
    if irregular_mask.any():
        first = time_diffs[irregular_mask].index[0]
        previous = first - time_diffs.loc[first]
        raise ValueError(
            "Weather data has irregular time steps. "
            f"First gap around: {previous} -> {first}. "
            f"Expected consistent resolution of {reference_step}."
        )


def _assert_fixed_offset_index(index: pd.DatetimeIndex, fixed_offset_minutes: int) -> None:
    if index.tz is None:
        raise ValueError("Weather index must be timezone-aware.")
    offsets = index.strftime("%z").unique().tolist()
    expected = f"{fixed_offset_minutes // 60:+03d}00" if fixed_offset_minutes % 60 == 0 else None
    if len(offsets) != 1:
        raise ValueError(f"Weather index has varying UTC offsets: {offsets}")
    if expected is not None and offsets[0] != expected:
        raise ValueError(f"Weather index offset {offsets[0]} does not match fixed offset {expected}.")


def load_weather(
    path: str | Path,
    weather_timestamp: str = "naive",
    fixed_offset_minutes: int = DEFAULT_FIXED_OFFSET_MINUTES,
) -> pd.DataFrame:
    """Load weather CSV and return fixed-offset timezone-aware data."""
    weather_path = Path(path)
    if not weather_path.exists():
        raise FileNotFoundError(f"Weather CSV not found: {weather_path}")

    weather = pd.read_csv(weather_path, sep=";")
    if list(weather.columns) != REQUIRED_WEATHER_COLUMNS:
        found = ", ".join(weather.columns)
        raise ValueError(
            "Weather data columns do not match expected header. "
            f"Found: {found}. Expected: {EXPECTED_HEADER}"
        )

    time_series = weather["time"].astype(str)
    timestamps = parse_weather_time(
        series=time_series,
        weather_timestamp=weather_timestamp,
        fixed_offset_minutes=fixed_offset_minutes,
    )

    weather = weather.set_index(timestamps)
    weather.index.name = "time"
    weather = weather.sort_index()

    _validate_time_regular(weather)
    _assert_fixed_offset_index(weather.index, fixed_offset_minutes)
    return weather
