"""Synthetic PV generation pipeline.

This module wires together input loading, scenario generation, PV modeling,
and CSV output writing.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import json

from pv_synth.io import load_site_meta, load_weather
from pv_synth.pv_models import simulate_system
from pv_synth.scenarios import generate_scenarios, scenarios_to_metadata


def generate_systems(
    weather_path: str | Path,
    meta_path: str | Path,
    out_dir: str | Path,
    n_systems: int,
    seed: int | None = None,
) -> None:
    """Generate synthetic PV systems and write outputs to disk."""
    # Load metadata (lat/lon/timezone) and the weather data.
    meta = load_site_meta(meta_path)
    weather = load_weather(weather_path, meta["tz"])
    # Create randomized system scenarios.
    scenarios = generate_scenarios(n_systems, seed=seed)

    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata_rows = []
    for config in scenarios:
        # Run pvlib modeling for each system configuration.
        system_df = simulate_system(weather, meta, config)
        system_id = f"{config.system_id:03d}"
        # Write per-system CSV with time, DC, and AC power.
        system_df.to_csv(output_path / f"system_{system_id}.csv", index=False)
        shading_profiles = config.shading_profiles
        if config.shading_model == "horizon_obstruction":
            horizon_deg = json.dumps({k: v.get("horizon_deg") for k, v in shading_profiles.items()})
            strength = json.dumps({k: v.get("strength") for k, v in shading_profiles.items()})
            softness_deg = json.dumps({k: v.get("softness_deg") for k, v in shading_profiles.items()})
            sectors = json.dumps({k: v.get("sectors") for k, v in shading_profiles.items()})
        else:
            horizon_deg = ""
            strength = ""
            softness_deg = ""
            sectors = ""

        metadata_rows.append({
            "system_id": config.system_id,
            "system_type": config.system_type,
            "kwp": config.kwp,
            "tilt": config.tilt,
            "azimuth": "90/270" if config.system_type == "east-west" else config.azimuth,
            "dc_ac_ratio": config.dc_ac_ratio,
            "losses": config.losses,
            "shading_model": config.shading_model,
            "shading_profiles": json.dumps(shading_profiles),
            "horizon_deg": horizon_deg,
            "strength": strength,
            "softness_deg": softness_deg,
            "sectors": sectors,
        })

    # Write a consolidated metadata file for all systems.
    metadata_df = pd.DataFrame(metadata_rows)
    metadata_df.to_csv(output_path / "systems_metadata.csv", index=False)
