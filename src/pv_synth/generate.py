"""End-to-end synthetic PV generation pipeline."""

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
    system_type: str = "mixed",
    mix_weights: dict[str, float] | None = None,
    n_by_type: dict[str, int] | None = None,
    ew_azimuth_mode: str = "fixed_cardinal",
    roof_type: str = "mixed",
    ew_azimuth_jitter_deg: float | None = None,
    ew_tilt_range_deg: tuple[float, float] | None = None,
) -> None:
    """Generate synthetic PV systems and write outputs to disk."""
    meta = load_site_meta(meta_path)
    weather = load_weather(weather_path, meta["tz"])
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

    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata_rows = []
    for config in scenarios:
        system_df = simulate_system(weather, meta, config)
        system_id = f"{config.system_id:03d}"
        system_df.to_csv(output_path / f"system_{system_id}.csv", index=False)

        metadata_rows.append(
            {
                "system_id": config.system_id,
                "system_type": config.system_type,
                "plane_type": config.plane_type,
                "roof_type": config.roof_type,
                "ew_azimuth_mode": config.ew_azimuth_mode,
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

    metadata_df = pd.DataFrame(metadata_rows)
    metadata_df.to_csv(output_path / "systems_metadata.csv", index=False)
