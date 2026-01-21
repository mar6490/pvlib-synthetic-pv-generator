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

## Weather input format (strict)
The pipeline accepts **only one** weather file format and will fail fast otherwise:
- CSV must be semicolon-separated (`;`).
- Required header (case-sensitive): `time;ghi;dhi;t_luft;v_wind`.
- `time` must include an explicit UTC offset (`±HH:MM`), e.g. `+01:00` or `+02:00`.
- Resolution must be continuous at 15-minute intervals.
- Internally, timestamps are converted to UTC.

Example (copy/paste):
```csv
time;ghi;dhi;t_luft;v_wind
2025-01-01 00:00:00+01:00;0;0;1.5;6.8933333333333335
2025-01-01 00:15:00+01:00;0;0;1.4466666666666668;7.446666666666666
2025-01-01 00:30:00+01:00;0;0;1.4333333333333333;7.053333333333334
2025-01-01 00:45:00+01:00;0;0;1.4133333333333333;6.94
2025-01-01 01:00:00+01:00;0;0;1.4533333333333334;7.006666666666667
```

## Usage
Install dependencies:

```bash
pip install -r requirements.txt
```

Generate synthetic systems:

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025-utc.csv \
  --meta data/site_meta.json \
  --out-dir outputs \
  --n-systems 30 \
  --seed 42
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

## System ranges and orientations
- kWp range: 3–15 kWp (randomized per system).
- Tilt range: 10–45 degrees.
- Azimuth ranges (degrees):
  - South-facing: centered around 180°, clipped to 135–225°.
  - East-facing: centered around 90°, clipped to 70–110°.
  - West-facing: centered around 270°, clipped to 250–290°.
- Combined orientation:
  - East–West systems are modeled as two sub-arrays (90° and 270°) with the
    total kWp split evenly.
