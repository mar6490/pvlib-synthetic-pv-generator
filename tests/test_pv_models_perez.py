from datetime import timezone, timedelta

import pandas as pd

from pv_synth.pv_models import SystemConfig, _dni_from_ghi_dhi, _poa_irradiance, simulate_system


def _mini_weather() -> pd.DataFrame:
    idx = pd.date_range(
        "2025-06-01 11:00:00",
        periods=6,
        freq="15min",
        tz=timezone(timedelta(hours=1)),
    )
    return pd.DataFrame(
        {
            "ghi": [400.0, 500.0, 600.0, 650.0, 550.0, 450.0],
            "dhi": [90.0, 100.0, 110.0, 120.0, 100.0, 95.0],
            "t_luft": [20.0, 21.0, 22.0, 23.0, 22.0, 21.0],
            "v_wind": [2.0, 2.2, 2.5, 2.3, 2.1, 2.0],
        },
        index=idx,
    )


def _meta() -> dict:
    return {"lat": 52.5, "lon": 13.4, "tz": "UTC"}


def test_poa_irradiance_uses_perez_model(monkeypatch) -> None:
    captured = {}

    def fake_get_total_irradiance(**kwargs):
        captured.update(kwargs)
        return pd.DataFrame({"poa_global": [200.0, 210.0]}, index=[0, 1])

    monkeypatch.setattr(
        "pv_synth.pv_models.pvlib.irradiance.get_total_irradiance",
        fake_get_total_irradiance,
    )

    solar_position = pd.DataFrame(
        {
            "apparent_zenith": [30.0, 35.0],
            "azimuth": [170.0, 175.0],
        }
    )
    ghi = pd.Series([500.0, 520.0])
    dhi = pd.Series([110.0, 120.0])
    dni = pd.Series([600.0, 620.0])

    out = _poa_irradiance(solar_position, ghi, dhi, dni, tilt=30.0, azimuth=180.0)

    assert captured["model"] == "perez"
    assert "dni_extra" in captured
    assert len(captured["dni_extra"]) == len(solar_position)
    assert (out >= 0).all()


def test_dni_is_zeroed_for_high_apparent_zenith(monkeypatch) -> None:
    def fake_dni(**kwargs):
        return pd.Series([500.0, 500.0], index=kwargs["ghi"].index)

    monkeypatch.setattr("pv_synth.pv_models.pvlib.irradiance.dni", fake_dni)

    idx = pd.date_range(
        "2025-06-01 11:00:00",
        periods=2,
        freq="15min",
        tz=timezone(timedelta(hours=1)),
    )
    ghi = pd.Series([400.0, 400.0], index=idx)
    dhi = pd.Series([100.0, 100.0], index=idx)
    zenith = pd.Series([70.0, 89.0], index=idx)
    apparent_zenith = pd.Series([70.0, 89.0], index=idx)

    dni = _dni_from_ghi_dhi(ghi, dhi, zenith, apparent_zenith, _meta())

    assert dni.iloc[0] >= 0.0
    assert dni.iloc[1] == 0.0


def test_simulate_system_outputs_are_non_negative_with_fixed_offset_index() -> None:
    weather = _mini_weather()
    config = SystemConfig(
        system_id=1,
        system_type="single",
        plane_type="south",
        roof_type=None,
        ew_azimuth_mode=None,
        kwp_total=8.0,
        kwp_east=None,
        kwp_west=None,
        tilt=30.0,
        azimuth=180.0,
        azimuth_east=None,
        azimuth_west=None,
        dc_ac_ratio=1.15,
        losses=0.1,
    )

    out = simulate_system(weather=weather, meta=_meta(), config=config)

    assert list(out.columns) == ["time", "dc_power_w", "ac_power_w"]
    assert (out["dc_power_w"] >= 0).all()
    assert (out["ac_power_w"] >= 0).all()
    assert pd.DatetimeIndex(out["time"]).tz is not None
    assert pd.DatetimeIndex(out["time"])[0].utcoffset().total_seconds() == 3600
