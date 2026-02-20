# Synthetic PV Profile Generator (pvlib-based)

This project creates **synthetic photovoltaic (PV) power profiles** from real weather measurements.

In simple terms:
- You provide measured weather data (sunlight, diffuse light, air temperature, wind).
- The tool simulates many plausible home PV systems.
- It writes time series files with simulated DC and AC power.

> Important: synthetic shading has been removed. The generator now creates only systems **without synthetic obstruction shading**.

---

## Who this is for

- Energy analysts who need many realistic PV profiles for studies.
- Data scientists who need simulation data for forecasting or clustering.
- Non-programmers who want a reproducible way to create scenario data.

You do **not** need to write Python code to use it. The command line script is enough.

---

## What the application does (high-level)

For each system, the pipeline does the following:

1. Reads and validates your weather file.
2. Reads site metadata (latitude, longitude, timezone).
3. Randomly creates a PV system configuration (size, orientation, tilt, losses, inverter sizing).
4. Calculates sun position at every timestamp.
5. Converts weather irradiance to module-plane irradiance.
6. Computes DC power and then AC power.
7. Writes one CSV per system + one metadata CSV.

---

## Quick start

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Run generation

```bash
python scripts/generate_synthetic_pv.py \
  --weather data/wetter-htw-2025-utc.csv \
  --meta data/site_meta.json \
  --out-dir outputs \
  --n-systems 30 \
  --seed 42
```

### 3) Check outputs

- `outputs/system_001.csv`, `outputs/system_002.csv`, ...
- `outputs/systems_metadata.csv`

---

## Input files

### Weather CSV (strict format)

The weather file must be semicolon-separated and must use exactly this header:

```text
time;ghi;dhi;t_luft;v_wind
```

Rules:
- Separator: `;`
- Time format: `YYYY-MM-DD HH:MM:SS±HH:MM` (offset required)
- Resolution: continuous 15-minute steps
- Required columns:
  - `time`: timestamp with UTC offset
  - `ghi`: global horizontal irradiance
  - `dhi`: diffuse horizontal irradiance
  - `t_luft`: air temperature
  - `v_wind`: wind speed

Example:

```csv
time;ghi;dhi;t_luft;v_wind
2025-01-01 00:00:00+01:00;0;0;1.5;6.89
2025-01-01 00:15:00+01:00;0;0;1.45;7.45
2025-01-01 00:30:00+01:00;0;0;1.43;7.05
```

### Site metadata JSON

Required keys:

```json
{
  "lat": 52.5,
  "lon": 13.4,
  "tz": "Europe/Berlin"
}
```

Optional: `altitude`

---

## Output files

### 1) Per-system power profile (`system_<id>.csv`)

Columns:
- `time`: timestamp
- `dc_power_w`: simulated DC power (W)
- `ac_power_w`: simulated AC power (W)

### 2) Scenario metadata (`systems_metadata.csv`)

Columns:
- `system_id`
- `system_type` (`south`, `east`, `west`, `east-west`)
- `kwp`
- `tilt`
- `azimuth` (`90/270` for east-west split systems)
- `dc_ac_ratio`
- `losses`

---

## Concept explained for non-programmers

Think of this tool as a **virtual PV lab**.

- The weather file is the “outside world”.
- A scenario is a “virtual roof installation”.
- The physical model calculates how much sunlight reaches the modules and how much electrical power comes out.

### Why random scenarios?

Real neighborhoods contain many different roof geometries and system sizes.
The generator samples realistic ranges so your dataset contains natural diversity.

### What is modeled physically?

- **Sun position**: where the sun is in the sky at each timestamp.
- **Irradiance transposition**: converts horizontal sunlight to tilted module sunlight.
- **Cell temperature**: warmer modules produce less power.
- **DC output**: calculated with PVWatts DC model.
- **AC output**: inverter efficiency and clipping with PVWatts inverter model.

### East-west systems

East-west is represented as two sub-arrays:
- one facing east (90°),
- one facing west (270°),
- each gets half of total kWp,
- DC outputs are summed and converted to AC.

### Losses

The `losses` factor is a simple aggregate percentage for typical effects such as cable losses, mismatch, and soiling.

---

## Code structure (architecture)

- `scripts/generate_synthetic_pv.py`
  - Command line entry point.
- `src/pv_synth/io.py`
  - Input loading and strict validation.
- `src/pv_synth/scenarios.py`
  - Random system scenario generation.
- `src/pv_synth/pv_models.py`
  - Physical simulation with pvlib.
- `src/pv_synth/generate.py`
  - End-to-end orchestration and CSV writing.

---

## Reproducibility

Use `--seed` to get deterministic random scenarios.
Same input + same seed = same synthetic systems.

---

## Notes and limitations

- The tool does not create synthetic weather; it uses your measured weather input.
- The model is simplified (PVWatts-based) and intended for realistic synthetic datasets, not detailed plant engineering.
- Synthetic shading is intentionally disabled/removed.

---

## Run tests

```bash
pytest
```

