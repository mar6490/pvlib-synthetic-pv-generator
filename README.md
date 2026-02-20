# Synthetic PV Profile Generator (pvlib-based)

This project creates synthetic PV power profiles from measured weather data.

## Key point
Synthetic shading is removed. The generator produces unshaded systems only.

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate profiles:

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025-utc.csv \
  --meta data/site_meta.json \
  --out-dir outputs \
  --n-systems 30 \
  --seed 42
```

## New system-type controls

### `--system-type`
Controls which architecture is generated:
- `single`: only single-plane systems
- `east-west`: only two-plane east-west systems
- `mixed`: random mix of single + east-west (default)

### `--mix-weights`
Used in `mixed` mode. Format:

```text
single=0.7,east-west=0.3
```

Rules:
- keys only: `single`, `east-west`
- values must be non-negative
- sum must equal 1.0

Default: `single=0.7,east-west=0.3`

### `--n-by-type`
Optional explicit counts, overrides `--n-systems` and `--mix-weights`.

Format:

```text
east-west=20,single=10
```

Rules:
- keys only: `single`, `east-west`
- values must be integers >= 0
- total must be > 0

## Examples

20 east-west systems:

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025-utc.csv \
  --meta data/site_meta.json \
  --out-dir outputs_ew \
  --n-systems 20 \
  --system-type east-west \
  --seed 42
```

Only single-plane systems:

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025-utc.csv \
  --meta data/site_meta.json \
  --out-dir outputs_single \
  --n-systems 20 \
  --system-type single \
  --seed 42
```

Mixed 50/50:

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025-utc.csv \
  --meta data/site_meta.json \
  --out-dir outputs_mix \
  --n-systems 40 \
  --system-type mixed \
  --mix-weights "single=0.5,east-west=0.5" \
  --seed 42
```

Explicit counts:

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025-utc.csv \
  --meta data/site_meta.json \
  --out-dir outputs_counts \
  --n-by-type "east-west=20,single=10" \
  --seed 42
```

## Input weather format

Strict CSV format:
- separator `;`
- header exactly: `time;ghi;dhi;t_luft;v_wind`
- timestamp format: `YYYY-MM-DD HH:MM:SS±HH:MM`
- fixed 15-minute resolution

## Output

Per system file: `system_<id>.csv`
- `time`
- `dc_power_w`
- `ac_power_w`

Metadata file: `systems_metadata.csv`
- `system_id`
- `system_type` (`single` or `east-west`)
- `plane_type` (`south`/`east`/`west` for single; empty for east-west)
- `kwp_total`
- `kwp` (alias to `kwp_total`)
- `kwp_east`, `kwp_west` (filled for east-west)
- `tilt`
- `azimuth` (single scalar or `90/270` for east-west)
- `azimuth_east`, `azimuth_west` (filled for east-west)
- `dc_ac_ratio`
- `losses`

## Reproducibility

Use `--seed` for deterministic generation.
Same input + same seed + same CLI options => same type distribution and parameter samples.

## Tests

```bash
pytest
```
