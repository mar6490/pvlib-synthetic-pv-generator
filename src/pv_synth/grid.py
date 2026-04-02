"""Scenario-grid expansion from YAML for deterministic benchmark generation."""

from __future__ import annotations

from itertools import product
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback for offline test envs
    yaml = None

from pv_synth.pv_models import SystemConfig


def _validate_list(section: dict, key: str, system_name: str) -> list[float]:
    if key not in section:
        raise ValueError(f"Grid section '{system_name}' is missing required key '{key}'.")
    value = section[key]
    if not isinstance(value, list) or len(value) == 0:
        raise ValueError(f"Grid key '{system_name}.{key}' must be a non-empty list.")
    return [float(item) for item in value]


def _require_numeric(entry: dict, key: str, system_name: str) -> float:
    if key not in entry:
        raise ValueError(f"Explicit entry for '{system_name}' missing required field '{key}'.")
    try:
        return float(entry[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Explicit field '{key}' must be numeric.") from exc


def _parse_scalar(value: str) -> float | str:
    value = value.strip()
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        value = value[1:-1]
    try:
        return float(value)
    except ValueError:
        return value


def _parse_inline_list(value: str) -> list[float]:
    stripped = value.strip()
    if not (stripped.startswith("[") and stripped.endswith("]")):
        raise ValueError(f"Expected inline list format [..], got: {value}")
    body = stripped[1:-1].strip()
    if not body:
        return []
    parts = [part.strip() for part in body.split(",")]
    return [float(_parse_scalar(part)) for part in parts]


def _safe_load_yaml(path: Path) -> dict:
    if yaml is not None:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        return data

    # Minimal fallback parser for the subset used by scenario files.
    root: dict[str, object] = {}
    current_section: str | None = None
    in_explicit = False
    current_item: dict[str, object] | None = None

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not line.startswith(" "):
            if not stripped.endswith(":"):
                raise ValueError(f"Invalid section header at line {lineno}: {raw}")
            current_section = stripped[:-1]
            in_explicit = current_section == "explicit"
            root[current_section] = [] if in_explicit else {}
            current_item = None
            continue

        if current_section is None:
            raise ValueError(f"Unexpected indented content at line {lineno}: {raw}")

        if in_explicit:
            if line.startswith("  - "):
                payload = stripped[2:].strip()
                item: dict[str, object] = {}
                if payload:
                    if ":" not in payload:
                        raise ValueError(f"Invalid explicit entry at line {lineno}: {raw}")
                    key, value = payload.split(":", 1)
                    item[key.strip()] = _parse_scalar(value)
                root[current_section].append(item)  # type: ignore[index]
                current_item = item
            elif line.startswith("    "):
                if current_item is None:
                    raise ValueError(f"Explicit field without list item at line {lineno}: {raw}")
                if ":" not in stripped:
                    raise ValueError(f"Invalid explicit field at line {lineno}: {raw}")
                key, value = stripped.split(":", 1)
                current_item[key.strip()] = _parse_scalar(value)
            else:
                raise ValueError(f"Unsupported explicit indentation at line {lineno}: {raw}")
        else:
            if not line.startswith("  ") or line.startswith("    "):
                raise ValueError(f"Unsupported grid indentation at line {lineno}: {raw}")
            if ":" not in stripped:
                raise ValueError(f"Invalid grid key/value at line {lineno}: {raw}")
            key, value = stripped.split(":", 1)
            section = root[current_section]
            if not isinstance(section, dict):
                raise ValueError(f"Section '{current_section}' must be mapping.")
            section[key.strip()] = _parse_inline_list(value)

    return root


def load_scenario_grid(path: str | Path) -> list[SystemConfig]:
    """Load YAML scenario axes and expand into deterministic SystemConfig combinations."""
    scenario_path = Path(path)
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    payload = _safe_load_yaml(scenario_path)

    if not isinstance(payload, dict):
        raise ValueError("Scenario file root must be a mapping.")

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
        tilts = _validate_list(east_west, "tilt_deg", "east-west")
        centers = _validate_list(east_west, "center_deg", "east-west")
        half_deltas = _validate_list(east_west, "half_delta_deg", "east-west")
        weights = _validate_list(east_west, "weight", "east-west")

        for tilt_deg, center_deg, half_delta_deg, weight in product(tilts, centers, half_deltas, weights):
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
                    tilt=float(tilt_deg),
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

    explicit = payload.get("explicit")
    if explicit is not None:
        if not isinstance(explicit, list):
            raise ValueError("Section 'explicit' must be a list of mappings.")

        for row in explicit:
            if not isinstance(row, dict):
                raise ValueError("Each explicit entry must be a mapping.")
            system_type = row.get("system_type")
            if system_type == "single":
                tilt_deg = _require_numeric(row, "tilt_deg", "single")
                azimuth_deg = _require_numeric(row, "azimuth_deg", "single")
                if not (0.0 <= tilt_deg <= 90.0):
                    raise ValueError("Explicit single tilt_deg must be in [0, 90].")

                scenarios.append(
                    SystemConfig(
                        system_id=next_id,
                        system_type="single",
                        plane_type="explicit_single",
                        roof_type=None,
                        ew_azimuth_mode=None,
                        kwp_total=10.0,
                        kwp_east=None,
                        kwp_west=None,
                        tilt=float(tilt_deg),
                        azimuth=float(azimuth_deg) % 360.0,
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
                continue

            if system_type == "east-west":
                tilt_deg = _require_numeric(row, "tilt_deg", "east-west")
                center_deg = _require_numeric(row, "center_deg", "east-west")
                half_delta_deg = _require_numeric(row, "half_delta_deg", "east-west")
                weight = _require_numeric(row, "weight", "east-west")

                if not (0.0 <= tilt_deg <= 90.0):
                    raise ValueError("Explicit east-west tilt_deg must be in [0, 90].")
                if not (0.0 < half_delta_deg <= 180.0):
                    raise ValueError("Explicit east-west half_delta_deg must be in (0, 180].")
                if not (0.0 < weight < 1.0):
                    raise ValueError("Explicit east-west weight must be in (0, 1).")

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
                        roof_type="explicit",
                        ew_azimuth_mode="explicit",
                        kwp_total=kwp_total,
                        kwp_east=kwp_east,
                        kwp_west=kwp_west,
                        tilt=float(tilt_deg),
                        azimuth=None,
                        azimuth_east=float(azimuth_east),
                        azimuth_west=float(azimuth_west),
                        dc_ac_ratio=1.15,
                        losses=0.08,
                        azimuth_center_deg_true=float(center_deg) % 360.0,
                        half_delta_deg_true=float(half_delta_deg),
                        weight_true=float(weight),
                    )
                )
                next_id += 1
                continue

            raise ValueError("Explicit entry has unknown system_type. Use 'single' or 'east-west'.")

    if not scenarios:
        raise ValueError("Scenario grid file produced no systems; define 'single', 'east-west', and/or 'explicit'.")

    return scenarios
