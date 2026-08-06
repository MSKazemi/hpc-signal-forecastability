#!/usr/bin/env python3
"""Stage 6 — compute model-free predictability measures for the sampled series.

Every measure comes from ``hsf.features.measures`` and none of them fits a
forecaster or sees a train/test split. This stage must run to completion before
any forecasting happens, so that the predictability profile of a series is
fixed before its skill is known.

Work is grouped by partition rather than by series: the sample draws many
entities from the same ``(month, plugin, metric)`` file, and reading that file
once instead of once per entity is the difference between minutes and hours.

Output: ``data/derived/features.parquet`` (committed).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.features.measures import (  # noqa: E402
    adf_pvalue,
    autocorrelation,
    changepoint_rate,
    compression_ratio,
    dfa_alpha,
    dominant_period_strength,
    drift_ratio,
    excess_kurtosis,
    flat_run_fraction,
    jump_fraction,
    kpss_pvalue,
    lempel_ziv_complexity,
    longest_flat_run,
    monotone_fraction,
    permutation_entropy,
    reset_rate,
    sample_entropy,
    seasonal_strength,
    spectral_entropy,
    stationarity_class,
    variance_ratio,
)
from hsf.io.series import load_series  # noqa: E402


def partition_path(interim: Path, year_month: str, plugin: str, metric: str) -> Path:
    return (
        interim
        / f"year_month={year_month}"
        / f"plugin={plugin}_pub"
        / f"metric={metric}"
        / "a_0.parquet"
    )


def measure_series(values: np.ndarray, step_s: float, conf: dict) -> dict:
    """The full predictability profile of one series."""
    features = conf["features"]
    pe = features["permutation_entropy"]

    # A day expressed in steps of this series' own cadence. Daily is the cycle
    # human working patterns impose on an HPC system, so it is the seasonal
    # period tested — but only where the series is sampled finely enough for a
    # day to be a meaningful number of steps.
    day_steps = int(round(86400.0 / step_s)) if step_s and np.isfinite(step_s) else 0
    period, period_strength = dominant_period_strength(values)

    # Both ADF and KPSS are needed for the four-cell classification; compute
    # them once and reuse, since each refits a regression over the series.
    adf_p = adf_pvalue(values)
    kpss_p = kpss_pvalue(values)

    sample_entropy_conf = features.get("sample_entropy", {"m": 2, "r_times_sd": 0.2})

    return {
        # entropy / complexity
        "permutation_entropy": permutation_entropy(values, order=pe["order"], delay=pe["delay"]),
        # Same measure with the tie convention that does not invent an ordering
        # out of equal values. Carried alongside rather than replacing it, so
        # the family ordering can be shown to survive the choice (OI-11(c)).
        "permutation_entropy_random_ties": permutation_entropy(
            values, order=pe["order"], delay=pe["delay"], tie_policy="random"
        ),
        "spectral_entropy": spectral_entropy(values),
        "sample_entropy": sample_entropy(
            values,
            m=sample_entropy_conf["m"],
            r_times_sd=sample_entropy_conf["r_times_sd"],
        ),
        "compression_ratio": compression_ratio(values),
        "lempel_ziv": lempel_ziv_complexity(values),
        # periodicity
        "dominant_period_steps": period,
        "dominant_period_strength": period_strength,
        "daily_seasonal_strength": (
            seasonal_strength(values, day_steps) if 2 <= day_steps <= values.size // 2 else np.nan
        ),
        # memory
        "acf1": autocorrelation(values, lag=1),
        "acf_day": autocorrelation(values, lag=day_steps) if day_steps >= 1 else np.nan,
        "dfa_alpha": dfa_alpha(
            values,
            min_scale=features["dfa"]["min_scale"],
            max_scale_fraction=features["dfa"]["max_scale_fraction"],
        ),
        # stationarity — formally tested, not merely proxied
        "drift_ratio": drift_ratio(values),
        "variance_ratio_8": variance_ratio(values, lag=8),
        "adf_pvalue": adf_p,
        "kpss_pvalue": kpss_p,
        "stationarity_class": stationarity_class(adf_p, kpss_p),
        "changepoint_rate": changepoint_rate(values),
        # direction — separates a monotone counter from every other signal, the
        # distinction the original suite could not make (see error_counter)
        "monotone_fraction": monotone_fraction(values),
        "reset_rate": reset_rate(values),
        # shape
        "jump_fraction": jump_fraction(values),
        "flat_run_fraction": flat_run_fraction(values),
        "longest_flat_run": longest_flat_run(values),
        "excess_kurtosis": excess_kurtosis(values),
        # observation quality, carried so predictability can be conditioned on it
        "day_steps": day_steps,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=Path, default=paths.DERIVED / "sample.csv")
    ap.add_argument("--interim", type=Path, default=paths.INTERIM)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--out", type=Path, default=paths.FEATURES)
    args = ap.parse_args()

    with open(args.conf) as fh:
        conf = yaml.safe_load(fh)
    paths.ensure_output_dirs()

    sample = pd.read_csv(args.sample)
    groups = list(sample.groupby(["year_month", "plugin", "metric"], observed=True))
    print(f"{len(sample):,} sampled series in {len(groups):,} partitions")

    min_length = conf["features"]["min_length"]
    # Same grid as the forecast stage; see analysis_grid in the config.
    grid_step = conf["analysis_grid"]["step_seconds"]
    rows: list[dict] = []
    skipped_missing = skipped_short = 0
    started = time.time()

    for i, ((year_month, plugin, metric), group) in enumerate(groups, start=1):
        path = partition_path(args.interim, year_month, plugin, metric)
        if not path.exists():
            skipped_missing += len(group)
            continue

        wanted = set(group.entity.astype(str))
        try:
            series_list = load_series(
                path,
                plugin=plugin,
                metric=metric,
                year_month=year_month,
                entities=wanted,
                step_s=grid_step,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  !! {year_month}/{plugin}/{metric}: {type(exc).__name__}: {exc}", flush=True)
            continue

        for series in series_list:
            # Measures need a contiguous run; gaps are dropped for the
            # computation but their share is recorded so it can be conditioned
            # on later (OI-1).
            finite = series.values[np.isfinite(series.values)]
            if finite.size < min_length:
                skipped_short += 1
                continue
            record = {
                "plugin": series.plugin,
                "metric": series.metric,
                "entity": series.entity,
                "year_month": series.year_month,
                "step_s": series.step_s,
                "n_grid": int(series.values.size),
                "n_observed": series.n_observed,
                "filled_fraction": series.filled_fraction,
            }
            record.update(measure_series(finite, series.step_s, conf))
            rows.append(record)

        if i % 25 == 0:
            rate = i / (time.time() - started)
            print(f"  {i:,}/{len(groups):,} partitions ({rate:.1f}/s, {len(rows):,} series)",
                  flush=True)

    features = pd.DataFrame(rows)
    features.to_parquet(args.out, index=False, compression="zstd")

    print(f"\nWrote {len(features):,} series to {args.out}")
    print(f"skipped: {skipped_missing:,} missing partition, {skipped_short:,} too short")
    if len(features):
        print("\n=== permutation entropy by plugin (median) ===")
        print(features.groupby("plugin").permutation_entropy.median().round(3).to_string())


if __name__ == "__main__":
    main()
