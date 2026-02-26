"""Noise models for synthetic PV outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_ac_noise(
    ac_power: pd.Series,
    noise_model: str = "none",
    noise_sigma_rel: float = 0.02,
    seed: int | None = None,
) -> pd.Series:
    """Apply optional deterministic noise to AC power only."""
    if noise_model not in {"none", "gaussian"}:
        raise ValueError("--noise-model must be one of: none, gaussian.")
    if noise_sigma_rel < 0:
        raise ValueError("--noise-sigma-rel must be >= 0.")

    if noise_model == "none":
        return ac_power

    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, noise_sigma_rel, size=len(ac_power))
    noisy = ac_power.to_numpy(dtype=float) * (1.0 + eps)
    return pd.Series(np.clip(noisy, 0.0, None), index=ac_power.index)
