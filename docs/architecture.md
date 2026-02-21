# Architecture

## Goal

Synthetic PV time series generator for controlled algorithm validation
and SDT-compatible analysis.

## High-Level Pipeline

Weather CSV → Time Parsing → Validation → Scenario Generation → pvlib
Simulation → CSV Export → Quicklook

## Core Modules

-   scripts/generate_synthetic_pv.py -- CLI entry point
-   src/pv_synth/io.py -- Weather & metadata loading
-   src/pv_synth/scenarios.py -- System sampling logic
-   src/pv_synth/pv_models.py -- pvlib-based simulation
-   src/pv_synth/generate.py -- Orchestration
-   src/pv_synth/quicklook.py -- Visualization

## Time Handling

-   Default: UTC+01:00 fixed offset
-   No DST usage
-   All timestamps tz-aware
-   No conversion to Europe/Berlin allowed

## pvlib Integration

-   Solar position via get_solarposition
-   DNI via irradiance.dni
-   POA via get_total_irradiance
-   DC via pvwatts_dc
-   AC via inverter.pvwatts

## Output Structure

outputs/ YYYY-MM-DD_HH-MM-SS/ system_XXX.csv systems_metadata.csv
quicklooks/

## Open TODOs

-   DNI NaN sanitization with clearsky constraint
-   Hard timezone assertions
-   Performance benchmark for \>100 systems
