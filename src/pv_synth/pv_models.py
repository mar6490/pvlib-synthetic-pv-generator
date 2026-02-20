"""Physical PV simulation functions based on pvlib.

High-level flow:
1) Compute sun position for each timestamp.
2) Derive DNI from measured GHI and DHI.
3) Transpose irradiance onto module plane (POA).
4) Estimate cell temperature.
5) Compute DC power (PVWatts DC model).
6) Convert DC to AC and apply inverter clipping (PVWatts inverter model).

This module intentionally does **not** apply synthetic shading.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pvlib


@dataclass
class SystemConfig:
    """Configuration parameters for one synthetic PV system.

    Field glossary (non-technical wording):
    - ``kwp``: nominal panel size at standard test conditions.
    - ``tilt``: roof/module inclination angle in degrees.
    - ``azimuth``: compass direction in degrees (None for east-west split).
    - ``dc_ac_ratio``: sizing ratio between panel DC peak and inverter AC peak.
    - ``losses``: aggregate fractional losses (cables, mismatch, dirt, etc.).
    """

    system_id: int
    system_type: str
    kwp: float
    tilt: float
    azimuth: float | None
    dc_ac_ratio: float
    losses: float


def _solar_position(times: pd.DatetimeIndex, meta: dict) -> pd.DataFrame:
    """Compute solar geometry (zenith, azimuth, ...) for each timestamp."""
    return pvlib.solarposition.get_solarposition(
        times,
        latitude=meta["lat"],
        longitude=meta["lon"],
        altitude=meta.get("altitude", 0),
    )


def _dni_from_ghi_dhi(ghi: pd.Series, dhi: pd.Series, zenith: pd.Series) -> pd.Series:
    """Estimate direct normal irradiance (DNI) from available weather channels."""
    dni = pvlib.irradiance.dni(ghi=ghi, dhi=dhi, zenith=zenith)
    return dni.clip(lower=0)


def _poa_irradiance(
    solar_position: pd.DataFrame,
    ghi: pd.Series,
    dhi: pd.Series,
    dni: pd.Series,
    tilt: float,
    azimuth: float,
) -> pd.Series:
    """Compute plane-of-array irradiance for a module surface orientation."""
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        dni=dni,
        ghi=ghi,
        dhi=dhi,
    )
    return poa["poa_global"].clip(lower=0)


def _dc_power(
    poa_global: pd.Series,
    temp_air: pd.Series,
    wind_speed: pd.Series,
    kwp: float,
) -> pd.Series:
    """Compute PV array DC output using PVWatts-style equations."""
    # pvlib's PVsyst temperature model estimates module cell temperature,
    # which strongly influences power.
    temp_cell = pvlib.temperature.pvsyst_cell(
        poa_global, temp_air=temp_air, wind_speed=wind_speed
    )
    return pvlib.pvsystem.pvwatts_dc(
        poa_global,
        temp_cell,
        pdc0=kwp * 1000,
        gamma_pdc=-0.004,
    ).clip(lower=0)


def _ac_power(
    dc_power: pd.Series,
    kwp: float,
    dc_ac_ratio: float,
    eta_inv_nom: float = 0.96,
) -> pd.Series:
    """Convert DC to AC with nominal inverter efficiency and clipping."""
    pac0 = kwp * 1000 / dc_ac_ratio
    pdc0 = pac0 / eta_inv_nom
    return pvlib.inverter.pvwatts(
        dc_power,
        pdc0=pdc0,
        eta_inv_nom=eta_inv_nom,
    ).clip(lower=0)


def simulate_system(
    weather: pd.DataFrame,
    meta: dict,
    config: SystemConfig,
) -> pd.DataFrame:
    """Simulate one PV system and return a tidy time series dataframe.

    East-west logic:
    - Simulate an east sub-array (90°) and west sub-array (270°).
    - Split total kWp equally between both sides.
    - Sum DC outputs, apply losses once, then pass through one inverter model.
    """
    solar_position = _solar_position(weather.index, meta)
    dni = _dni_from_ghi_dhi(weather["ghi"], weather["dhi"], solar_position["zenith"])

    if config.system_type == "east-west":
        poa_east = _poa_irradiance(
            solar_position,
            weather["ghi"],
            weather["dhi"],
            dni,
            tilt=config.tilt,
            azimuth=90.0,
        )
        poa_west = _poa_irradiance(
            solar_position,
            weather["ghi"],
            weather["dhi"],
            dni,
            tilt=config.tilt,
            azimuth=270.0,
        )

        dc_east = _dc_power(poa_east, weather["t_luft"], weather["v_wind"], config.kwp / 2)
        dc_west = _dc_power(poa_west, weather["t_luft"], weather["v_wind"], config.kwp / 2)

        dc_power = (dc_east + dc_west) * (1 - config.losses)
    else:
        poa = _poa_irradiance(
            solar_position,
            weather["ghi"],
            weather["dhi"],
            dni,
            tilt=config.tilt,
            azimuth=config.azimuth or 180.0,
        )
        dc_power = _dc_power(
            poa,
            weather["t_luft"],
            weather["v_wind"],
            config.kwp,
        ) * (1 - config.losses)

    ac_power = _ac_power(dc_power, config.kwp, config.dc_ac_ratio)

    return pd.DataFrame(
        {
            "time": weather.index,
            "dc_power_w": dc_power.values,
            "ac_power_w": ac_power.values,
        }
    )
