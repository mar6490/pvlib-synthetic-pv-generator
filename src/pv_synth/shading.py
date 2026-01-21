"""Simple shading profile helpers.

These are optional, toy shading profiles intended to introduce variety.
They apply a multiplicative factor to irradiance or power by time of day.
"""

from __future__ import annotations

import pandas as pd


def shading_factor(times: pd.DatetimeIndex, shading_type: str) -> pd.Series:
    """Return multiplicative shading factors for the given timestamps.

    Args:
        times: Timestamp index for which to compute shading.
        shading_type: One of "none", "morning", "evening", "midday".
    """
    shading_type = shading_type.lower()
    # Start with no shading (factor 1.0) everywhere.
    factors = pd.Series(1.0, index=times)

    if shading_type == "none":
        return factors

    # Convert timestamps to decimal hours for simple time-of-day rules.
    hours = times.hour + times.minute / 60.0

    if shading_type == "morning":
        factors.loc[hours < 10] = 0.7
    elif shading_type == "evening":
        factors.loc[hours > 16] = 0.7
    elif shading_type == "midday":
        factors.loc[(hours >= 12) & (hours <= 14)] = 0.8
    else:
        raise ValueError(f"Unknown shading type: {shading_type}")

    return factors
