#!/usr/bin/env python3
"""Stage 3 — build the per-series census from the extracted partitions.

One row per ``(plugin, metric, entity, month)``: how many samples, over what
span, at what cadence, how irregular that cadence was, how much is missing,
what the value range and quantisation step are.

The census is *descriptive only*. It deliberately contains no predictability
measure and no model, so that the later claim "predictability differs by signal
family" cannot be an artefact of having peeked.

Work is sharded per partition file into ``data/interim/_census/`` so the run is
resumable; the shards are concatenated into ``data/derived/manifest.parquet``.
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.io.census import census_for_table  # noqa: E402
from hsf.io.schema import entity_columns, is_timeseries_plugin  # noqa: E402

SHARD_DIR = paths.INTERIM / "_census"


def parse_partition_path(path: Path) -> tuple[str, str, str]:
    """``.../year_month=21-08/plugin=ipmi_pub/metric=ambient/a_0.parquet``."""
    parts = {p.split("=", 1)[0]: p.split("=", 1)[1] for p in path.parts if "=" in p}
    plugin = parts.get("plugin", "")
    if plugin.endswith("_pub"):
        plugin = plugin[:-4]
    return parts.get("year_month", ""), plugin, parts.get("metric", "")


def shard_path(year_month: str, plugin: str, metric: str) -> Path:
    safe = metric.replace("/", "_")
    return SHARD_DIR / f"{year_month}__{plugin}__{safe}.parquet"


def process_one(path_str: str) -> tuple[str, int, str]:
    """Census one partition file. Returns (label, n_series, status)."""
    path = Path(path_str)
    year_month, plugin, metric = parse_partition_path(path)
    label = f"{year_month}/{plugin}/{metric}"
    out = shard_path(year_month, plugin, metric)
    if out.exists():
        return label, -1, "cached"

    try:
        schema = pq.read_schema(path)
        if "value" not in schema.names or "timestamp" not in schema.names:
            return label, 0, "not-a-series"

        # Read only the columns the census needs. Ganglia partitions exceed
        # 100M rows, so pulling unused tag columns would dominate memory.
        wanted = ["timestamp", "value", *entity_columns(plugin, list(schema.names))]
        table = pq.read_table(path, columns=wanted)
        census = census_for_table(table, plugin=plugin, metric=metric, year_month=year_month)
        del table
    except Exception as exc:  # noqa: BLE001 - one bad partition must not kill the run
        return label, 0, f"error: {type(exc).__name__}: {exc}"

    out.parent.mkdir(parents=True, exist_ok=True)
    census.to_parquet(out, index=False, compression="zstd")
    return label, len(census), "ok"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--interim", type=Path, default=paths.INTERIM)
    ap.add_argument("--out", type=Path, default=paths.MANIFEST)
    # Worker count is set by memory, not by core count.
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument(
        "--big-bytes",
        type=int,
        default=60 * 1024**2,
        help="partitions at or above this size are processed one at a time",
    )
    ap.add_argument("--plugins", nargs="*", default=None, help="restrict to these plugin families")
    args = ap.parse_args()

    paths.ensure_output_dirs()
    SHARD_DIR.mkdir(parents=True, exist_ok=True)

    files = [p for p in args.interim.rglob("*.parquet") if "_census" not in p.parts]
    todo: list[str] = []
    for p in files:
        _, plugin, _ = parse_partition_path(p)
        if not plugin or not is_timeseries_plugin(plugin):
            continue
        if args.plugins and plugin not in args.plugins:
            continue
        todo.append(str(p))

    print(f"{len(todo):,} partition files to census (workers={args.workers})")
    started = time.time()
    done = errors = cached = 0

    # This machine also hosts Kubernetes workloads, and an earlier attempt was
    # OOM-killed and took an unrelated pod down with it. Partitions are
    # therefore split by size: the large ones are processed one at a time, and
    # only the small ones run in parallel.
    big = sorted((p for p in todo if Path(p).stat().st_size >= args.big_bytes), reverse=True)
    small = [p for p in todo if Path(p).stat().st_size < args.big_bytes]
    print(
        f"  {len(big):,} large partitions (>= {args.big_bytes / 1024**2:.0f} MiB) run serially\n"
        f"  {len(small):,} small partitions run with {args.workers} workers",
        flush=True,
    )

    def run(batch: list[str], workers: int) -> None:
        nonlocal done, errors, cached
        if not batch:
            return
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(process_one, p): p for p in batch}
            for fut in as_completed(futures):
                label, _n, status = fut.result()
                done += 1
                if status == "cached":
                    cached += 1
                elif status != "ok":
                    errors += 1
                    print(f"  !! {label}: {status}", flush=True)
                if done % 250 == 0 or (workers == 1 and done % 25 == 0):
                    rate = done / (time.time() - started)
                    print(
                        f"  {done:,}/{len(todo):,} ({rate:.1f}/s, {cached} cached, "
                        f"{errors} errors)",
                        flush=True,
                    )

    run(big, 1)
    run(small, args.workers)

    shards = sorted(SHARD_DIR.glob("*.parquet"))
    print(f"\nConcatenating {len(shards):,} shards")
    manifest = pd.concat((pd.read_parquet(s) for s in shards), ignore_index=True)
    manifest = manifest.sort_values(["plugin", "metric", "year_month", "entity"]).reset_index(
        drop=True
    )
    manifest.to_parquet(args.out, index=False, compression="zstd")

    size_mb = args.out.stat().st_size / 1024**2
    print(f"Wrote {len(manifest):,} series to {args.out} ({size_mb:.1f} MiB)")
    print(f"\nseries per plugin:\n{manifest.plugin.value_counts().to_string()}")
    print(f"\nelapsed: {time.time() - started:.0f}s · errors: {errors}")


if __name__ == "__main__":
    main()
