import json
from pathlib import Path

import pandas as pd

from pv_synth.generate import generate_systems
from pv_synth.io import load_weather


def _write_weather_csv(path: Path) -> None:
    weather = pd.DataFrame(
        {
            "time": [
                "2025-01-01 10:00:00+01:00",
                "2025-01-01 10:15:00+01:00",
                "2025-01-01 10:30:00+01:00",
                "2025-01-01 10:45:00+01:00",
            ],
            "ghi": [500, 520, 530, 540],
            "dhi": [100, 110, 120, 130],
            "t_luft": [20, 20, 21, 21],
            "v_wind": [2, 2, 3, 3],
        }
    )
    weather.to_csv(path, index=False, sep=";")


def _write_meta(path: Path) -> None:
    meta = {"lat": 52.5, "lon": 13.4, "tz": "Europe/Berlin"}
    path.write_text(json.dumps(meta), encoding="utf-8")


def _prepare_inputs(tmp_path: Path) -> tuple[Path, Path]:
    weather_path = tmp_path / "wetter-htw-2025-utc.csv"
    meta_path = tmp_path / "meta.json"
    _write_weather_csv(weather_path)
    _write_meta(meta_path)
    return weather_path, meta_path


def test_load_weather_localizes_timezone(tmp_path: Path) -> None:
    weather_path, _ = _prepare_inputs(tmp_path)
    weather = load_weather(weather_path, "Europe/Berlin")
    assert str(weather.index.tz) == "Europe/Berlin"


def test_generation_outputs_match_input_length(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs"

    generate_systems(weather_path, meta_path, out_dir, n_systems=3, seed=1)

    first_system = out_dir / "system_001.csv"
    assert first_system.exists()
    system_df = pd.read_csv(first_system)
    assert len(system_df) == 4

    metadata_df = pd.read_csv(out_dir / "systems_metadata.csv")
    assert len(metadata_df) == 3


def test_system_type_east_west_only(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_ew"

    generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=5,
        seed=42,
        system_type="east-west",
    )

    metadata_df = pd.read_csv(out_dir / "systems_metadata.csv")

    assert (metadata_df["system_type"] == "east-west").all()
    assert ((metadata_df["kwp_east"] - metadata_df["kwp_total"] / 2).abs() < 1e-9).all()
    assert ((metadata_df["kwp_west"] - metadata_df["kwp_total"] / 2).abs() < 1e-9).all()
    assert (metadata_df["azimuth_east"] == 90.0).all()
    assert (metadata_df["azimuth_west"] == 270.0).all()


def test_system_type_single_only(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_single"

    generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=5,
        seed=42,
        system_type="single",
    )

    metadata_df = pd.read_csv(out_dir / "systems_metadata.csv")

    assert (metadata_df["system_type"] == "single").all()
    assert metadata_df["kwp_east"].isna().all()
    assert metadata_df["kwp_west"].isna().all()
    assert metadata_df["azimuth_east"].isna().all()
    assert metadata_df["azimuth_west"].isna().all()
    assert pd.to_numeric(metadata_df["azimuth"], errors="coerce").notna().all()


def test_mixed_with_all_east_west_weight(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_mix"

    generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=6,
        seed=7,
        system_type="mixed",
        mix_weights={"single": 0.0, "east-west": 1.0},
    )

    metadata_df = pd.read_csv(out_dir / "systems_metadata.csv")
    assert (metadata_df["system_type"] == "east-west").all()


def test_reproducibility_same_seed_same_metadata(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"

    kwargs = {
        "n_systems": 8,
        "seed": 123,
        "system_type": "mixed",
        "mix_weights": {"single": 0.6, "east-west": 0.4},
    }
    generate_systems(weather_path, meta_path, out_a, **kwargs)
    generate_systems(weather_path, meta_path, out_b, **kwargs)

    meta_a = pd.read_csv(out_a / "systems_metadata.csv")
    meta_b = pd.read_csv(out_b / "systems_metadata.csv")

    pd.testing.assert_frame_equal(meta_a, meta_b)


def test_n_by_type_overrides_n_systems(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_counts"

    generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=999,
        seed=9,
        system_type="mixed",
        mix_weights={"single": 0.1, "east-west": 0.9},
        n_by_type={"single": 3, "east-west": 2},
    )

    metadata_df = pd.read_csv(out_dir / "systems_metadata.csv")
    assert len(metadata_df) == 5
    assert int((metadata_df["system_type"] == "single").sum()) == 3
    assert int((metadata_df["system_type"] == "east-west").sum()) == 2
