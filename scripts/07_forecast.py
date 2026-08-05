#!/usr/bin/env python3
"""Stage 7 — run the tiered forecast benchmark over the sampled series.

Produces one row per (series, model, horizon, origin). Nothing is averaged
here: aggregation is an analysis decision and a mean taken too early cannot be
undone.

The seasonal period is fixed per series from its own cadence — a day expressed
in steps — which was decided before any skill was measured (OI-5). The
non-seasonal robustness check at m=1 is run alongside, not instead.

Output: ``data/derived/skill.parquet`` (committed).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.forecast.harness import iter_evaluations  # noqa: E402
from hsf.forecast.models import build_suite  # noqa: E402
from hsf.io.series import load_series  # noqa: E402

SHARD_DIR = paths.INTERIM / "_skill"


def partition_path(interim: Path, year_month: str, plugin: str, metric: str) -> Path:
    return (
        interim
        / f"year_month={year_month}"
        / f"plugin={plugin}_pub"
        / f"metric={metric}"
        / "a_0.parquet"
    )


def shard_path(year_month: str, plugin: str, metric: str) -> Path:
    return SHARD_DIR / f"{year_month}__{plugin}__{metric.replace('/', '_')}.parquet"


def run_partition(job: dict) -> tuple[str, int, str]:
    """Benchmark every sampled series in one partition."""
    year_month, plugin, metric = job["year_month"], job["plugin"], job["metric"]
    label = f"{year_month}/{plugin}/{metric}"
    out = shard_path(year_month, plugin, metric)
    if out.exists():
        return label, -1, "cached"

    path = Path(job["path"])
    if not path.exists():
        return label, 0, "missing-partition"

    conf = job["conf"]
    horizons = conf["forecast"]["horizons"]
    rolling = conf["forecast"]["rolling_origin"]
    n_origins = rolling["n_origins"]
    min_train = rolling["min_train_fraction"]
    max_train = rolling.get("max_train_points")
    robustness_periods = conf["forecast"]["seasonal_period_robustness"]
    robustness_fraction = conf["forecast"].get("robustness_fraction", 1.0)

    try:
        series_list = load_series(
            path,
            plugin=plugin,
            metric=metric,
            year_month=year_month,
            entities=set(job["entities"]),
        )
    except Exception as exc:  # noqa: BLE001
        return label, 0, f"error: {type(exc).__name__}: {exc}"

    records: list[dict] = []
    models = build_suite()

    for series in series_list:
        values = series.values
        # Forecasters need a contiguous run. Taking the longest gap-free
        # stretch is more honest than imputing across outages, and its length
        # is recorded so short stretches can be filtered downstream.
        values = _longest_finite_run(values)
        if values.size < conf["features"]["min_length"]:
            continue

        day_steps = (
            int(round(86400.0 / series.step_s))
            if series.step_s and np.isfinite(series.step_s)
            else 1
        )
        seasonal = day_steps if 2 <= day_steps <= values.size // 3 else 1

        # The m=1 robustness check runs on a deterministic subsample, chosen by
        # hashing the series identity so it is reproducible and independent of
        # anything the data does.
        identity = f"{plugin}|{metric}|{series.entity}|{year_month}"
        in_robustness = (
            int(hashlib.blake2b(identity.encode(), digest_size=4).hexdigest(), 16) % 100
        ) < int(robustness_fraction * 100)
        periods = [(seasonal, "daily")]
        if in_robustness:
            periods += [(p, f"m{p}") for p in robustness_periods]

        for period, tag in periods:
            for record in iter_evaluations(
                values,
                models=models,
                horizons=horizons,
                seasonal_period=period,
                n_origins=n_origins,
                min_train_fraction=min_train,
                max_train=max_train,
            ):
                records.append(
                    {
                        "plugin": plugin,
                        "metric": metric,
                        "entity": series.entity,
                        "year_month": year_month,
                        "step_s": series.step_s,
                        "n_used": int(values.size),
                        "seasonal_period": period,
                        "seasonal_tag": tag,
                        **record,
                    }
                )

    if not records:
        return label, 0, "no-series"

    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(out, index=False, compression="zstd")
    return label, len(records), "ok"


def _longest_finite_run(values: np.ndarray) -> np.ndarray:
    """The longest gap-free stretch of a series."""
    finite = np.isfinite(values)
    if finite.all():
        return values
    if not finite.any():
        return values[:0]
    # Boundaries of runs of True.
    padded = np.concatenate(([False], finite, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    starts, ends = edges[0::2], edges[1::2]
    best = int(np.argmax(ends - starts))
    return values[starts[best] : ends[best]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=Path, default=paths.DERIVED / "sample.csv")
    ap.add_argument("--interim", type=Path, default=paths.INTERIM)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--out", type=Path, default=paths.SKILL)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    with open(args.conf) as fh:
        conf = yaml.safe_load(fh)
    paths.ensure_output_dirs()
    SHARD_DIR.mkdir(parents=True, exist_ok=True)

    sample = pd.read_csv(args.sample)

    # Bound the sweep. Predictability is measured on every sampled series;
    # skill is measured on a deterministic subset, because profiling put the
    # full suite at ~4.7 s per series per origin and the whole sample would
    # take ~50 hours. Membership is a hash of the series identity, so it is
    # reproducible and uncorrelated with anything the data does — never "the
    # first N" or "the ones that ran quickly". Recorded as OI-12.
    cap = conf["forecast"].get("max_series_per_stratum")
    if cap:
        identity = (
            sample.plugin + "|" + sample.metric + "|"
            + sample.entity.astype(str) + "|" + sample.year_month
        )
        sample = sample.assign(
            _rank=identity.map(
                lambda x: int(hashlib.blake2b(x.encode(), digest_size=8).hexdigest(), 16)
            )
        )
        before = len(sample)
        sample = (
            sample.sort_values("_rank")
            .groupby(["plugin", "origin", "value_kind"], observed=True)
            .head(cap)
            .drop(columns="_rank")
            .reset_index(drop=True)
        )
        print(f"forecast subset: {len(sample):,} of {before:,} sampled series (cap {cap}/stratum)")

    jobs = [
        {
            "year_month": year_month,
            "plugin": plugin,
            "metric": metric,
            "entities": [str(e) for e in group.entity],
            "path": str(partition_path(args.interim, year_month, plugin, metric)),
            "conf": conf,
        }
        for (year_month, plugin, metric), group in sample.groupby(
            ["year_month", "plugin", "metric"], observed=True
        )
    ]

    print(f"{len(sample):,} series in {len(jobs):,} partitions (workers={args.workers})")
    started = time.time()
    done = errors = 0

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_partition, job): job for job in jobs}
        for fut in as_completed(futures):
            label, _n, status = fut.result()
            done += 1
            if status not in {"ok", "cached"}:
                errors += 1
                print(f"  !! {label}: {status}", flush=True)
            if done % 25 == 0:
                rate = done / (time.time() - started)
                print(f"  {done:,}/{len(jobs):,} ({rate:.2f}/s, {errors} errors)", flush=True)

    shards = sorted(SHARD_DIR.glob("*.parquet"))
    print(f"\nConcatenating {len(shards):,} shards")
    skill = pd.concat((pd.read_parquet(s) for s in shards), ignore_index=True)
    skill["skill"] = 1.0 - skill["mase"]
    skill.to_parquet(args.out, index=False, compression="zstd")

    print(f"Wrote {len(skill):,} evaluations to {args.out}")
    defined = skill.mase.notna()
    print(f"defined MASE: {defined.sum():,} / {len(skill):,} ({defined.mean():.1%})")
    if defined.any():
        print("\n=== median skill by model (all horizons pooled) ===")
        print(skill[defined].groupby("model").skill.median().sort_values().round(3).to_string())
        print("\n=== median skill by plugin ===")
        print(skill[defined].groupby("plugin").skill.median().sort_values().round(3).to_string())


if __name__ == "__main__":
    main()
