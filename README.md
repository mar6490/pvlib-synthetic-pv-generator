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


## Timestamped output structure

Generation now writes into a timestamped run folder.

Example:
- Input `--out-dir outputs`
- Effective run folder: `outputs/YYYY-MM-DD_HH-MM-SS/`

If `--out-dir` already points to a timestamped run directory (for example `outputs/2026-02-20_16-12-33`), no extra nested timestamp folder is created.

## System-type controls

### `--system-type`
- `single`: only single-plane systems
- `east-west`: only two-plane east-west systems
- `mixed`: random mix (default)

### `--mix-weights`
Used in `mixed` mode. Format:

```text
single=0.7,east-west=0.3
```

Rules:
- keys only `single`, `east-west`
- non-negative values
- sum must equal 1.0

### `--n-by-type`
Optional explicit counts. Overrides `--n-systems` and `--mix-weights`.

```text
east-west=20,single=10
```

## East-west parametrization (new)

### `--ew-azimuth-mode`
- `fixed_cardinal` (default, backwards compatible): east/west azimuths fixed at 90/270
- `jittered_180` (realistic): east azimuth is jittered around 90°, west is always exactly 180° apart

### `--roof-type`
- `flat`
- `pitched`
- `mixed` (default; per east-west system sampled 50/50 flat vs pitched)

### Optional east-west overrides
- `--ew-azimuth-jitter-deg X`
  - overrides default jitter width in `jittered_180` mode (`delta ~ Uniform(-X, +X)`)
- `--ew-tilt-range-deg "a,b"`
  - overrides east-west tilt sampling (`tilt ~ Uniform(a,b)`)

Default east-west behavior without overrides:
- `fixed_cardinal`: 90/270
- `jittered_180` + roof type `flat`: jitter ±15°, tilt 5..20°
- `jittered_180` + roof type `pitched`: jitter ±30°, tilt 20..55°

> These east-west options are only relevant for east-west systems.

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

Realistic east-west parametrization:

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025-utc.csv \
  --meta data/site_meta.json \
  --out-dir outputs_ew_real \
  --n-systems 20 \
  --system-type east-west \
  --ew-azimuth-mode jittered_180 \
  --roof-type mixed \
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
- `plane_type` (`south`/`east`/`west` for single)
- `roof_type` (for east-west)
- `ew_azimuth_mode` (for east-west)
- `lat`, `lon` (included for every system)
- `kwp_total`
- `kwp` (alias to `kwp_total`)
- `kwp_east`, `kwp_west` (east-west)
- `tilt`
- `azimuth`
- `azimuth_east`, `azimuth_west` (east-west)
- `dc_ac_ratio`
- `losses`


## Quicklook plots

You can create AC-only quicklook figures for existing generated systems (independent from generation):

```bash
python scripts/quicklook_systems.py --in-dir outputs/2026-02-20_16-45-12 --tz Europe/Berlin
```


Default standalone quicklook output for `--in-dir` is also timestamped:
- `--in-dir outputs/2026-02-20_16-45-12`
- output: `outputs/2026-02-20_16-45-12/quicklooks_YYYY-MM-DD_HH-MM-SS/`

If you pass `--out-dir`, it is used directly (created if needed) without adding another timestamp subfolder.

Times are parsed robustly with UTC (`pd.to_datetime(..., utc=True)`) and then optionally converted for plotting via `--tz` (default: `UTC`).

Or via glob:

```bash
python scripts/quicklook_systems.py --glob "outputs/system_*.csv" --out-dir outputs/quicklooks
```

Each system gets one PNG with 3 panels:
- AC heatmap (date vs minute-of-day)
- Median daily AC profile (optionally normalized)
- Representative 7-day AC window around max-energy day

Optional convenience hook during generation:

```bash
python scripts/generate_synthetic_pv.py ... --quicklook
# quicklooks will be written to <run_dir>/quicklooks/
```

Use `--quicklook-dir` to override the default output folder (`<run-dir>/quicklooks`).

## Reproducibility

Use `--seed` for deterministic generation.
Same input + same seed + same CLI options => same type distribution and sampled parameters.

## Tests

```bash
pytest
```
