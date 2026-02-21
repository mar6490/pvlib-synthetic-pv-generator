# Design Decisions

## Why add `grid` mode
`random` is useful for diversity but not ideal for repeatable benchmark sweeps. `grid` mode creates deterministic combinations from explicit axes in YAML, enabling strict comparisons and ablation studies.

## Why AC-only noise
We model measurement/inverter-side uncertainty as post-processing on AC output while preserving deterministic, physically-derived DC trajectories.

## Metadata schema extension
Ground-truth columns are numeric and explicit (`*_true`) so downstream profiling/evaluation avoids parsing string-encoded fields. Legacy columns remain for compatibility, but GT columns are the authoritative reference.
