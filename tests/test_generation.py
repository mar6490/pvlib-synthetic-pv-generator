import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from pv_synth.generate import generate_systems
from pv_synth.io import load_weather

TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


def _write_weather_csv(path: Path) -> None:
    weather = pd.DataFrame(
        {
            "time": [
                "2025-01-01 10:00:00",
                "2025-01-01 10:15:00",
                "2025-01-01 10:30:00",
                "2025-01-01 10:45:00",
            ],
            "ghi": [500, 520, 530, 540],
            "dhi": [100, 110, 120, 130],
            "t_luft": [20, 20, 21, 21],
            "v_wind": [2, 2, 3, 3],
        }
    )
    weather.to_csv(path, index=False, sep=";")




def _write_weather_csv_naive(path: Path) -> None:
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


def _write_weather_csv_with_offset(path: Path) -> None:
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




def _write_weather_csv_naive(path: Path) -> None:
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


def _prepare_inputs(tmp_path: Path) -> tuple[Path, Path]:
    weather_path = tmp_path / "wetter-htw-2025-utc.csv"
    meta_path = tmp_path / "meta.json"
    _write_weather_csv(weather_path)
    _write_meta(meta_path)
    return weather_path, meta_path


def test_load_weather_localizes_timezone(tmp_path: Path) -> None:
    weather_path = tmp_path / "wetter-with-offset.csv"
    _write_weather_csv_with_offset(weather_path)
    weather = load_weather(weather_path, weather_timestamp="with_offset", fixed_offset_minutes=60)
    assert weather.index[0].utcoffset().total_seconds() == 3600


