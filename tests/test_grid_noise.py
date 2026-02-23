import json
from pathlib import Path

import pandas as pd

from pv_synth.generate import generate_systems


def _write_weather_csv(path: Path) -> None:
    weather = pd.DataFrame(
        {
            "time": [
                "2025-01-01 10:00:00",
                "2025-01-01 10:05:00",
                "2025-01-01 10:10:00",
                "2025-01-01 10:15:00",
            ],
            "ghi": [500, 510, 520, 530],
            "dhi": [100, 105, 110, 115],
            "t_luft": [20, 20, 21, 21],
            "v_wind": [2, 2, 3, 3],
        }
    )
    weather.to_csv(path, index=False, sep=";")


def _write_meta(path: Path) -> None:
    meta = {"lat": 52.5, "lon": 13.4, "tz": "Europe/Berlin"}
    path.write_text(json.dumps(meta), encoding="utf-8")


def _write_scenario(path: Path) -> None:
    path.write_text(
        """
single:
  tilt_deg: [10, 20]
  azimuth_deg: [90, 180]

east-west:
  center_deg: [0, 180]
  half_delta_deg: [90]
  weight: [0.2, 0.8]
""".strip(),
        encoding="utf-8",
    )


def test_grid_mode_is_deterministic_and_seed_independent(tmp_path: Path) -> None:
    weather = tmp_path / "w.csv"
    meta = tmp_path / "m.json"
    scenario = tmp_path / "s.yml"
    _write_weather_csv(weather)
    _write_meta(meta)
    _write_scenario(scenario)

    run_a = generate_systems(
        weather,
        meta,
        tmp_path / "a",
        n_systems=99,
        seed=1,
        generation_mode="grid",
        scenario_file=scenario,
    )
    run_b = generate_systems(
        weather,
        meta,
        tmp_path / "b",
        n_systems=3,
        seed=999,
        generation_mode="grid",
        scenario_file=scenario,
    )

    meta_a = pd.read_csv(run_a / "systems_metadata.csv")
    meta_b = pd.read_csv(run_b / "systems_metadata.csv")

    cols = ["system_type", "tilt_deg_true", "azimuth_deg_true", "azimuth_center_deg_true", "half_delta_deg_true", "weight_true", "azimuth_east_deg_true", "azimuth_west_deg_true"]
    pd.testing.assert_frame_equal(meta_a[cols], meta_b[cols], check_dtype=False)


def test_noise_is_deterministic_for_same_seed(tmp_path: Path) -> None:
    weather = tmp_path / "w.csv"
    meta = tmp_path / "m.json"
    _write_weather_csv(weather)
    _write_meta(meta)

    kwargs = dict(
        n_systems=2,
        seed=42,
        noise_model="gaussian",
        noise_sigma_rel=0.02,
    )
    run_a = generate_systems(weather, meta, tmp_path / "a", **kwargs)
    run_b = generate_systems(weather, meta, tmp_path / "b", **kwargs)

    a = pd.read_csv(run_a / "system_001.csv")
    b = pd.read_csv(run_b / "system_001.csv")
    pd.testing.assert_series_equal(a["ac_power_w"], b["ac_power_w"], check_names=False)


def test_ground_truth_columns_are_numeric_and_consistent(tmp_path: Path) -> None:
    weather = tmp_path / "w.csv"
    meta = tmp_path / "m.json"
    scenario = tmp_path / "s.yml"
    _write_weather_csv(weather)
    _write_meta(meta)
    _write_scenario(scenario)

    run_dir = generate_systems(
        weather,
        meta,
        tmp_path / "out",
        n_systems=1,
        generation_mode="grid",
        scenario_file=scenario,
    )

    metadata = pd.read_csv(run_dir / "systems_metadata.csv")
    expected = [
        "seed",
        "generation_mode",
        "noise_model",
        "noise_sigma_rel",
        "tilt_deg_true",
        "azimuth_deg_true",
        "azimuth_center_deg_true",
        "half_delta_deg_true",
        "azimuth_east_deg_true",
        "azimuth_west_deg_true",
        "weight_true",
    ]
    for column in expected:
        assert column in metadata.columns

    east_west = metadata[metadata["system_type"] == "east-west"].copy()
    assert not east_west.empty
    delta_e = (east_west["azimuth_center_deg_true"] - east_west["half_delta_deg_true"]) % 360
    delta_w = (east_west["azimuth_center_deg_true"] + east_west["half_delta_deg_true"]) % 360
    assert (east_west["azimuth_east_deg_true"].round(9) == delta_e.round(9)).all()
    assert (east_west["azimuth_west_deg_true"].round(9) == delta_w.round(9)).all()


def test_backward_compatibility_default_random_mode(tmp_path: Path) -> None:
    weather = tmp_path / "w.csv"
    meta = tmp_path / "m.json"
    _write_weather_csv(weather)
    _write_meta(meta)

    run_dir = generate_systems(weather, meta, tmp_path / "out", n_systems=3, seed=7)
    metadata = pd.read_csv(run_dir / "systems_metadata.csv")

    assert (metadata["generation_mode"] == "random").all()
    assert (metadata["noise_model"] == "none").all()
    assert metadata["noise_sigma_rel"].eq(0.02).all()
    # legacy columns still present
    assert "azimuth" in metadata.columns
