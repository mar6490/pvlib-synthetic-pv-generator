"""Scenario-grid expansion from YAML for deterministic benchmark generation."""

from __future__ import annotations

from itertools import product
from pathlib import Path

from pv_synth.pv_models import SystemConfig


def _parse_inline_list(raw: str) -> list[float]:
    value = raw.strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise ValueError(f"Expected inline list syntax like [1, 2], got: {raw}")
    body = value[1:-1].strip()
    if not body:
        return []
    items = [part.strip() for part in body.split(",")]
    try:
        return [float(item) for item in items]
    except ValueError as exc:
        raise ValueError(f"List contains non-numeric value: {raw}") from exc


def _load_simple_yaml(path: Path) -> dict:
    """Load a constrained YAML subset used by scenario grid files."""
    root: dict[str, dict[str, list[float]]] = {}
    current_section: str | None = None

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not line.startswith(" "):
            if not stripped.endswith(":"):
                raise ValueError(f"Invalid section line at {lineno}: {raw}")
            current_section = stripped[:-1]
            root[current_section] = {}
            continue

        if current_section is None:
            raise ValueError(f"Key/value line before any section at {lineno}: {raw}")

        if line.startswith("  ") and not line.startswith("    "):
            if ":" not in stripped:
                raise ValueError(f"Invalid key/value line at {lineno}: {raw}")
            key, raw_value = stripped.split(":", 1)
            root[current_section][key.strip()] = _parse_inline_list(raw_value.strip())
        else:
            raise ValueError(f"Unsupported indentation at {lineno}: {raw}")

    return root


def _validate_list(section: dict, key: str, system_name: str) -> list[float]:
    if key not in section:
        raise ValueError(f"Grid section '{system_name}' is missing required key '{key}'.")
    value = section[key]
    if not isinstance(value, list) or len(value) == 0:
        raise ValueError(f"Grid key '{system_name}.{key}' must be a non-empty list.")
    return [float(item) for item in value]


def load_scenario_grid(path: str | Path) -> list[SystemConfig]:
    """Load YAML scenario axes and expand into deterministic SystemConfig combinations."""
    scenario_path = Path(path)
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    payload = _load_simple_yaml(scenario_path)
    if not isinstance(payload, dict):
        raise ValueError("Scenario file must define a mapping with optional 'single'/'east-west' sections.")

    scenarios: list[SystemConfig] = []
    next_id = 1

    single = payload.get("single")
    if single is not None:
        if not isinstance(single, dict):
            raise ValueError("Grid section 'single' must be a mapping.")
        tilts = _validate_list(single, "tilt_deg", "single")
        azimuths = _validate_list(single, "azimuth_deg", "single")
        for tilt_deg, azimuth_deg in product(tilts, azimuths):
            scenarios.append(
                SystemConfig(
                    system_id=next_id,
                    system_type="single",
                    plane_type="grid_single",
                    roof_type=None,
                    ew_azimuth_mode=None,
                    kwp_total=10.0,
                    kwp_east=None,
                    kwp_west=None,
                    tilt=float(tilt_deg),
                    azimuth=float(azimuth_deg % 360.0),
                    azimuth_east=None,
                    azimuth_west=None,
                    dc_ac_ratio=1.15,
                    losses=0.08,
                    azimuth_center_deg_true=None,
                    half_delta_deg_true=None,
                    weight_true=None,
                )
            )
            next_id += 1

    east_west = payload.get("east-west")
    if east_west is not None:
        if not isinstance(east_west, dict):
            raise ValueError("Grid section 'east-west' must be a mapping.")
        centers = _validate_list(east_west, "center_deg", "east-west")
        half_deltas = _validate_list(east_west, "half_delta_deg", "east-west")
        weights = _validate_list(east_west, "weight", "east-west")

        for center_deg, half_delta_deg, weight in product(centers, half_deltas, weights):
            azimuth_east = (center_deg - half_delta_deg) % 360.0
            azimuth_west = (center_deg + half_delta_deg) % 360.0
            kwp_total = 10.0
            kwp_east = kwp_total * weight
            kwp_west = kwp_total * (1.0 - weight)
            scenarios.append(
                SystemConfig(
                    system_id=next_id,
                    system_type="east-west",
                    plane_type=None,
                    roof_type="grid",
                    ew_azimuth_mode="grid",
                    kwp_total=kwp_total,
                    kwp_east=kwp_east,
                    kwp_west=kwp_west,
                    tilt=25.0,
                    azimuth=None,
                    azimuth_east=float(azimuth_east),
                    azimuth_west=float(azimuth_west),
                    dc_ac_ratio=1.15,
                    losses=0.08,
                    azimuth_center_deg_true=float(center_deg % 360.0),
                    half_delta_deg_true=float(half_delta_deg),
                    weight_true=float(weight),
                )
            )
            next_id += 1

    if not scenarios:
        raise ValueError("Scenario grid file produced no systems; define 'single' and/or 'east-west' axes.")

    return scenarios
