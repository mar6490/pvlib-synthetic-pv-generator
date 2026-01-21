"""Scenario generation for synthetic systems.

The scenarios represent different residential PV configurations typical for
Germany/Austria/Switzerland (DACH) with variability in size, tilt, azimuth,
losses, and DC/AC ratio.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import List

import numpy as np

from pv_synth.pv_models import SystemConfig


def _sector_for_orientation(system_type: str) -> list[tuple[float, float]]:
    if system_type == "south":
        return [(140.0, 220.0)]
    if system_type == "east":
        return [(60.0, 150.0)]
    if system_type == "west":
        return [(210.0, 300.0)]
    return [(140.0, 220.0)]


def _sample_azimuth(system_type: str, rng: np.random.Generator) -> float | None:
    """Sample an azimuth appropriate for each system orientation."""
    if system_type == "south":
        return float(np.clip(rng.normal(180, 15), 135, 225))
    if system_type == "east":
        return float(np.clip(rng.normal(90, 10), 70, 110))
    if system_type == "west":
        return float(np.clip(rng.normal(270, 10), 250, 290))
    if system_type == "east-west":
        return None
    raise ValueError(f"Unknown system type: {system_type}")


def generate_scenarios(n_systems: int, seed: int | None = None) -> List[SystemConfig]:
    """Generate randomized system scenarios with required orientation coverage."""
    rng = np.random.default_rng(seed)
    # Ensure at least one east-west system, then fill the rest with single-tilt types.
    base_types = ["east-west", "south", "east", "west"]
    types = base_types[: min(n_systems, len(base_types))]
    while len(types) < n_systems:
        types.append(rng.choice(base_types[1:]))

    scenarios: List[SystemConfig] = []
    for idx, system_type in enumerate(types, start=1):
        # Draw values from realistic residential ranges.
        kwp = float(rng.uniform(3, 15))
        tilt = float(rng.uniform(10, 45))
        azimuth = _sample_azimuth(system_type, rng)
        dc_ac_ratio = float(rng.uniform(1.05, 1.25))
        losses = float(rng.uniform(0, 0.2))
        shading_model = rng.choice(["none", "horizon_obstruction"])
        horizon_deg = float(rng.uniform(5, 25))
        strength = float(rng.uniform(0.2, 0.8))
        softness_deg = float(rng.uniform(2, 8))
        shading_profiles: dict[str, dict] = {}

        if shading_model == "horizon_obstruction":
            if system_type == "east-west":
                variant = rng.choice(["east_obstruction", "west_obstruction", "south_obstruction"])
                if variant == "east_obstruction":
                    shading_profiles = {
                        "east": {
                            "sectors": [(60.0, 150.0)],
                            "horizon_deg": horizon_deg,
                            "strength": strength,
                            "softness_deg": softness_deg,
                        },
                        "west": {
                            "sectors": [(210.0, 300.0)],
                            "horizon_deg": horizon_deg,
                            "strength": 0.05,
                            "softness_deg": softness_deg,
                        },
                    }
                elif variant == "west_obstruction":
                    shading_profiles = {
                        "east": {
                            "sectors": [(60.0, 150.0)],
                            "horizon_deg": horizon_deg,
                            "strength": 0.05,
                            "softness_deg": softness_deg,
                        },
                        "west": {
                            "sectors": [(210.0, 300.0)],
                            "horizon_deg": horizon_deg,
                            "strength": strength,
                            "softness_deg": softness_deg,
                        },
                    }
                else:
                    shading_profiles = {
                        "east": {
                            "sectors": [(140.0, 220.0)],
                            "horizon_deg": horizon_deg,
                            "strength": strength,
                            "softness_deg": softness_deg,
                        },
                        "west": {
                            "sectors": [(140.0, 220.0)],
                            "horizon_deg": horizon_deg,
                            "strength": strength,
                            "softness_deg": softness_deg,
                        },
                    }
            else:
                shading_profiles = {
                    "single": {
                        "sectors": _sector_for_orientation(system_type),
                        "horizon_deg": horizon_deg,
                        "strength": strength,
                        "softness_deg": softness_deg,
                    }
                }
        scenarios.append(
            SystemConfig(
                system_id=idx,
                system_type=system_type,
                kwp=kwp,
                tilt=tilt,
                azimuth=azimuth,
                dc_ac_ratio=dc_ac_ratio,
                losses=losses,
                shading_model=shading_model,
                shading_profiles=shading_profiles,
            )
        )

    return scenarios


def scenarios_to_metadata(scenarios: List[SystemConfig]) -> list[dict]:
    """Convert scenario objects to a list of metadata dicts for CSV output."""
    metadata = []
    for config in scenarios:
        row = asdict(config)
        row["azimuth"] = "90/270" if config.system_type == "east-west" else config.azimuth
        metadata.append(row)
    return metadata