def test_generation_outputs_match_input_length(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs"

    run_dir = generate_systems(weather_path, meta_path, out_dir, n_systems=3, seed=1)

    first_system = run_dir / "system_001.csv"
    assert first_system.exists()
    system_df = pd.read_csv(first_system)
    assert len(system_df) == 4

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")
    assert len(metadata_df) == 3


def test_generator_creates_timestamp_subdir_when_base_given(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    base_out_dir = tmp_path / "outputs"

    run_dir = generate_systems(weather_path, meta_path, base_out_dir, n_systems=1, seed=2)

    assert run_dir.parent == base_out_dir
    assert TIMESTAMP_PATTERN.fullmatch(run_dir.name)
    assert (run_dir / "systems_metadata.csv").exists()


def test_generator_uses_timestamped_out_dir_directly(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    explicit_run_dir = tmp_path / "outputs" / "2026-02-20_16-12-33"

    run_dir = generate_systems(weather_path, meta_path, explicit_run_dir, n_systems=1, seed=3)

    assert run_dir == explicit_run_dir
    assert (run_dir / "systems_metadata.csv").exists()
    nested = [path for path in run_dir.iterdir() if path.is_dir() and TIMESTAMP_PATTERN.fullmatch(path.name)]
    assert not nested


def test_system_type_east_west_only_fixed_cardinal(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_ew"

    run_dir = generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=5,
        seed=42,
        system_type="east-west",
        ew_azimuth_mode="fixed_cardinal",
    )

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")

    assert (metadata_df["system_type"] == "east-west").all()
    assert ((metadata_df["kwp_east"] - metadata_df["kwp_total"] / 2).abs() < 1e-9).all()
    assert ((metadata_df["kwp_west"] - metadata_df["kwp_total"] / 2).abs() < 1e-9).all()
    assert (metadata_df["azimuth_east"] == 90.0).all()
    assert (metadata_df["azimuth_west"] == 270.0).all()


def test_system_type_single_only(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_single"

    run_dir = generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=5,
        seed=42,
        system_type="single",
        ew_azimuth_mode="jittered_180",
        roof_type="pitched",
        ew_azimuth_jitter_deg=50,
    )

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")

    assert (metadata_df["system_type"] == "single").all()
    assert metadata_df["kwp_east"].isna().all()
    assert metadata_df["kwp_west"].isna().all()
    assert metadata_df["azimuth_east"].isna().all()
    assert metadata_df["azimuth_west"].isna().all()
    assert metadata_df["roof_type"].isna().all()
    assert metadata_df["ew_azimuth_mode"].isna().all()
    assert pd.to_numeric(metadata_df["azimuth"], errors="coerce").notna().all()


def test_mixed_with_all_east_west_weight(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_mix"

    run_dir = generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=6,
        seed=7,
        system_type="mixed",
        mix_weights={"single": 0.0, "east-west": 1.0},
    )

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")
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
        "ew_azimuth_mode": "jittered_180",
        "roof_type": "mixed",
    }
    run_a = generate_systems(weather_path, meta_path, out_a, **kwargs)
    run_b = generate_systems(weather_path, meta_path, out_b, **kwargs)

    meta_a = pd.read_csv(run_a / "systems_metadata.csv")
    meta_b = pd.read_csv(run_b / "systems_metadata.csv")

    pd.testing.assert_frame_equal(meta_a, meta_b)


def test_n_by_type_overrides_n_systems(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_counts"

    run_dir = generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=999,
        seed=9,
        system_type="mixed",
        mix_weights={"single": 0.1, "east-west": 0.9},
        n_by_type={"single": 3, "east-west": 2},
    )

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")
    assert len(metadata_df) == 5
    assert int((metadata_df["system_type"] == "single").sum()) == 3
    assert int((metadata_df["system_type"] == "east-west").sum()) == 2


def test_jittered_flat_realism_ranges(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_flat"

    run_dir = generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=50,
        seed=42,
        system_type="east-west",
        ew_azimuth_mode="jittered_180",
        roof_type="flat",
    )

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")
    diff = (metadata_df["azimuth_west"] - metadata_df["azimuth_east"]) % 360

    assert ((diff - 180.0).abs() < 1e-9).all()
    assert metadata_df["azimuth_east"].between(75, 105).all()
    assert metadata_df["tilt"].between(5, 20).all()


def test_jittered_pitched_realism_ranges(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_pitched"

    run_dir = generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=50,
        seed=42,
        system_type="east-west",
        ew_azimuth_mode="jittered_180",
        roof_type="pitched",
    )

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")
    diff = (metadata_df["azimuth_west"] - metadata_df["azimuth_east"]) % 360

    assert ((diff - 180.0).abs() < 1e-9).all()
    assert metadata_df["azimuth_east"].between(60, 120).all()
    assert metadata_df["tilt"].between(20, 55).all()


def test_metadata_contains_lat_lon(tmp_path: Path) -> None:
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_latlon"

    run_dir = generate_systems(weather_path, meta_path, out_dir, n_systems=5, seed=11)

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")

    assert "lat" in metadata_df.columns
    assert "lon" in metadata_df.columns
    assert (metadata_df["lat"] == 52.5).all()
    assert (metadata_df["lon"] == 13.4).all()


def test_generate_cli_with_quicklook_hook(tmp_path: Path) -> None:
    if importlib.util.find_spec("matplotlib") is None:
        return
    weather_path, meta_path = _prepare_inputs(tmp_path)
    out_dir = tmp_path / "outputs_cli"
    quicklook_dir = tmp_path / "ql_cli"

    subprocess.run(
        [
            "python",
            "scripts/generate_synthetic_pv.py",
            "--weather",
            str(weather_path),
            "--meta",
            str(meta_path),
            "--out-dir",
            str(out_dir),
            "--n-systems",
            "1",
            "--seed",
            "1",
            "--quicklook",
            "--quicklook-dir",
            str(quicklook_dir),
        ],
        check=True,
    )

    run_dirs = [path for path in out_dir.iterdir() if path.is_dir() and TIMESTAMP_PATTERN.fullmatch(path.name)]
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "system_001.csv").exists()
    assert (quicklook_dir / "system_001_quicklook.png").exists()


def test_naive_fixed_offset_outputs_plus_0100(tmp_path: Path) -> None:
    weather_path = tmp_path / "wetter-naive-5min.csv"
    meta_path = tmp_path / "meta.json"
    out_dir = tmp_path / "outputs_fixed"
    _write_weather_csv_naive(weather_path)
    _write_meta(meta_path)

    run_dir = generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=2,
        seed=5,
        weather_timestamp="naive",
        fixed_offset_minutes=60,
    )

    metadata_df = pd.read_csv(run_dir / "systems_metadata.csv")
    assert (metadata_df["time_mode"] == "fixed_offset").all()
    assert (metadata_df["fixed_offset_minutes"] == 60).all()
    assert (metadata_df["tz_name"] == "UTC+01:00").all()

    system_df = pd.read_csv(run_dir / "system_001.csv")
    time_strings = system_df["time"].astype(str)
    assert time_strings.str.endswith("+01:00").all()
    assert (~time_strings.str.endswith("+02:00")).all()


def test_load_weather_naive_fixed_offset_index_is_aware(tmp_path: Path) -> None:
    weather_path = tmp_path / "wetter-naive-5min.csv"
    _write_weather_csv_naive(weather_path)

    weather = load_weather(
        weather_path,
        weather_timestamp="naive",
        fixed_offset_minutes=60,
    )

    assert isinstance(weather.index, pd.DatetimeIndex)
    assert weather.index.tz is not None
    assert weather.index[0].utcoffset().total_seconds() == 3600


