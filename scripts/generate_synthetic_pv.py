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
from pv_synth.scenarios import parse_mix_weights, parse_n_by_type  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Generate synthetic PV time series.")
    parser.add_argument("--weather", required=True, help="Path to weather CSV")
    parser.add_argument("--meta", required=True, help="Path to site metadata JSON")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--n-systems", type=int, default=30, help="Number of systems")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
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

    args = parser.parse_args()
    try:
        args.mix_weights = parse_mix_weights(args.mix_weights)
        args.n_by_type = parse_n_by_type(args.n_by_type)
    except ValueError as exc:
        parser.error(str(exc))

    if args.n_systems <= 0 and args.n_by_type is None:
        parser.error("--n-systems must be > 0 unless --n-by-type is used.")

    return args


def main() -> None:
    """Entry point used when running the script directly."""
    args = parse_args()
    generate_systems(
        weather_path=args.weather,
        meta_path=args.meta,
        out_dir=args.out_dir,
        n_systems=args.n_systems,
        seed=args.seed,
        system_type=args.system_type,
        mix_weights=args.mix_weights,
        n_by_type=args.n_by_type,
    )


if __name__ == "__main__":
    main()
