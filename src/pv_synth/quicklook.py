"""Quicklook plotting utilities for generated PV system CSV files."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

_SYSTEM_ID_PATTERN = re.compile(r"system_(\d+)\.csv$")


def _import_matplotlib() -> tuple[Any, Any]:
    """Import matplotlib lazily so core package usage does not require it."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return matplotlib, plt
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Quicklook plotting requires matplotlib. Install it with 'pip install matplotlib'."
        ) from exc


def _system_sort_key(path: Path) -> tuple[int, str]:
    match = _SYSTEM_ID_PATTERN.search(path.name)
    if match:
        return int(match.group(1)), path.name
    return 10**9, path.name


def find_system_csvs(in_dir: Path, pattern: str = "system_*.csv") -> list[Path]:
    """Find and sort system CSV files in a directory."""
    files = [path for path in in_dir.glob(pattern) if path.is_file()]
    return sorted(files, key=_system_sort_key)


def load_system_csv(path: Path, tz: str = "UTC") -> pd.DataFrame:
    """Load one system CSV as a timezone-aware, time-indexed dataframe."""
    df = pd.read_csv(path)
    if "time" not in df.columns:
        raise ValueError(f"Missing required 'time' column in {path}")

    # Parse as UTC to avoid mixed-timezone parsing warnings and errors.
    timestamps = pd.to_datetime(df["time"], errors="coerce", utc=True)
    if timestamps.isna().all():
        raise ValueError(f"Could not parse any timestamps in {path}")

    index = pd.DatetimeIndex(timestamps)
    if tz != "UTC":
        index = index.tz_convert(tz)

    df = df.copy()
    df.index = index
    df.index.name = "time"
    return df.sort_index()


