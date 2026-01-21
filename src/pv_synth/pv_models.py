"""PV modeling functions using pvlib.

This module turns weather data plus system configuration into DC and AC power.
It uses pvlib for solar position, irradiance transposition, temperature, and
PVWatts-style power models.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pvlib

from pv_synth.shading import compute_shading_factor


@dataclass
class SystemConfig:
    """Configuration for a synthetic PV system."""
    system_id: int
    system_type: str
    kwp: float
    tilt: float
    azimuth: float | None
    dc_ac_ratio: float
    losses: float
    shading_model: str
    shading_profiles: dict[str, dict]


def _solar_position(times: pd.DatetimeIndex, meta: dict) -> pd.DataFrame:
    """Compute solar position for each timestamp."""
    return pvlib.solarposition.get_solarposition(
        times,
        latitude=meta["lat"],
        longitude=meta["lon"],
        altitude=meta.get("altitude", 0),
    )


def _dni_from_ghi_dhi(ghi: pd.Series, dhi: pd.Series, zenith: pd.Series) -> pd.Series:
    """Estimate DNI from GHI, DHI, and solar zenith."""
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
    """Compute plane-of-array (POA) irradiance for a tilted surface."""
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
    """Compute DC power using PVWatts with a temperature model."""
    # Estimate cell temperature using the PVsyst model.
    temp_cell = pvlib.temperature.pvsyst_cell(
        poa_global, temp_air=temp_air, wind_speed=wind_speed
    )
    # Compute DC power from irradiance and cell temperature.
    return pvlib.pvsystem.pvwatts_dc(
        poa_global, temp_cell, pdc0=kwp * 1000, gamma_pdc=-0.004
    ).clip(lower=0)


def _ac_power(
    dc_power: pd.Series,
    kwp: float,
    dc_ac_ratio: float,
    eta_inv_nom: float = 0.96,
) -> pd.Series:
    """Compute AC power with inverter efficiency and clipping."""
    # Nominal AC power derived from the DC/AC ratio.
    pac0 = kwp * 1000 / dc_ac_ratio
    # PVWatts inverter model expects a DC reference power.
    pdc0 = pac0 / eta_inv_nom
    return pvlib.inverter.pvwatts(
        dc_power, pdc0=pdc0, eta_inv_nom=eta_inv_nom
    ).clip(lower=0)


def simulate_system(
    weather: pd.DataFrame,
    meta: dict,
    config: SystemConfig,
) -> pd.DataFrame:
    """Simulate DC/AC power for a system.

    For east-west systems we model two sub-arrays and aggregate their DC power
    before applying inverter clipping.
    """
    solar_position = _solar_position(weather.index, meta)
    # Estimate DNI so we can compute POA irradiance.
    dni = _dni_from_ghi_dhi(weather["ghi"], weather["dhi"], solar_position["zenith"])

    shading = None
    shading_east = None
    shading_west = None

    if config.system_type == "east-west":
        # East-facing sub-array.
        poa_east = _poa_irradiance(
            solar_position,
            weather["ghi"],
            weather["dhi"],
            dni,
            tilt=config.tilt,
            azimuth=90.0,
        )
        # West-facing sub-array.
        poa_west = _poa_irradiance(
            solar_position,
            weather["ghi"],
            weather["dhi"],
            dni,
            tilt=config.tilt,
            azimuth=270.0,
        )
        # Apply shading profiles to both sub-arrays.
        shading_east = compute_shading_factor(
            solar_position, config.shading_model, config.shading_profiles.get("east", {})
        )
        shading_west = compute_shading_factor(
            solar_position, config.shading_model, config.shading_profiles.get("west", {})
        )
        poa_east = poa_east * shading_east
        poa_west = poa_west * shading_west
        # Split DC capacity evenly across east and west.
        dc_east = _dc_power(
            poa_east, weather["t_luft"], weather["v_wind"], config.kwp / 2
        )
        dc_west = _dc_power(
            poa_west, weather["t_luft"], weather["v_wind"], config.kwp / 2
        )
        # Aggregate DC power and apply system losses.
        dc_power = (dc_east + dc_west) * (1 - config.losses)
    else:
        # Single-orientation system (south/east/west).
        poa = _poa_irradiance(
            solar_position,
            weather["ghi"],
            weather["dhi"],
            dni,
            tilt=config.tilt,
            azimuth=config.azimuth or 180.0,
        )
        shading = compute_shading_factor(
            solar_position, config.shading_model, config.shading_profiles.get("single", {})
        )
        poa = poa * shading
        # Apply system losses after DC generation.
        dc_power = _dc_power(
            poa, weather["t_luft"], weather["v_wind"], config.kwp
        ) * (1 - config.losses)

    # Convert DC to AC, including inverter clipping via DC/AC ratio.
    ac_power = _ac_power(dc_power, config.kwp, config.dc_ac_ratio)

    # Return a tidy dataframe for CSV output.
    return pd.DataFrame(
        {
            "time": weather.index,
            "dc_power_w": dc_power.values,
            "ac_power_w": ac_power.values,
            "shading_factor": (
                (shading_east + shading_west) / 2 if config.system_type == "east-west" else shading
            ).values,
        }
    )
