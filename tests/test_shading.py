import pandas as pd

from pv_synth.shading import compute_shading_factor


def test_shading_none_returns_one() -> None:
    solar_position = pd.DataFrame(
        {
            "azimuth": [90.0, 180.0],
            "apparent_zenith": [60.0, 70.0],
        },
        index=pd.date_range("2025-01-01", periods=2, freq="15min", tz="UTC"),
    )

    shading = compute_shading_factor(solar_position, "none", {})

    assert (shading == 1.0).all()


def test_shading_obstruction_reduces_factor() -> None:
    solar_position = pd.DataFrame(
        {
            "azimuth": [90.0, 200.0],
            "apparent_zenith": [85.0, 30.0],
        },
        index=pd.date_range("2025-01-01", periods=2, freq="15min", tz="UTC"),
    )
    profile = {
        "sectors": [(80.0, 100.0)],
        "horizon_deg": 10.0,
        "strength": 0.5,
        "softness_deg": 2.0,
    }

    shading = compute_shading_factor(solar_position, "horizon_obstruction", profile)

    assert shading.iloc[0] < 1.0
    assert shading.iloc[1] == 1.0
