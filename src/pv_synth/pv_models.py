"""Physical PV simulation functions based on pvlib."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pvlib


@dataclass
class SystemConfig:
    """Configuration parameters for one synthetic PV system."""

    system_id: int
    system_type: str
    plane_type: str | None
    kwp_total: float
    kwp_east: float | None
    kwp_west: float | None
    tilt: float
    azimuth: float | None
    dc_ac_ratio: float
    losses: float


def _solar_position(times: pd.DatetimeIndex, meta: dict) -> pd.DataFrame:
    return pvlib.solarposition.get_solarposition(
        times,
        latitude=meta["lat"],
        longitude=meta["lon"],
        altitude=meta.get("altitude", 0),
    )


def _dni_from_ghi_dhi(ghi: pd.Series, dhi: pd.Series, zenith: pd.Series) -> pd.Series:
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
    kwp_total: float,
    dc_ac_ratio: float,
    eta_inv_nom: float = 0.96,
) -> pd.Series:
    pac0 = kwp_total * 1000 / dc_ac_ratio
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
    solar_position = _solar_position(weather.index, meta)
    dni = _dni_from_ghi_dhi(weather["ghi"], weather["dhi"], solar_position["zenith"])

    if config.system_type == "east-west":
        kwp_east = config.kwp_east if config.kwp_east is not None else config.kwp_total / 2
        kwp_west = config.kwp_west if config.kwp_west is not None else config.kwp_total / 2

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

        dc_east = _dc_power(poa_east, weather["t_luft"], weather["v_wind"], kwp_east)
        dc_west = _dc_power(poa_west, weather["t_luft"], weather["v_wind"], kwp_west)
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
            config.kwp_total,
        ) * (1 - config.losses)

    ac_power = _ac_power(dc_power, config.kwp_total, config.dc_ac_ratio)

    return pd.DataFrame(
        {
            "time": weather.index,
            "dc_power_w": dc_power.values,
            "ac_power_w": ac_power.values,
        }
    )
