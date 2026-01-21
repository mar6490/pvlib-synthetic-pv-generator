# Synthetic PV Generator (pvlib)

Generate synthetic residential PV power time series from measured weather data
using pvlib. Intended for testing PV orientation and shading inference methods.

## Features
- 15-minute resolution
- Typical residential systems (DACH)
- Variable tilt, azimuth, size
- pvlib-based physical modeling

## Status
Work in progress.

## Usage
Install dependencies:

```bash
pip install -r requirements.txt
```

Generate synthetic systems:

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025.csv \
  --meta data/site_meta.json \
  --out-dir outputs \
  --n-systems 30 \
  --seed 42
```

Outputs:
- Per-system CSVs at `outputs/system_<id>.csv`
- `outputs/systems_metadata.csv` for system definitions
