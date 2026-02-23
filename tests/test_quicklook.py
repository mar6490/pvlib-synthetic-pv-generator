import re
import subprocess
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("matplotlib")

from pv_synth.quicklook import (
    find_system_csvs,
    load_system_csv,
    plot_quicklooks_for_dir,
    plot_system_quicklook,
)

TIMESTAMP_PATTERN = re.compile(r"^quicklooks_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


def _write_system_csv(path: Path, periods: int = 96 * 10) -> None:
    time_index = pd.date_range("2025-01-01 00:00:00+01:00", periods=periods, freq="15min")
    ac = []
    for ts in time_index:
        hour = ts.hour + ts.minute / 60
        if 6 <= hour <= 18:
            value = max(0.0, (1 - abs(hour - 12) / 6) * 4000)
        else:
            value = 0.0
        ac.append(value)

    df = pd.DataFrame(
        {
            "time": time_index.astype(str),
            "dc_power_w": [v * 1.05 for v in ac],
            "ac_power_w": ac,
        }
    )
    df.to_csv(path, index=False)


def _write_dst_mixed_system_csv(path: Path) -> None:
    # Explicit mixed offsets around DST switch to ensure robust utc parsing.
    times = [
        "2025-03-30 00:00:00+01:00",
        "2025-03-30 00:15:00+01:00",
        "2025-03-30 00:30:00+01:00",
        "2025-03-30 03:00:00+02:00",
        "2025-03-30 03:15:00+02:00",
        "2025-03-30 03:30:00+02:00",
    ]
    df = pd.DataFrame(
        {
            "time": times,
            "dc_power_w": [0, 0, 10, 500, 900, 1200],
            "ac_power_w": [0, 0, 8, 450, 850, 1100],
        }
    )
    df.to_csv(path, index=False)


def test_find_system_csvs_and_load(tmp_path: Path) -> None:
    _write_system_csv(tmp_path / "system_010.csv")
    _write_system_csv(tmp_path / "system_002.csv")
    _write_system_csv(tmp_path / "system_001.csv")
    (tmp_path / "notes.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    files = find_system_csvs(tmp_path)
    assert [path.name for path in files] == ["system_001.csv", "system_002.csv", "system_010.csv"]

    loaded = load_system_csv(files[0])
    assert isinstance(loaded.index, pd.DatetimeIndex)
    assert str(loaded.index.tz) == "UTC"
    assert "ac_power_w" in loaded.columns


def test_plot_system_quicklook_smoke(tmp_path: Path) -> None:
    system_csv = tmp_path / "system_001.csv"
    _write_system_csv(system_csv)
    out_png = tmp_path / "quicklooks" / "system_001_quicklook.png"

    written = plot_system_quicklook(system_csv, out_png, normalize=True, overwrite=False)
    assert written is True
    assert out_png.exists()

    written_again = plot_system_quicklook(system_csv, out_png, normalize=True, overwrite=False)
    assert written_again is False


def test_plot_system_quicklook_dst_mixed_offsets_smoke(tmp_path: Path) -> None:
    system_csv = tmp_path / "system_001.csv"
    _write_dst_mixed_system_csv(system_csv)
    out_png = tmp_path / "quicklooks" / "system_001_quicklook.png"

    written = plot_system_quicklook(system_csv, out_png, normalize=True, overwrite=False, tz="Europe/Berlin")
    assert written is True
    assert out_png.exists()


def test_plot_quicklooks_for_dir_smoke(tmp_path: Path) -> None:
    _write_system_csv(tmp_path / "system_001.csv")

    out_dir = tmp_path / "quicklooks"
    stats = plot_quicklooks_for_dir(tmp_path, out_dir)

    assert stats["found"] == 1
    assert stats["plotted"] == 1
    assert stats["errors"] == 0
    assert (out_dir / "system_001_quicklook.png").exists()


def test_quicklook_standalone_default_creates_timestamped_dir(tmp_path: Path) -> None:
    in_dir = tmp_path / "run_1"
    in_dir.mkdir(parents=True)
    _write_system_csv(in_dir / "system_001.csv")

    subprocess.run(
        [
            "python",
            "scripts/quicklook_systems.py",
            "--in-dir",
            str(in_dir),
        ],
        check=True,
    )

    ql_dirs = [path for path in in_dir.iterdir() if path.is_dir() and TIMESTAMP_PATTERN.fullmatch(path.name)]
    assert len(ql_dirs) == 1
    assert (ql_dirs[0] / "system_001_quicklook.png").exists()


def test_quicklook_standalone_respects_explicit_out_dir(tmp_path: Path) -> None:
    in_dir = tmp_path / "run_2"
    in_dir.mkdir(parents=True)
    _write_system_csv(in_dir / "system_001.csv")

    explicit_out = in_dir / "my_quicklooks"
    subprocess.run(
        [
            "python",
            "scripts/quicklook_systems.py",
            "--in-dir",
            str(in_dir),
            "--out-dir",
            str(explicit_out),
        ],
        check=True,
    )

    assert explicit_out.exists()
    assert (explicit_out / "system_001_quicklook.png").exists()
    nested = [path for path in explicit_out.iterdir() if path.is_dir() and TIMESTAMP_PATTERN.fullmatch(path.name)]
    assert not nested
