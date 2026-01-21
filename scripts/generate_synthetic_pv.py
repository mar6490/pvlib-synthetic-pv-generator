"""CLI for generating synthetic PV systems."""

from __future__ import annotations

import argparse

from pv_synth.generate import generate_systems


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic PV time series.")
    parser.add_argument("--weather", required=True, help="Path to weather CSV")
    parser.add_argument("--meta", required=True, help="Path to site metadata JSON")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--n-systems", type=int, default=30, help="Number of systems")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_systems(
        weather_path=args.weather,
        meta_path=args.meta,
        out_dir=args.out_dir,
        n_systems=args.n_systems,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
