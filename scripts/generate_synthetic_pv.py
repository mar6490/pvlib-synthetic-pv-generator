"""CLI for generating synthetic PV systems.

This script parses command-line arguments and calls the generation pipeline.
It also adds the local ``src`` directory to ``sys.path`` so the package can be
used without installing the project (helpful on Windows).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from pv_synth.generate import generate_systems  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Generate synthetic PV time series.")
    parser.add_argument("--weather", required=True, help="Path to weather CSV")
    parser.add_argument("--meta", required=True, help="Path to site metadata JSON")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--n-systems", type=int, default=30, help="Number of systems")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    return parser.parse_args()


def main() -> None:
    """Entry point used when running the script directly."""
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
