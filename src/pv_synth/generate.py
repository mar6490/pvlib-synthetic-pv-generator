"""End-to-end synthetic PV generation pipeline.

Responsibilities:
- Read validated weather and site metadata.
- Create randomized PV system scenarios.
- Run physical simulation for each system.
- Persist per-system time series and one metadata overview file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pv_synth.io import load_site_meta, load_weather
from pv_synth.pv_models import simulate_system
from pv_synth.scenarios import generate_scenarios


def generate_systems(
    weather_path: str | Path,
    meta_path: str | Path,
    out_dir: str | Path,
    n_systems: int,
    seed: int | None = None,
) -> None:
    """Generate synthetic PV systems and write outputs to disk.

    This function is the orchestration layer and intentionally straightforward,
    so beginners can follow the workflow step by step.
    """
    meta = load_site_meta(meta_path)
    weather = load_weather(weather_path, meta["tz"])
    scenarios = generate_scenarios(n_systems, seed=seed)

    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata_rows = []
    for config in scenarios:
        system_df = simulate_system(weather, meta, config)
        system_id = f"{config.system_id:03d}"

        # One CSV file per synthetic system.
        system_df.to_csv(output_path / f"system_{system_id}.csv", index=False)

        # Metadata makes each generated file interpretable later.
        metadata_rows.append(
            {
                "system_id": config.system_id,
                "system_type": config.system_type,
                "kwp": config.kwp,
                "tilt": config.tilt,
                "azimuth": "90/270" if config.system_type == "east-west" else config.azimuth,
                "dc_ac_ratio": config.dc_ac_ratio,
                "losses": config.losses,
            }
        )

    metadata_df = pd.DataFrame(metadata_rows)
    metadata_df.to_csv(output_path / "systems_metadata.csv", index=False)