def _minute_of_day(index: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(index.hour * 60 + index.minute, index=index)


def make_ac_heatmap(df: pd.DataFrame, ax: Any, clip_quantile: float = 0.995) -> None:
    """Plot AC heatmap by day (x) and minute-of-day (y)."""
    _, plt = _import_matplotlib()

    if "ac_power_w" not in df.columns:
        raise ValueError("Missing required 'ac_power_w' column.")

    work = df[["ac_power_w"]].dropna().copy()
    if work.empty:
        ax.set_title("AC Heatmap (no data)")
        ax.set_axis_off()
        return

    work["day"] = work.index.normalize()
    work["minute_of_day"] = _minute_of_day(work.index)
    grid = work.pivot_table(
        index="minute_of_day",
        columns="day",
        values="ac_power_w",
        aggfunc="median",
    ).sort_index(axis=0).sort_index(axis=1)

    if grid.empty:
        ax.set_title("AC Heatmap (no data)")
        ax.set_axis_off()
        return

    vmax = float(np.nanquantile(work["ac_power_w"].to_numpy(), clip_quantile))
    vmax = vmax if vmax > 0 else 1.0

    im = ax.imshow(
        grid.to_numpy(),
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        vmin=0,
        vmax=vmax,
    )
    ax.set_title("AC Heatmap")
    ax.set_ylabel("Minute of day")

    y_ticks = [0, 360, 720, 1080, 1440]
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(["00:00", "06:00", "12:00", "18:00", "24:00"])

    n_cols = grid.shape[1]
    x_ticks = np.linspace(0, max(n_cols - 1, 0), num=min(6, n_cols), dtype=int)
    labels = [pd.Timestamp(grid.columns[idx]).strftime("%Y-%m") for idx in x_ticks]
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(labels, rotation=0)

    plt.colorbar(im, ax=ax, label="AC power [W]")


def make_median_profile(df: pd.DataFrame, ax: Any, normalize: bool = True) -> None:
    """Plot median daily profile and p10/p90 interval."""
    if "ac_power_w" not in df.columns:
        raise ValueError("Missing required 'ac_power_w' column.")

    work = df[["ac_power_w"]].dropna().copy()
    if work.empty:
        ax.set_title("Median Daily Profile (no data)")
        ax.set_axis_off()
        return

    work["minute_of_day"] = _minute_of_day(work.index)
    grouped = work.groupby("minute_of_day")["ac_power_w"]
    median = grouped.median()
    p10 = grouped.quantile(0.10)
    p90 = grouped.quantile(0.90)

    scale = 1.0
    if normalize:
        scale = float(np.nanquantile(work["ac_power_w"].to_numpy(), 0.99))
        if scale <= 0:
            scale = 1.0

    x = median.index.to_numpy()
    ax.plot(x, median.to_numpy() / scale, label="median", color="tab:blue")
    ax.fill_between(
        x,
        p10.to_numpy() / scale,
        p90.to_numpy() / scale,
        color="tab:blue",
        alpha=0.2,
        label="p10-p90",
    )

    ax.set_title("Median Daily Profile (AC)")
    ax.set_xlabel("Time of day")
    ax.set_ylabel("Normalized AC" if normalize else "AC power [W]")
    ax.set_xlim(0, 1440)
    ax.set_xticks([0, 360, 720, 1080, 1440])
    ax.set_xticklabels(["00:00", "06:00", "12:00", "18:00", "24:00"])
    ax.grid(alpha=0.2)


def make_week_overview(df: pd.DataFrame, ax: Any, days: int = 7) -> None:
    """Plot a representative 7-day AC timeseries around max-energy day."""
    if "ac_power_w" not in df.columns:
        raise ValueError("Missing required 'ac_power_w' column.")

    work = df[["ac_power_w"]].copy()
    if work.dropna().empty:
        ax.set_title("Representative Week (no data)")
        ax.set_axis_off()
        return

    daily_energy = work["ac_power_w"].fillna(0).resample("D").sum()
    if daily_energy.empty:
        ax.set_title("Representative Week (no data)")
        ax.set_axis_off()
        return

    center_day = daily_energy.idxmax().normalize()
    half = days // 2
    start = center_day - pd.Timedelta(days=half)
    end = center_day + pd.Timedelta(days=half + 1)

    window = work.loc[(work.index >= start) & (work.index < end)]
    if window.empty:
        ax.set_title("Representative Week (no data)")
        ax.set_axis_off()
        return

    ax.plot(window.index, window["ac_power_w"], color="tab:orange", linewidth=1.0)
    ax.set_title("Representative 7-Day AC Window")
    ax.set_xlabel("Time")
    ax.set_ylabel("AC power [W]")
    ax.grid(alpha=0.2)


def plot_system_quicklook(
    system_csv: Path,
    out_png: Path,
    normalize: bool = True,
    overwrite: bool = False,
    tz: str = "UTC",
) -> bool:
    """Create a three-panel quicklook PNG for one system file.

    Returns True if file was written, False if skipped because file exists.
    """
    _, plt = _import_matplotlib()

    if out_png.exists() and not overwrite:
        return False

    df = load_system_csv(system_csv, tz=tz)
    if "ac_power_w" not in df.columns:
        raise ValueError(f"Missing required 'ac_power_w' column in {system_csv}")

    out_png.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(3, 1, figsize=(14, 12), constrained_layout=True)
    make_ac_heatmap(df, axes[0])
    make_median_profile(df, axes[1], normalize=normalize)
    make_week_overview(df, axes[2], days=7)

    fig.suptitle(system_csv.stem, fontsize=14)
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return True


def plot_quicklooks_for_dir(
    in_dir: Path,
    out_dir: Path,
    max_systems: int | None = None,
    normalize: bool = True,
    overwrite: bool = False,
    fmt: str = "png",
    tz: str = "UTC",
) -> dict[str, int]:
    """Generate quicklook files for a directory of system CSVs."""
    if fmt != "png":
        raise ValueError("Only 'png' format is supported currently.")

    system_csvs = find_system_csvs(in_dir)
    if max_systems is not None:
        system_csvs = system_csvs[:max_systems]

    stats = {"found": len(system_csvs), "plotted": 0, "skipped": 0, "errors": 0}

    for system_csv in system_csvs:
        out_file = out_dir / f"{system_csv.stem}_quicklook.{fmt}"
        try:
            written = plot_system_quicklook(
                system_csv,
                out_file,
                normalize=normalize,
                overwrite=overwrite,
                tz=tz,
            )
            if written:
                stats["plotted"] += 1
            else:
                stats["skipped"] += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[quicklook] warning: could not process {system_csv}: {exc}")
            stats["errors"] += 1

    return stats