def test_with_offset_also_normalized_to_fixed_offset(tmp_path: Path) -> None:
    weather_path = tmp_path / "wetter-with-offset.csv"
    _write_weather_csv_with_offset(weather_path)

    weather = load_weather(
        weather_path,
        weather_timestamp="with_offset",
        fixed_offset_minutes=60,
    )

    assert weather.index[0].utcoffset().total_seconds() == 3600


def test_no_nan_in_output_under_nan_prone_irradiance(tmp_path: Path) -> None:
    weather_path = tmp_path / "wetter-edge.csv"
    meta_path = tmp_path / "meta.json"
    out_dir = tmp_path / "outputs_edge"

    weather = pd.DataFrame(
        {
            "time": [
                "2025-01-01 06:00:00+01:00",
                "2025-01-01 06:05:00+01:00",
                "2025-01-01 06:10:00+01:00",
                "2025-01-01 06:15:00+01:00",
                "2025-01-01 06:20:00+01:00",
            ],
            "ghi": [0, 5, 10, 20, 30],
            "dhi": [0, 10, 15, 25, 35],
            "t_luft": [5, 5, 5, 5, 5],
            "v_wind": [1, 1, 1, 1, 1],
        }
    )
    weather.to_csv(weather_path, index=False, sep=";")
    _write_meta(meta_path)

    run_dir = generate_systems(
        weather_path,
        meta_path,
        out_dir,
        n_systems=2,
        seed=7,
        weather_timestamp="with_offset",
        fixed_offset_minutes=60,
    )

    for path in run_dir.glob("system_*.csv"):
        df = pd.read_csv(path)
        assert not df["dc_power_w"].isna().any()
        assert not df["ac_power_w"].isna().any()


def test_default_cli_time_policy_is_fixed_plus_0100(tmp_path: Path) -> None:
    weather_path = tmp_path / "wetter-naive-default.csv"
    meta_path = tmp_path / "meta.json"
    out_dir = tmp_path / "outputs_default"
    _write_weather_csv_naive(weather_path)
    _write_meta(meta_path)

    run_dir = generate_systems(weather_path, meta_path, out_dir, n_systems=1, seed=13)
    system_df = pd.read_csv(run_dir / "system_001.csv")
    ts = system_df["time"].astype(str)
    assert ts.str.endswith("+01:00").all()
    assert (~ts.str.endswith("+02:00")).all()


def test_output_timestamp_naive_and_with_offset_modes(tmp_path: Path) -> None:
    weather_path = tmp_path / "wetter-naive-output-ts.csv"
    meta_path = tmp_path / "meta.json"
    _write_weather_csv_naive(weather_path)
    _write_meta(meta_path)

    run_with_offset = generate_systems(
        weather_path,
        meta_path,
        tmp_path / "out_with_offset",
        n_systems=1,
        seed=101,
        output_timestamp="with_offset",
    )
    df_with_offset = pd.read_csv(run_with_offset / "system_001.csv")
    ts_with_offset = pd.to_datetime(df_with_offset["time"], errors="raise")
    assert ts_with_offset.dt.tz is not None
    assert ts_with_offset.iloc[0].utcoffset().total_seconds() == 3600

    run_naive = generate_systems(
        weather_path,
        meta_path,
        tmp_path / "out_naive",
        n_systems=1,
        seed=101,
        output_timestamp="naive",
    )
    df_naive = pd.read_csv(run_naive / "system_001.csv")
    ts_naive = pd.to_datetime(df_naive["time"], errors="raise")
    assert ts_naive.dt.tz is None

    metadata_with_offset = pd.read_csv(run_with_offset / "systems_metadata.csv")
    metadata_naive = pd.read_csv(run_naive / "systems_metadata.csv")
    assert (metadata_with_offset["output_timestamp"] == "with_offset").all()
    assert (metadata_naive["output_timestamp"] == "naive").all()


def test_output_timestamp_invalid_value_raises(tmp_path: Path) -> None:
    weather_path = tmp_path / "wetter-invalid-output-ts.csv"
    meta_path = tmp_path / "meta.json"
    _write_weather_csv_naive(weather_path)
    _write_meta(meta_path)

    with pytest.raises(ValueError, match="output_timestamp"):
        generate_systems(
            weather_path,
            meta_path,
            tmp_path / "out_invalid",
            n_systems=1,
            seed=1,
            output_timestamp="broken",  # type: ignore[arg-type]
        )
