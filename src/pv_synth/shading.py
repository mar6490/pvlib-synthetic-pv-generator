"""Horizon obstruction shading profile helpers.

This module provides a deterministic, sun-geometry-based shading model
that approximates horizon obstructions using azimuth sectors and a
soft elevation cutoff.
"""

from __future__ import annotations

import math

import pandas as pd


def _sigmoid(x: pd.Series) -> pd.Series:
    return 1 / (1 + (-x).apply(math.exp))


def _azimuth_in_sector(azimuth: pd.Series, start: float, end: float) -> pd.Series:
    if start <= end:
        return (azimuth >= start) & (azimuth <= end)
    return (azimuth >= start) | (azimuth <= end)


def compute_shading_factor(
    solar_position: pd.DataFrame, shading_model: str, profile: dict
) -> pd.Series:
    """Compute shading factor from solar geometry for a single profile."""
    if shading_model == "none":
        return pd.Series(1.0, index=solar_position.index)

    sectors = profile.get("sectors", [])
    horizon_deg = float(profile.get("horizon_deg", 0))
    strength = float(profile.get("strength", 0))
    softness_deg = float(profile.get("softness_deg", 1))

    azimuth = solar_position["azimuth"]
    elevation = 90 - solar_position["apparent_zenith"]

    if not sectors or strength <= 0:
        return pd.Series(1.0, index=solar_position.index)

    in_sector = pd.Series(False, index=solar_position.index)
    for start, end in sectors:
        in_sector = in_sector | _azimuth_in_sector(azimuth, start, end)

    x = (horizon_deg - elevation) / max(softness_deg, 0.1)
    reduction = strength * _sigmoid(x)
    factor = 1 - reduction
    factor = factor.where(in_sector, 1.0)
    factor = factor.clip(lower=0.0, upper=1.0)
    factor = factor.where(elevation >= 0, 0.0)

    return factor
