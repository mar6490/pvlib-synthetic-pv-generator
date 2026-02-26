# CODEX CONTEXT

## Objective

Synthetic PV generator for algorithm validation.

## Timezone Policy

ALWAYS UTC+01:00 fixed. NEVER use Europe/Berlin.

## I/O Format

Weather CSV: time;ghi;dhi;t_luft;v_wind

System Output: time,dc_power_w,ac_power_w

## Allowed Libraries

-   pandas
-   numpy
-   pvlib
-   matplotlib

## Architecture Principles

-   Deterministic
-   Fixed timezone
-   No NaNs in output
-   Fail-fast validation

## Naming Convention

system_XXX.csv YYYY-MM-DD_HH-MM-SS directories

## Must Not Change

-   Fixed offset default
-   Two-plane east-west structure
-   Deterministic seed behavior
