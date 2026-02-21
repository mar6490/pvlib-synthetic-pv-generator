# Assumptions

- Time axis is always timezone-aware fixed offset (`fixed_offset_minutes`, default +60 minutes).
- No DST-based output switching is used.
- East-west geometry maintains 180° separation in random mode.
- Noise is optional and AC-only; DC remains physical model output.
- Defaults remain backward-compatible (`generation_mode=random`, `noise_model=none`).
