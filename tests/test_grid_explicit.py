from pathlib import Path

import pytest

from pv_synth.grid import load_scenario_grid


def test_explicit_single_no_cartesian_product(tmp_path: Path) -> None:
    scenario = tmp_path / "scenarios.yml"
    scenario.write_text(
        """
explicit:
  - system_type: single
    tilt_deg: 10
    azimuth_deg: 90
  - system_type: single
    tilt_deg: 20
    azimuth_deg: 180
""".strip(),
        encoding="utf-8",
    )

    systems = load_scenario_grid(scenario)
    assert len(systems) == 2
    assert systems[0].system_type == "single"
    assert systems[0].tilt == 10.0
    assert systems[1].tilt == 20.0


def test_explicit_ew_ground_truth_fields(tmp_path: Path) -> None:
    scenario = tmp_path / "scenarios.yml"
    scenario.write_text(
        """
explicit:
  - system_type: east-west
    tilt_deg: 25
    center_deg: 0
    half_delta_deg: 90
    weight: 0.5
""".strip(),
        encoding="utf-8",
    )

    systems = load_scenario_grid(scenario)
    assert len(systems) == 1
    cfg = systems[0]
    assert cfg.system_type == "east-west"
    assert cfg.roof_type == "explicit"
    assert cfg.ew_azimuth_mode == "explicit"
    assert cfg.tilt == 25.0
    assert cfg.azimuth_east == 270.0
    assert cfg.azimuth_west == 90.0
    assert cfg.azimuth_center_deg_true == 0.0
    assert cfg.half_delta_deg_true == 90.0
    assert cfg.weight_true == 0.5


def test_explicit_and_grid_sections_coexist(tmp_path: Path) -> None:
    scenario = tmp_path / "scenarios.yml"
    scenario.write_text(
        """
single:
  tilt_deg: [10]
  azimuth_deg: [180]

explicit:
  - system_type: single
    tilt_deg: 20
    azimuth_deg: 90
""".strip(),
        encoding="utf-8",
    )

    systems = load_scenario_grid(scenario)
    assert len(systems) == 2
    assert systems[0].system_id == 1
    assert systems[0].plane_type == "grid_single"
    assert systems[1].system_id == 2
    assert systems[1].plane_type == "explicit_single"


def test_explicit_missing_field_raises(tmp_path: Path) -> None:
    scenario = tmp_path / "scenarios.yml"
    scenario.write_text(
        """
explicit:
  - system_type: east-west
    tilt_deg: 20
    center_deg: 45
    half_delta_deg: 90
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required field 'weight'"):
        load_scenario_grid(scenario)


def test_explicit_s20_tilt_zero(tmp_path: Path) -> None:
    scenario = tmp_path / "scenarios.yml"
    scenario.write_text(
        """
explicit:
  - system_type: single
    tilt_deg: 0
    azimuth_deg: 180
""".strip(),
        encoding="utf-8",
    )

    systems = load_scenario_grid(scenario)
    assert len(systems) == 1
    assert systems[0].tilt == 0.0


def test_explicit_invalid_weight_raises(tmp_path: Path) -> None:
    scenario = tmp_path / "scenarios.yml"
    scenario.write_text(
        """
explicit:
  - system_type: east-west
    tilt_deg: 20
    center_deg: 0
    half_delta_deg: 90
    weight: 1.0
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"weight must be in \(0, 1\)"):
        load_scenario_grid(scenario)
