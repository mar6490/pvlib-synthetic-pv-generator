"""End-to-end synthetic PV generation pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import pandas as pd

from pv_synth.grid import load_scenario_grid
from pv_synth.io import DEFAULT_FIXED_OFFSET_MINUTES, load_site_meta, load_weather
from pv_synth.noise import apply_ac_noise
from pv_synth.pv_models import SystemConfig, simulate_system
from pv_synth.scenarios import generate_scenarios


OUTPUT_TIMESTAMP_CHOICES = {"with_offset", "naive"}

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


def _build_scenarios(
    generation_mode: str,
    scenario_file: str | Path | None,
    n_systems: int,
    seed: int | None,
    system_type: str,
    mix_weights: dict[str, float] | None,
    n_by_type: dict[str, int] | None,
    ew_azimuth_mode: str,
    roof_type: str,
    ew_azimuth_jitter_deg: float | None,
    ew_tilt_range_deg: tuple[float, float] | None,
) -> list[SystemConfig]:
    if generation_mode == "grid":
        if scenario_file is None:
            raise ValueError("--scenario-file is required when --generation-mode=grid.")
        return load_scenario_grid(scenario_file)

    return generate_scenarios(
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




def _format_output_time(
    times: pd.Series | pd.DatetimeIndex,
    site_tz: timezone,
    output_timestamp: str,
) -> pd.DatetimeIndex:
    if output_timestamp not in OUTPUT_TIMESTAMP_CHOICES:
        raise ValueError("output_timestamp must be 'with_offset' or 'naive'.")

    localized = pd.DatetimeIndex(times).tz_convert(site_tz)
    if output_timestamp == "naive":
        return localized.tz_localize(None)
    return localized

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
    generation_mode: str = "random",
    scenario_file: str | Path | None = None,
    noise_model: str = "none",
    noise_sigma_rel: float = 0.02,
    output_timestamp: str = "with_offset",
) -> Path:
    """Generate synthetic PV systems and write outputs to disk."""
    meta = load_site_meta(meta_path)

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

    scenarios = _build_scenarios(
        generation_mode=generation_mode,
        scenario_file=scenario_file,
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
        system_df["ac_power_w"] = apply_ac_noise(
            system_df["ac_power_w"],
            noise_model=noise_model,
            noise_sigma_rel=noise_sigma_rel,
            seed=(seed or 0) + config.system_id,
        )
        system_df["time"] = _format_output_time(system_df["time"], site_tz, output_timestamp)

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
                "seed": seed,
                "generation_mode": generation_mode,
                "noise_model": noise_model,
                "noise_sigma_rel": noise_sigma_rel,
                "output_timestamp": output_timestamp,
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
                "tilt_deg_true": float(config.tilt) if config.system_type == "single" else None,
                "azimuth_deg_true": float(config.azimuth) if config.system_type == "single" and config.azimuth is not None else None,
                "azimuth_center_deg_true": config.azimuth_center_deg_true,
                "half_delta_deg_true": config.half_delta_deg_true,
                "azimuth_east_deg_true": float(config.azimuth_east) if config.azimuth_east is not None else None,
                "azimuth_west_deg_true": float(config.azimuth_west) if config.azimuth_west is not None else None,
                "weight_true": config.weight_true,
            }
        )

    pd.DataFrame(metadata_rows).to_csv(output_path / "systems_metadata.csv", index=False)
    return output_path
