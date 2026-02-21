# Design Decisions

## 1. Fixed Offset Timezone

Decision: Always use UTC+01:00 fixed. Reason: - SDT incompatibility with
DST - Logger-style continuous time axis - Avoid mixed offsets (+01/+02)

## 2. East-West Modeling

Decision: - Two independent DC calculations - 180° azimuth difference
enforced - Jittered mode optional Reason: - Physical realism -
Real-world EFH configurations

## 3. Deterministic Sampling

Decision: - Seed-based RNG - Deterministic type ordering Reason: -
Reproducibility for research

## 4. NaN Handling

Decision (pending full implementation): - Replace NaN with 0 in output
layer Reason: - Downstream tool stability
