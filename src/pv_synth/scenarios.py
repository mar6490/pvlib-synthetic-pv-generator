"""Scenario generation for synthetic photovoltaic (PV) systems.

This module creates random-but-realistic PV system configurations.

Design goal (plain language):
- We want many different PV systems so downstream analysis has variety.
- We keep ranges realistic for residential systems in DACH countries.
- We intentionally guarantee orientation diversity, so each run contains
  south, east, west, and east-west examples (as far as n_systems allows).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import List

import numpy as np

from pv_synth.pv_models import SystemConfig


# Orientation set we want to cover in generated data.
# Keeping this as a constant makes the intent explicit and easy to change.
BASE_TYPES = ["east-west", "south", "east", "west"]


def _sample_azimuth(system_type: str, rng: np.random.Generator) -> float | None:
    """Sample a realistic azimuth angle (compass direction) for one system.

    Why this helper exists:
    - Different roof orientations have different plausible azimuth ranges.
    - Encapsulating this logic keeps ``generate_scenarios`` simple.

    Notes for beginners:
    - Azimuth in this project follows pvlib convention:
      * 180° = south
      * 90° = east
      * 270° = west
    - East-west systems are modeled as two separate sub-arrays (fixed at
      90° and 270°), so they do not have one single azimuth value.
    """
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
    """Create ``n_systems`` randomized PV configurations.

    The generated systems do *not* include any synthetic shading model.
    All scenarios represent unshaded systems with standard aggregate losses.
    """
    rng = np.random.default_rng(seed)

    # Step 1: build an orientation list with guaranteed coverage.
    # Example: for n=3 -> [east-west, south, east]
    #          for n=8 -> first 4 fixed, then random picks from single-tilt types.
    types = BASE_TYPES[: min(n_systems, len(BASE_TYPES))]
    while len(types) < n_systems:
        types.append(rng.choice(BASE_TYPES[1:]))

    scenarios: List[SystemConfig] = []

    # Step 2: sample physical/electrical parameters for each system.
    for idx, system_type in enumerate(types, start=1):
        kwp = float(rng.uniform(3, 15))
        tilt = float(rng.uniform(10, 45))
        azimuth = _sample_azimuth(system_type, rng)
        dc_ac_ratio = float(rng.uniform(1.05, 1.25))
        losses = float(rng.uniform(0, 0.2))

        scenarios.append(
            SystemConfig(
                system_id=idx,
                system_type=system_type,
                kwp=kwp,
                tilt=tilt,
                azimuth=azimuth,
                dc_ac_ratio=dc_ac_ratio,
                losses=losses,
            )
        )

    return scenarios


def scenarios_to_metadata(scenarios: List[SystemConfig]) -> list[dict]:
    """Convert scenario objects into row dictionaries for CSV export."""
    metadata = []
    for config in scenarios:
        row = asdict(config)
        # East-west systems have two fixed azimuths instead of one numeric value.
        row["azimuth"] = "90/270" if config.system_type == "east-west" else config.azimuth
        metadata.append(row)
    return metadata
