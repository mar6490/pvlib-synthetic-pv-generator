# Pipeline

## Defaults
- `generation_mode=random`
- `time_mode=fixed_offset`
- `fixed_offset_minutes=60`
- `weather_timestamp=naive`
- `noise_model=none`
- `noise_sigma_rel=0.02`

## Steps
1. Load/validate weather and normalize to a fixed tz-aware UTC+offset index (no DST switching).
2. Build scenarios:
   - `random`: stochastic sampling controlled by `--seed`.
   - `grid`: deterministic cartesian product from `--scenario-file`.
3. Simulate per-system DC/AC with pvlib.
4. Optionally apply AC-only noise.
5. Persist per-system CSV plus machine-readable ground-truth metadata.

## Grid mode
`grid` expands yaml axes deterministically. For east-west systems:
- `azimuth_east = (center_deg - half_delta_deg) % 360`
- `azimuth_west = (center_deg + half_delta_deg) % 360`

`--seed` does not affect scenario order in grid mode.

## Noise model
For `--noise-model gaussian`:

\[
P_{ac,noisy}(t)=\max\left(0, P_{ac}(t)\cdot (1+\epsilon_t)\right),\quad \epsilon_t \sim \mathcal{N}(0,\sigma_{rel})
\]

Noise is deterministic for fixed seed and is only applied to AC.
