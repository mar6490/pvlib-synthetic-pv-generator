"""CLI runner for quicklook plots from existing system CSV files."""

from __future__ import annotations

import argparse
from datetime import datetime
import glob
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from pv_synth.quicklook import plot_system_quicklook, plot_quicklooks_for_dir  # noqa: E402

SYSTEM_ID_PATTERN = re.compile(r"system_(\d+)\.csv$")


def _system_sort_key(path: Path) -> tuple[int, str]:
    match = SYSTEM_ID_PATTERN.search(path.name)
    if match:
        return int(match.group(1)), path.name
    return 10**9, path.name


def _timestamped_quicklook_dir(parent: Path) -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return parent / f"quicklooks_{ts}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate quicklook plots for system CSV outputs.")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--in-dir", default=None, help="Directory containing system_*.csv files")
    source_group.add_argument("--glob", dest="glob_pattern", default=None, help="Glob pattern for system CSV files")

    parser.add_argument("--out-dir", default=None, help="Output directory for quicklook images")
    parser.add_argument("--max-systems", type=int, default=None, help="Maximum number of systems to plot")
    parser.add_argument("--normalize", dest="normalize", action="store_true", default=True)
    parser.add_argument("--no-normalize", dest="normalize", action="store_false")
    parser.add_argument("--format", choices=["png"], default="png")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing quicklook files")
    parser.add_argument("--tz", default="UTC", help="Timezone for plotting (converted after UTC parsing)")

    args = parser.parse_args()
    if args.max_systems is not None and args.max_systems <= 0:
        parser.error("--max-systems must be > 0")
    return args


def _run_glob_mode(args: argparse.Namespace) -> dict[str, int]:
    csv_paths = [Path(path) for path in sorted(glob.glob(args.glob_pattern), key=lambda p: _system_sort_key(Path(p)))]
    if args.max_systems is not None:
        csv_paths = csv_paths[: args.max_systems]

    out_dir = Path(args.out_dir) if args.out_dir else _timestamped_quicklook_dir(Path("."))
    stats = {"found": len(csv_paths), "plotted": 0, "skipped": 0, "errors": 0}

    for csv_path in csv_paths:
        out_png = out_dir / f"{csv_path.stem}_quicklook.{args.format}"
        try:
            written = plot_system_quicklook(
                csv_path,
                out_png,
                normalize=args.normalize,
                overwrite=args.overwrite,
                tz=args.tz,
            )
            if written:
                stats["plotted"] += 1
            else:
                stats["skipped"] += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[quicklook] warning: could not process {csv_path}: {exc}")
            stats["errors"] += 1

    return stats


def main() -> None:
    args = parse_args()

    if args.in_dir:
        in_dir = Path(args.in_dir)
        out_dir = Path(args.out_dir) if args.out_dir else _timestamped_quicklook_dir(in_dir)
        stats = plot_quicklooks_for_dir(
            in_dir=in_dir,
            out_dir=out_dir,
            max_systems=args.max_systems,
            normalize=args.normalize,
            overwrite=args.overwrite,
            fmt=args.format,
            tz=args.tz,
        )
    else:
        stats = _run_glob_mode(args)

    print(
        "Quicklook summary: "
        f"found={stats['found']}, plotted={stats['plotted']}, skipped={stats['skipped']}, errors={stats['errors']}"
    )


if __name__ == "__main__":
    main()
