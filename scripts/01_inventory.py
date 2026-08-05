#!/usr/bin/env python3
"""Stage 1 — inventory every partition of every monthly archive.

Walks the tar headers of all 31 monthly archives and records what exists:
which plugins, which metrics, in which months, at what size. No data is
extracted and no disk is consumed.

This is the first quantitative answer to "what is actually in ExaData, and did
it stay the same?" — and it does not, which is why OI-2 exists.

Output: ``data/derived/inventory.parquet`` (committed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.io.archive import find_archives, iter_partitions, month_from_archive_name  # noqa: E402


def build_inventory(raw_dir: Path, months: list[str] | None) -> pd.DataFrame:
    archives = find_archives(raw_dir, months)
    if not archives:
        raise SystemExit(f"No .tar archives found in {raw_dir}")

    rows: list[dict] = []
    for archive in archives:
        month = month_from_archive_name(archive)
        n_before = len(rows)
        for part in iter_partitions(archive):
            rows.append(
                {
                    "year_month": part.year_month,
                    "archive_month": month,
                    "plugin": part.plugin_family,
                    "metric": part.metric,
                    "member": part.member,
                    "size_bytes": part.size_bytes,
                }
            )
        n = len(rows) - n_before
        size_gb = sum(r["size_bytes"] for r in rows[n_before:]) / 1024**3
        print(f"  {month}: {n:5d} partitions, {size_gb:8.2f} GiB", flush=True)

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("Inventory is empty — check the archive layout.")
    return df.sort_values(["archive_month", "plugin", "metric"]).reset_index(drop=True)


def summarise(df: pd.DataFrame) -> None:
    print("\n=== partitions per plugin per month ===")
    pivot = df.pivot_table(
        index="archive_month", columns="plugin", values="metric", aggfunc="nunique", fill_value=0
    )
    print(pivot.to_string())

    print("\n=== total size per plugin (GiB) ===")
    size = df.groupby("plugin")["size_bytes"].sum().sort_values(ascending=False) / 1024**3
    print(size.round(2).to_string())

    print("\n=== metric stability across months ===")
    months = df["archive_month"].nunique()
    per_metric = df.groupby(["plugin", "metric"])["archive_month"].nunique()
    always = (per_metric == months).sum()
    print(f"{len(per_metric)} distinct (plugin, metric) pairs across {months} months")
    print(f"{always} present in every month ({always / len(per_metric):.1%})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", type=Path, default=paths.RAW_DIR)
    ap.add_argument("--months", nargs="*", default=None, help="default: every archive found")
    ap.add_argument("--out", type=Path, default=paths.DERIVED / "inventory.parquet")
    args = ap.parse_args()

    paths.ensure_output_dirs()
    print(f"Scanning archives in {args.raw_dir} (headers only, no extraction)")
    df = build_inventory(args.raw_dir, args.months)
    summarise(df)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False, compression="zstd")
    print(f"\nWrote {len(df):,} rows to {args.out} ({args.out.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
