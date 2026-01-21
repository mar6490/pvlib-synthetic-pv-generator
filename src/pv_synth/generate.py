"""Synthetic PV generation pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

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
    meta = load_site_meta(meta_path)
    weather = load_weather(weather_path, meta["tz"])
    scenarios = generate_scenarios(n_systems, seed=seed)

    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata_rows = []
    for config in scenarios:
        system_df = simulate_system(weather, meta, config)
        system_id = f"{config.system_id:03d}"
        system_df.to_csv(output_path / f"system_{system_id}.csv", index=False)
        metadata_rows.append({
            "system_id": config.system_id,
            "system_type": config.system_type,
            "kwp": config.kwp,
            "tilt": config.tilt,
            "azimuth": "90/270" if config.system_type == "east-west" else config.azimuth,
            "dc_ac_ratio": config.dc_ac_ratio,
            "losses": config.losses,
            "shading_type": config.shading_type,
        })

    metadata_df = pd.DataFrame(metadata_rows)
    metadata_df.to_csv(output_path / "systems_metadata.csv", index=False)
