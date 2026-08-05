#!/usr/bin/env python3
"""Stage 2 — selectively extract the partitions the study needs.

The selection rule lives in ``conf/experiment.yaml`` and was fixed before any
predictability was measured (see the ``extraction.select`` block). In short:
the six small plugins are taken for the whole campaign because they cost only
a few GiB in total, while IPMI and Ganglia are taken for the sampled months
only. Within a selected (plugin, month), *every* metric is extracted, so no
metric is ever chosen for how it behaves.

Free space is re-checked throughout; the run aborts rather than filling the
filesystem.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.io.archive import (  # noqa: E402
    extract_partitions,  # noqa: E402
    find_archives,
    month_from_archive_name,
)
from hsf.io.disk import dir_size_gb, free_gb  # noqa: E402


def load_conf(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", type=Path, default=paths.RAW_DIR)
    ap.add_argument("--dest", type=Path, default=paths.INTERIM)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--min-free-gb", type=float, default=None)
    ap.add_argument("--dry-run", action="store_true", help="report the plan, extract nothing")
    args = ap.parse_args()

    conf = load_conf(args.conf)
    extraction = conf["extraction"]
    min_free = args.min_free_gb if args.min_free_gb is not None else extraction["min_free_gb"]
    max_interim = extraction["max_interim_gb"]
    sampled_months = set(conf["months"])
    take_all_months = set(extraction["select"]["all_months"])
    take_sampled = set(extraction["select"]["sampled_months"])

    def wanted(part, month: str) -> bool:
        family = part.plugin_family
        if family in take_all_months:
            return True
        if family in take_sampled:
            return month in sampled_months
        return False

    archives = find_archives(args.raw_dir)
    print(f"{len(archives)} archives in {args.raw_dir}")
    print(f"free now: {free_gb(args.dest):.1f} GiB · safety margin: {min_free} GiB")
    print(f"interim ceiling: {max_interim} GiB · dest: {args.dest}\n")

    if args.dry_run:
        import pandas as pd

        inv = pd.read_parquet(paths.DERIVED / "inventory.parquet")
        sel = inv[
            inv.plugin.isin(take_all_months)
            | (inv.plugin.isin(take_sampled) & inv.archive_month.isin(sampled_months))
        ]
        print("--- dry run: selection ---")
        print((sel.groupby("plugin").size_bytes.sum() / 1024**3).round(2).to_string())
        print(f"\n{len(sel):,} partitions, {sel.size_bytes.sum() / 1024**3:.2f} GiB total")
        return

    total = 0
    for archive in archives:
        month = month_from_archive_name(archive)
        used = dir_size_gb(args.dest)
        if used > max_interim:
            raise SystemExit(
                f"data/interim is {used:.1f} GiB, above the {max_interim} GiB ceiling. "
                f"Stopping before {month}."
            )
        written = extract_partitions(
            archive,
            args.dest,
            predicate=lambda p, m=month: wanted(p, m),
            min_free_gb=min_free,
        )
        total += len(written)
        if written:
            print(
                f"  {month}: {len(written):4d} partitions "
                f"(interim now {dir_size_gb(args.dest):.1f} GiB, "
                f"{free_gb(args.dest):.0f} GiB free)",
                flush=True,
            )

    print(f"\nExtracted {total:,} partitions · interim {dir_size_gb(args.dest):.1f} GiB")


if __name__ == "__main__":
    main()
