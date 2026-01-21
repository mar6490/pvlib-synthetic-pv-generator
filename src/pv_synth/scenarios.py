"""Scenario generation for synthetic systems."""

from __future__ import annotations

from dataclasses import asdict
from typing import List

import numpy as np

from pv_synth.pv_models import SystemConfig


def _sample_azimuth(system_type: str, rng: np.random.Generator) -> float | None:
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
    rng = np.random.default_rng(seed)
    base_types = ["east-west", "south", "east", "west"]
    types = base_types[: min(n_systems, len(base_types))]
    while len(types) < n_systems:
        types.append(rng.choice(base_types[1:]))

    scenarios: List[SystemConfig] = []
    for idx, system_type in enumerate(types, start=1):
        kwp = float(rng.uniform(3, 15))
        tilt = float(rng.uniform(10, 45))
        azimuth = _sample_azimuth(system_type, rng)
        dc_ac_ratio = float(rng.uniform(1.05, 1.25))
        losses = float(rng.uniform(0, 0.2))
        shading_type = rng.choice(["none", "morning", "evening", "midday"])
        scenarios.append(
            SystemConfig(
                system_id=idx,
                system_type=system_type,
                kwp=kwp,
                tilt=tilt,
                azimuth=azimuth,
                dc_ac_ratio=dc_ac_ratio,
                losses=losses,
                shading_type=shading_type,
            )
        )

    return scenarios


def scenarios_to_metadata(scenarios: List[SystemConfig]) -> list[dict]:
    metadata = []
    for config in scenarios:
        row = asdict(config)
        row["azimuth"] = "90/270" if config.system_type == "east-west" else config.azimuth
        metadata.append(row)
    return metadata
