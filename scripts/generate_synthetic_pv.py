"""CLI for generating synthetic PV systems."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from pv_synth.generate import generate_systems  # noqa: E402
from pv_synth.quicklook import plot_quicklooks_for_dir  # noqa: E402
from pv_synth.scenarios import parse_mix_weights, parse_n_by_type, parse_tilt_range  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Generate synthetic PV time series.")
    parser.add_argument("--weather", required=True, help="Path to weather CSV")
    parser.add_argument("--meta", required=True, help="Path to site metadata JSON")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--n-systems", type=int, default=30, help="Number of systems")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--generation-mode",
        choices=["random", "grid"],
        default="random",
        help="Scenario generation mode",
    )
    parser.add_argument(
        "--scenario-file",
        default=None,
        help="Path to scenario YAML file (required for --generation-mode grid)",
    )

    parser.add_argument(
        "--system-type",
        choices=["single", "east-west", "mixed"],
        default="mixed",
        help="Which system types to generate",
    )
    parser.add_argument(
        "--mix-weights",
        default="single=0.7,east-west=0.3",
        help="Weights for mixed mode, e.g. single=0.7,east-west=0.3",
    )
    parser.add_argument(
        "--n-by-type",
        default=None,
        help="Explicit counts override, e.g. east-west=20,single=10",
    )
    parser.add_argument(
        "--ew-azimuth-mode",
        choices=["fixed_cardinal", "jittered_180"],
        default="fixed_cardinal",
        help="East-west azimuth mode",
    )
    parser.add_argument(
        "--roof-type",
        choices=["flat", "pitched", "mixed"],
        default="mixed",
        help="Roof type model for east-west systems",
    )
    parser.add_argument(
        "--ew-azimuth-jitter-deg",
        type=float,
        default=None,
        help="Override jitter half-width (degrees) for jittered_180 mode",
    )
    parser.add_argument(
        "--ew-tilt-range-deg",
        default=None,
        help="Override east-west tilt range as 'min,max'",
    )

    parser.add_argument(
        "--time-mode",
        choices=["dst", "fixed_offset"],
        default="fixed_offset",
        help="Time interpretation mode (fixed_offset is project standard; dst is deprecated)",
    )
    parser.add_argument(
        "--fixed-offset-minutes",
        type=int,
        default=60,
        help="Fixed timezone offset in minutes when --time-mode fixed_offset",
    )
    parser.add_argument(
        "--weather-timestamp",
        choices=["with_offset", "naive"],
        default="naive",
        help="Timestamp format in weather CSV",
    )
    parser.add_argument(
        "--output-timestamp",
        choices=["with_offset", "naive"],
        default="with_offset",
        help="Output CSV timestamp format: with_offset keeps timezone offset, naive drops tz info after fixed-offset conversion",
    )

    parser.add_argument(
        "--noise-model",
        choices=["none", "gaussian"],
        default="none",
        help="Optional AC-only noise model",
    )
    parser.add_argument(
        "--noise-sigma-rel",
        type=float,
        default=0.02,
        help="Relative sigma for gaussian AC noise",
    )

    parser.add_argument(
        "--quicklook",
        action="store_true",
        help="Generate quicklook plots after successful generation",
    )
    parser.add_argument(
        "--quicklook-dir",
        default=None,
        help="Optional directory for quicklook images (defaults to <run-dir>/quicklooks)",
    )

    args = parser.parse_args()
    try:
        args.mix_weights = parse_mix_weights(args.mix_weights)
        args.n_by_type = parse_n_by_type(args.n_by_type)
        args.ew_tilt_range_deg = parse_tilt_range(args.ew_tilt_range_deg)
    except ValueError as exc:
        parser.error(str(exc))

    if args.generation_mode == "grid" and not args.scenario_file:
        parser.error("--scenario-file is required when --generation-mode=grid.")
    if args.n_systems <= 0 and args.n_by_type is None and args.generation_mode == "random":
        parser.error("--n-systems must be > 0 unless --n-by-type is used.")
    if args.ew_azimuth_jitter_deg is not None and args.ew_azimuth_jitter_deg < 0:
        parser.error("--ew-azimuth-jitter-deg must be >= 0.")
    if args.noise_sigma_rel < 0:
        parser.error("--noise-sigma-rel must be >= 0.")

    return args


def main() -> None:
    """Entry point used when running the script directly."""
    args = parse_args()
    run_dir = generate_systems(
        weather_path=args.weather,
        meta_path=args.meta,
        out_dir=args.out_dir,
        n_systems=args.n_systems,
        seed=args.seed,
        generation_mode=args.generation_mode,
        scenario_file=args.scenario_file,
        system_type=args.system_type,
        mix_weights=args.mix_weights,
        n_by_type=args.n_by_type,
        ew_azimuth_mode=args.ew_azimuth_mode,
        roof_type=args.roof_type,
        ew_azimuth_jitter_deg=args.ew_azimuth_jitter_deg,
        ew_tilt_range_deg=args.ew_tilt_range_deg,
        time_mode=args.time_mode,
        fixed_offset_minutes=args.fixed_offset_minutes,
        weather_timestamp=args.weather_timestamp,
        noise_model=args.noise_model,
        noise_sigma_rel=args.noise_sigma_rel,
        output_timestamp=args.output_timestamp,
    )

    if args.quicklook:
        ql_dir = Path(args.quicklook_dir) if args.quicklook_dir else run_dir / "quicklooks"
        stats = plot_quicklooks_for_dir(
            in_dir=run_dir,
            out_dir=ql_dir,
            normalize=True,
            overwrite=False,
            fmt="png",
        )
        print(
            "Quicklook summary: "
            f"found={stats['found']}, plotted={stats['plotted']}, skipped={stats['skipped']}, errors={stats['errors']}"
        )


if __name__ == "__main__":
    main()
