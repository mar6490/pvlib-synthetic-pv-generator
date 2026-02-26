from pathlib import Path

from pv_synth.grid import load_scenario_grid


def test_grid_east_west_uses_tilt_axis(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenarios.yml"
    scenario_path.write_text(
        """
east-west:
  tilt_deg: [10, 20]
  center_deg: [30]
  half_delta_deg: [90]
  weight: [0.5]
""".strip(),
        encoding="utf-8",
    )

    scenarios = load_scenario_grid(scenario_path)

    assert len(scenarios) == 2
    assert all(cfg.system_type == "east-west" for cfg in scenarios)
    assert sorted(cfg.tilt for cfg in scenarios) == [10.0, 20.0]
    assert all(cfg.azimuth_east == 300.0 for cfg in scenarios)
    assert all(cfg.azimuth_west == 120.0 for cfg in scenarios)
