"""I/O helpers for synthetic PV generation.

These functions focus on loading the input data (weather CSV and site metadata)
with strict validation so that downstream PV modeling can rely on clean inputs.
"""

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
EXAMPLE_TIMESTAMP = "2025-01-01 00:00:00+01:00"


def load_site_meta(path: str | Path) -> dict:
    """Load site metadata from JSON with validation."""
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


def parse_weather_time(
    series: pd.Series,
    weather_timestamp: str,
    time_mode: str,
    fixed_offset_minutes: int,
    meta_tz: str,
) -> pd.DatetimeIndex:
    """Parse weather timestamps into one timezone-aware DatetimeIndex.

    Modes:
    - weather_timestamp=with_offset: parse timestamps with explicit offsets.
    - weather_timestamp=naive: parse naive timestamps then localize.

    Time handling:
    - time_mode=dst: use metadata timezone (e.g. Europe/Berlin).
    - time_mode=fixed_offset: use fixed offset (e.g. UTC+01:00) year-round.
    """
    if weather_timestamp not in {"with_offset", "naive"}:
        raise ValueError("weather_timestamp must be 'with_offset' or 'naive'.")
    if time_mode not in {"dst", "fixed_offset"}:
        raise ValueError("time_mode must be 'dst' or 'fixed_offset'.")

    fixed_tz = timezone(timedelta(minutes=fixed_offset_minutes))

    if weather_timestamp == "with_offset":
        invalid_mask = ~series.str.match(TIME_PATTERN_WITH_OFFSET)
        if invalid_mask.any():
            raise ValueError(
                "Timestamps must include an explicit offset (±HH:MM) when "
                "--weather-timestamp=with_offset."
            )

        timestamps_utc = pd.to_datetime(series, errors="coerce", utc=True)
        if timestamps_utc.isna().all():
            raise ValueError("Could not parse any weather timestamps with offset.")

        index = pd.DatetimeIndex(timestamps_utc)
        if time_mode == "dst":
            return index.tz_convert(meta_tz)
        return index.tz_convert(fixed_tz)

    invalid_mask = ~series.str.match(TIME_PATTERN_NAIVE)
    if invalid_mask.any():
        raise ValueError(
            "Timestamps must be naive format YYYY-MM-DD HH:MM:SS when "
            "--weather-timestamp=naive."
        )

    naive = pd.to_datetime(series, errors="coerce")
    if naive.isna().all():
        raise ValueError("Could not parse any naive weather timestamps.")

    if time_mode == "dst":
        localized = naive.dt.tz_localize(meta_tz, ambiguous="raise", nonexistent="raise")
    else:
        localized = naive.dt.tz_localize(fixed_tz)

    return pd.DatetimeIndex(localized)


def _validate_time_regular(weather: pd.DataFrame) -> None:
    duplicate_mask = weather.index.duplicated(keep=False)
    if duplicate_mask.any():
        duplicate_count = int(duplicate_mask.sum())
        examples = ", ".join(weather.index[duplicate_mask].astype(str).unique()[:5])
        raise ValueError(
            "Weather data contains duplicate timestamps. "
            f"Duplicate count: {duplicate_count}. Examples: {examples}."
        )

    time_diffs = weather.index.to_series().diff().dropna()
    if time_diffs.empty:
        return

    reference_step = time_diffs.mode().iloc[0]
    irregular_mask = time_diffs != reference_step
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
            f"Expected consistent resolution of {reference_step}."
        )


def load_weather(
    path: str | Path,
    tz: str,
    weather_timestamp: str = "with_offset",
    time_mode: str = "dst",
    fixed_offset_minutes: int = 60,
) -> pd.DataFrame:
    """Load weather CSV, validate columns, and return timezone-aware data."""
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

    time_series = weather["time"].astype(str)
    timestamps = parse_weather_time(
        series=time_series,
        weather_timestamp=weather_timestamp,
        time_mode=time_mode,
        fixed_offset_minutes=fixed_offset_minutes,
        meta_tz=tz,
    )

    nat_mask = timestamps.isna()
    if nat_mask.any():
        invalid_count = int(nat_mask.sum())
        examples = _invalid_time_examples(time_series, nat_mask)
        raise ValueError(
            "Weather data contains unparsable timestamps. "
            f"Invalid count: {invalid_count}. Examples: {examples}. "
            f"Expected example with offset: {EXAMPLE_TIMESTAMP}."
        )

    weather = weather.set_index(timestamps)
    weather.index.name = "time"

    # Convert the index to the site timezone from metadata.
    # This keeps local-clock interpretation intuitive for users and tests.
    weather.index = weather.index.tz_convert(tz)
    weather = weather.sort_index()

    _validate_time_regular(weather)

    return weather
