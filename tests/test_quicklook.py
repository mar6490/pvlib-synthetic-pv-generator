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


def test_find_system_csvs_and_load(tmp_path: Path) -> None:
    _write_system_csv(tmp_path / "system_010.csv")
    _write_system_csv(tmp_path / "system_002.csv")
    _write_system_csv(tmp_path / "system_001.csv")
    (tmp_path / "notes.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    files = find_system_csvs(tmp_path)
    assert [path.name for path in files] == ["system_001.csv", "system_002.csv", "system_010.csv"]

    loaded = load_system_csv(files[0])
    assert isinstance(loaded.index, pd.DatetimeIndex)
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


def test_plot_quicklooks_for_dir_smoke(tmp_path: Path) -> None:
    _write_system_csv(tmp_path / "system_001.csv")

    out_dir = tmp_path / "quicklooks"
    stats = plot_quicklooks_for_dir(tmp_path, out_dir)

    assert stats["found"] == 1
    assert stats["plotted"] == 1
    assert stats["errors"] == 0
    assert (out_dir / "system_001_quicklook.png").exists()
