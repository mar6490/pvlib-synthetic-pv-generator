import json
from pathlib import Path

import pandas as pd

from pv_synth.generate import generate_systems
from pv_synth.io import load_weather


def _write_weather_csv(path: Path) -> None:
    """Create a small weather CSV fixture for testing."""
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
    """Create a minimal metadata JSON fixture for testing."""
    meta = {"lat": 52.5, "lon": 13.4, "tz": "Europe/Berlin"}
    path.write_text(json.dumps(meta), encoding="utf-8")


def test_load_weather_localizes_timezone(tmp_path: Path) -> None:
    """Verify timestamps are localized to Europe/Berlin."""
    weather_path = tmp_path / "wetter-htw-2025-utc.csv"
    _write_weather_csv(weather_path)

    weather = load_weather(weather_path, "Europe/Berlin")

    assert str(weather.index.tz) == "Europe/Berlin"


def test_generation_outputs_match_input_length(tmp_path: Path) -> None:
    """Check output length and metadata rows match expectations."""
    weather_path = tmp_path / "wetter-htw-2025-utc.csv"
    meta_path = tmp_path / "meta.json"
    out_dir = tmp_path / "outputs"
    _write_weather_csv(weather_path)
    _write_meta(meta_path)

    generate_systems(weather_path, meta_path, out_dir, n_systems=3, seed=1)

    first_system = out_dir / "system_001.csv"
    assert first_system.exists()
    system_df = pd.read_csv(first_system)
    assert len(system_df) == 4

    metadata_df = pd.read_csv(out_dir / "systems_metadata.csv")
    assert len(metadata_df) == 3
