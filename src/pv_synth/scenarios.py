"""Scenario generation for synthetic photovoltaic (PV) systems."""

from __future__ import annotations

from dataclasses import asdict
from typing import List

import numpy as np

from pv_synth.pv_models import SystemConfig

ALLOWED_SYSTEM_TYPES = ("single", "east-west")
DEFAULT_MIX_WEIGHTS = {"single": 0.7, "east-west": 0.3}


def parse_mix_weights(raw: str | None) -> dict[str, float]:
    """Parse and validate mix weights from ``single=0.7,east-west=0.3`` style input."""
    if raw is None:
        return dict(DEFAULT_MIX_WEIGHTS)

    weights: dict[str, float] = {}
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError("Invalid --mix-weights format. Use key=value pairs.")
        key, value = token.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_SYSTEM_TYPES:
            raise ValueError("--mix-weights supports only keys: single, east-west.")
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(f"Invalid weight for '{key}': {value}") from exc
        if number < 0:
            raise ValueError("--mix-weights values must be non-negative.")
        weights[key] = number

    for key in ALLOWED_SYSTEM_TYPES:
        weights.setdefault(key, 0.0)

    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError("--mix-weights must sum to 1.0.")

    return weights


def parse_n_by_type(raw: str | None) -> dict[str, int] | None:
    """Parse and validate explicit counts from ``single=10,east-west=20`` style input."""
    if raw is None:
        return None

    counts: dict[str, int] = {}
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError("Invalid --n-by-type format. Use key=value pairs.")
        key, value = token.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_SYSTEM_TYPES:
            raise ValueError("--n-by-type supports only keys: single, east-west.")
        try:
            number = int(value)
        except ValueError as exc:
            raise ValueError(f"Invalid count for '{key}': {value}") from exc
        if number < 0:
            raise ValueError("--n-by-type counts must be >= 0.")
        counts[key] = number

    for key in ALLOWED_SYSTEM_TYPES:
        counts.setdefault(key, 0)

    if sum(counts.values()) <= 0:
        raise ValueError("--n-by-type must define at least one system.")

    return counts


def _sample_single_plane_type(rng: np.random.Generator) -> str:
    return str(rng.choice(["south", "east", "west"]))


def _sample_azimuth(plane_type: str, rng: np.random.Generator) -> float:
    if plane_type == "south":
        return float(np.clip(rng.normal(180, 15), 135, 225))
    if plane_type == "east":
        return float(np.clip(rng.normal(90, 10), 70, 110))
    if plane_type == "west":
        return float(np.clip(rng.normal(270, 10), 250, 290))
    raise ValueError(f"Unknown plane type: {plane_type}")


def _build_system_types(
    n_systems: int,
    rng: np.random.Generator,
    requested_type: str,
    mix_weights: dict[str, float],
    n_by_type: dict[str, int] | None,
) -> list[str]:
    if n_by_type is not None:
        types = ["single"] * n_by_type["single"] + ["east-west"] * n_by_type["east-west"]
        rng.shuffle(types)
        return types

    if requested_type == "single":
        return ["single"] * n_systems
    if requested_type == "east-west":
        return ["east-west"] * n_systems
    if requested_type == "mixed":
        return list(
            rng.choice(
                ["single", "east-west"],
                size=n_systems,
                p=[mix_weights["single"], mix_weights["east-west"]],
            )
        )
    raise ValueError("--system-type must be one of: single, east-west, mixed.")


def generate_scenarios(
    n_systems: int,
    seed: int | None = None,
    system_type: str = "mixed",
    mix_weights: dict[str, float] | None = None,
    n_by_type: dict[str, int] | None = None,
) -> List[SystemConfig]:
    """Create randomized PV configurations with controllable system-type composition."""
    rng = np.random.default_rng(seed)
    mix = dict(DEFAULT_MIX_WEIGHTS if mix_weights is None else mix_weights)
    types = _build_system_types(n_systems, rng, system_type, mix, n_by_type)

    scenarios: List[SystemConfig] = []
    for idx, scenario_type in enumerate(types, start=1):
        kwp_total = float(rng.uniform(3, 15))
        tilt = float(rng.uniform(10, 45))
        dc_ac_ratio = float(rng.uniform(1.05, 1.25))
        losses = float(rng.uniform(0, 0.2))

        if scenario_type == "east-west":
            kwp_east = kwp_total / 2
            kwp_west = kwp_total / 2
            scenarios.append(
                SystemConfig(
                    system_id=idx,
                    system_type="east-west",
                    plane_type=None,
                    kwp_total=kwp_total,
                    kwp_east=kwp_east,
                    kwp_west=kwp_west,
                    tilt=tilt,
                    azimuth=None,
                    dc_ac_ratio=dc_ac_ratio,
                    losses=losses,
                )
            )
        else:
            plane_type = _sample_single_plane_type(rng)
            scenarios.append(
                SystemConfig(
                    system_id=idx,
                    system_type="single",
                    plane_type=plane_type,
                    kwp_total=kwp_total,
                    kwp_east=None,
                    kwp_west=None,
                    tilt=tilt,
                    azimuth=_sample_azimuth(plane_type, rng),
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
        row["azimuth_east"] = 90.0 if config.system_type == "east-west" else None
        row["azimuth_west"] = 270.0 if config.system_type == "east-west" else None
        row["kwp"] = config.kwp_total
        metadata.append(row)
    return metadata
