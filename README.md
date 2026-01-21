# Synthetic PV Generator (pvlib)

Generate synthetic residential PV power time series from measured weather data
using pvlib. Intended for testing PV orientation and shading inference methods.

This repository reads an existing weather file (no new weather data is created)
and produces multiple PV system time series plus a metadata summary.

## Features
- 15-minute resolution
- Typical residential systems (DACH)
- Variable tilt, azimuth, size
- pvlib-based physical modeling

## Status
Work in progress.

## What this repository does
- Reads 15-minute weather data (GHI, DHI, air temperature, wind speed) from a CSV.
- Computes solar position, derived DNI, POA irradiance, cell temperature, and DC/AC
  power using pvlib (PVWatts models).
- Generates multiple residential PV scenarios typical for DACH, including south,
  east, west, and combined east-west orientations.
- Writes per-system CSVs containing DC and AC power and a consolidated metadata file.

## Inputs
- Weather data CSV with columns: `time`, `ghi`, `dhi`, `t_luft`, `v_wind`.
  - Trennzeichen: Komma oder Semikolon (z. B. `;`).
- Site metadata JSON containing at least `lat`, `lon`, and `tz` (e.g. `Europe/Berlin`).
  - Hinweis: Wenn die Zeitstempel bereits timezone-aware sind (z. B. `+01:00`/`+02:00`),
    werden sie direkt nach `tz` konvertiert. Für naive, DST-blinde Reihen wird die
    doppelte Stunde beim Wechsel auf Winterzeit entfernt.

## Usage
Install dependencies:

```bash
pip install -r requirements.txt
```

Generate synthetic systems:

```bash
py scripts\generate_synthetic_pv.py --weather data\wetter-htw-2025-utc.csv --meta data\site_meta.json --out-dir outputs --n-systems 30 --seed 42

```

Outputs:
- Per-system CSVs at `outputs/system_<id>.csv`
- `outputs/systems_metadata.csv` for system definitions

## Output details
- `outputs/system_<id>.csv` columns:
  - `time`: localized timestamps (Europe/Berlin)
  - `dc_power_w`: DC power in watts
  - `ac_power_w`: AC power in watts (after inverter clipping)
- `outputs/systems_metadata.csv` columns:
  - `system_id`, `system_type`, `kwp`, `tilt`, `azimuth`, `dc_ac_ratio`,
    `losses`, `shading_type`
