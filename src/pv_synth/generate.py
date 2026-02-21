"""End-to-end synthetic PV generation pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import pandas as pd

from pv_synth.io import DEFAULT_FIXED_OFFSET_MINUTES, load_site_meta, load_weather
from pv_synth.pv_models import simulate_system
from pv_synth.scenarios import generate_scenarios

TIMESTAMP_DIR_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


def create_run_directory(base_out_dir: Path) -> Path:
    if TIMESTAMP_DIR_PATTERN.fullmatch(base_out_dir.name):
        run_dir = base_out_dir
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = base_out_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _fixed_tz_name(fixed_offset_minutes: int) -> str:
    sign = "+" if fixed_offset_minutes >= 0 else "-"
    minutes_abs = abs(fixed_offset_minutes)
    hours = minutes_abs // 60
    minutes = minutes_abs % 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def generate_systems(
    weather_path: str | Path,
    meta_path: str | Path,
    out_dir: str | Path,
    n_systems: int,
    seed: int | None = None,
    system_type: str = "mixed",
    mix_weights: dict[str, float] | None = None,
    n_by_type: dict[str, int] | None = None,
    ew_azimuth_mode: str = "fixed_cardinal",
    roof_type: str = "mixed",
    ew_azimuth_jitter_deg: float | None = None,
    ew_tilt_range_deg: tuple[float, float] | None = None,
    time_mode: str = "fixed_offset",
    fixed_offset_minutes: int = DEFAULT_FIXED_OFFSET_MINUTES,
    weather_timestamp: str = "naive",
) -> Path:
    """Generate synthetic PV systems and write outputs to disk."""
    meta = load_site_meta(meta_path)

    # Project standard: always use fixed offset for simulation/output axis.
    site_tz = timezone(timedelta(minutes=fixed_offset_minutes))
    tz_name = _fixed_tz_name(fixed_offset_minutes)
    effective_time_mode = "fixed_offset"

    weather = load_weather(
        weather_path,
        weather_timestamp=weather_timestamp,
        fixed_offset_minutes=fixed_offset_minutes,
    )

    offsets = weather.index.strftime("%z").unique().tolist()
    if len(offsets) != 1:
        raise ValueError(f"Weather index has varying offsets, expected fixed offset: {offsets}")

    scenarios = generate_scenarios(
        n_systems=n_systems,
        seed=seed,
        system_type=system_type,
        mix_weights=mix_weights,
        n_by_type=n_by_type,
        ew_azimuth_mode=ew_azimuth_mode,
        roof_type=roof_type,
        ew_azimuth_jitter_deg=ew_azimuth_jitter_deg,
        ew_tilt_range_deg=ew_tilt_range_deg,
    )

    output_path = create_run_directory(Path(out_dir))

    metadata_rows = []
    for config in scenarios:
        system_df = simulate_system(weather, meta, config).copy()
        system_df["time"] = pd.DatetimeIndex(system_df["time"]).tz_convert(site_tz)
        system_id = f"{config.system_id:03d}"
        system_df.to_csv(output_path / f"system_{system_id}.csv", index=False)

        metadata_rows.append(
            {
                "system_id": config.system_id,
                "system_type": config.system_type,
                "plane_type": config.plane_type,
                "roof_type": config.roof_type,
                "ew_azimuth_mode": config.ew_azimuth_mode,
                "time_mode": effective_time_mode,
                "fixed_offset_minutes": fixed_offset_minutes,
                "tz_name": tz_name,
                "meta_tz": meta.get("tz"),
                "lat": meta["lat"],
                "lon": meta["lon"],
                "kwp_total": config.kwp_total,
                "kwp": config.kwp_total,
                "kwp_east": config.kwp_east,
                "kwp_west": config.kwp_west,
                "tilt": config.tilt,
                "azimuth": (
                    f"{config.azimuth_east:.6f}/{config.azimuth_west:.6f}"
                    if config.system_type == "east-west"
                    else config.azimuth
                ),
                "azimuth_east": config.azimuth_east,
                "azimuth_west": config.azimuth_west,
                "dc_ac_ratio": config.dc_ac_ratio,
                "losses": config.losses,
            }
        )

    pd.DataFrame(metadata_rows).to_csv(output_path / "systems_metadata.csv", index=False)
    return output_path
