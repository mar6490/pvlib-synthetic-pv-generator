"""Scenario generation for synthetic photovoltaic (PV) systems."""

from __future__ import annotations

from typing import List

import numpy as np

from pv_synth.pv_models import SystemConfig

ALLOWED_SYSTEM_TYPES = ("single", "east-west")
DEFAULT_MIX_WEIGHTS = {"single": 0.7, "east-west": 0.3}
ALLOWED_EW_AZIMUTH_MODES = ("fixed_cardinal", "jittered_180")
ALLOWED_ROOF_TYPES = ("flat", "pitched", "mixed")


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


def parse_tilt_range(raw: str | None) -> tuple[float, float] | None:
    """Parse optional east-west tilt range override from ``a,b`` format."""
    if raw is None:
        return None

    parts = [item.strip() for item in raw.split(",")]
    if len(parts) != 2:
        raise ValueError("Invalid --ew-tilt-range-deg format. Use 'min,max'.")

    try:
        low = float(parts[0])
        high = float(parts[1])
    except ValueError as exc:
        raise ValueError("Invalid --ew-tilt-range-deg values. Use numeric min,max.") from exc

    if low < 0 or high < 0:
        raise ValueError("--ew-tilt-range-deg values must be non-negative.")
    if low >= high:
        raise ValueError("--ew-tilt-range-deg requires min < max.")

    return low, high


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


def _sample_ew_roof_type(selected_roof_type: str, rng: np.random.Generator) -> str:
    if selected_roof_type == "mixed":
        return str(rng.choice(["flat", "pitched"], p=[0.5, 0.5]))
    return selected_roof_type


def _sample_ew_tilt(
    roof_type: str,
    rng: np.random.Generator,
    ew_tilt_range_deg: tuple[float, float] | None,
) -> float:
    if ew_tilt_range_deg is not None:
        return float(rng.uniform(ew_tilt_range_deg[0], ew_tilt_range_deg[1]))
    if roof_type == "flat":
        return float(rng.uniform(5, 20))
    return float(rng.uniform(20, 55))


def _sample_ew_azimuths(
    roof_type: str,
    mode: str,
    rng: np.random.Generator,
    ew_azimuth_jitter_deg: float | None,
) -> tuple[float, float]:
    if mode == "fixed_cardinal":
        azimuth_east = 90.0
    else:
        if ew_azimuth_jitter_deg is not None:
            jitter = ew_azimuth_jitter_deg
        elif roof_type == "flat":
            jitter = 15.0
        else:
            jitter = 30.0
        delta = float(rng.uniform(-jitter, jitter))
        azimuth_east = 90.0 + delta

    azimuth_west = (azimuth_east + 180.0) % 360.0
    return azimuth_east, azimuth_west


def generate_scenarios(
    n_systems: int,
    seed: int | None = None,
    system_type: str = "mixed",
    mix_weights: dict[str, float] | None = None,
    n_by_type: dict[str, int] | None = None,
    ew_azimuth_mode: str = "fixed_cardinal",
    roof_type: str = "mixed",
    ew_azimuth_jitter_deg: float | None = None,
    ew_tilt_range_deg: tuple[float, float] | None = None,
) -> List[SystemConfig]:
    """Create randomized PV configurations with controllable system-type composition."""
    if ew_azimuth_mode not in ALLOWED_EW_AZIMUTH_MODES:
        raise ValueError("--ew-azimuth-mode must be one of: fixed_cardinal, jittered_180.")
    if roof_type not in ALLOWED_ROOF_TYPES:
        raise ValueError("--roof-type must be one of: flat, pitched, mixed.")
    if ew_azimuth_jitter_deg is not None and ew_azimuth_jitter_deg < 0:
        raise ValueError("--ew-azimuth-jitter-deg must be >= 0.")

    rng = np.random.default_rng(seed)
    mix = dict(DEFAULT_MIX_WEIGHTS if mix_weights is None else mix_weights)
    types = _build_system_types(n_systems, rng, system_type, mix, n_by_type)

    scenarios: List[SystemConfig] = []
    for idx, scenario_type in enumerate(types, start=1):
        kwp_total = float(rng.uniform(3, 15))
        dc_ac_ratio = float(rng.uniform(1.05, 1.25))
        losses = float(rng.uniform(0, 0.2))

        if scenario_type == "east-west":
            sampled_roof_type = _sample_ew_roof_type(roof_type, rng)
            sampled_tilt = _sample_ew_tilt(sampled_roof_type, rng, ew_tilt_range_deg)
            azimuth_east, azimuth_west = _sample_ew_azimuths(
                sampled_roof_type,
                ew_azimuth_mode,
                rng,
                ew_azimuth_jitter_deg,
            )
            kwp_east = kwp_total / 2
            kwp_west = kwp_total / 2
            center = (azimuth_east + 90.0) % 360.0
            scenarios.append(
                SystemConfig(
                    system_id=idx,
                    system_type="east-west",
                    plane_type=None,
                    roof_type=sampled_roof_type,
                    ew_azimuth_mode=ew_azimuth_mode,
                    kwp_total=kwp_total,
                    kwp_east=kwp_east,
                    kwp_west=kwp_west,
                    tilt=sampled_tilt,
                    azimuth=None,
                    azimuth_east=azimuth_east,
                    azimuth_west=azimuth_west,
                    dc_ac_ratio=dc_ac_ratio,
                    losses=losses,
                    azimuth_center_deg_true=center,
                    half_delta_deg_true=90.0,
                    weight_true=0.5,
                )
            )
        else:
            plane_type = _sample_single_plane_type(rng)
            scenarios.append(
                SystemConfig(
                    system_id=idx,
                    system_type="single",
                    plane_type=plane_type,
                    roof_type=None,
                    ew_azimuth_mode=None,
                    kwp_total=kwp_total,
                    kwp_east=None,
                    kwp_west=None,
                    tilt=float(rng.uniform(10, 45)),
                    azimuth=_sample_azimuth(plane_type, rng),
                    azimuth_east=None,
                    azimuth_west=None,
                    dc_ac_ratio=dc_ac_ratio,
                    losses=losses,
                    azimuth_center_deg_true=None,
                    half_delta_deg_true=None,
                    weight_true=None,
                )
            )

    return scenarios
