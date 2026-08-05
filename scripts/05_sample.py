#!/usr/bin/env python3
"""Stage 5 — draw the stratified sample of series that the sweep will run on.

The census describes far more series than can be forecast, so a sample is
unavoidable. What matters is that it is drawn on axes defined *before* any
predictability was measured, and uniformly at random within each stratum, so
that no series is chosen for how it behaves.

Strata are ``(plugin, origin, value_kind)`` — the taxonomy axes the study's
hypothesis is about. Every eligibility rule comes from ``conf/experiment.yaml``.

Exclusions are counted and reported rather than quietly applied: how many series
are constant, too short, or too sparse is itself a result about HPC telemetry.

Output: ``data/derived/sample.csv`` (committed) and a report of what was
dropped and why.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402


def load_conf(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def apply_eligibility(manifest: pd.DataFrame, rules: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the census into eligible series and a table of exclusion reasons."""
    reasons = pd.DataFrame(index=manifest.index)
    reasons["too_short"] = manifest.n_samples < rules["min_samples"]
    reasons["low_coverage"] = manifest.coverage.fillna(0) < rules["min_coverage"]
    if rules.get("exclude_constant", True):
        reasons["constant"] = manifest.is_constant.fillna(False)
    else:
        reasons["constant"] = False
    # A series whose values never parsed as numbers cannot be forecast.
    reasons["non_numeric"] = manifest.n_unique.fillna(0) == 0

    excluded = reasons.any(axis=1)
    return manifest[~excluded].copy(), reasons


def draw(eligible: pd.DataFrame, per_stratum: int, seed: int) -> pd.DataFrame:
    """Uniform random sample of up to ``per_stratum`` series per stratum."""
    rng = np.random.default_rng(seed)
    chunks = []
    for _, group in eligible.groupby(["plugin", "origin", "value_kind"], observed=True):
        take = min(per_stratum, len(group))
        picked = rng.choice(len(group), size=take, replace=False)
        chunks.append(group.iloc[np.sort(picked)])
    if not chunks:
        return eligible.head(0)
    return pd.concat(chunks, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=paths.MANIFEST)
    ap.add_argument("--taxonomy", type=Path, default=paths.TAXONOMY)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--out", type=Path, default=paths.DERIVED / "sample.csv")
    args = ap.parse_args()

    conf = load_conf(args.conf)
    paths.ensure_output_dirs()

    manifest = pd.read_parquet(args.manifest)
    taxonomy = pd.read_csv(args.taxonomy)
    merged = manifest.merge(taxonomy, on=["plugin", "metric"], how="left", validate="many_to_one")

    unlabelled = merged.origin.isna().sum()
    if unlabelled:
        raise SystemExit(f"{unlabelled} series have no taxonomy label; run 04_taxonomy.py first")

    eligible, reasons = apply_eligibility(merged, conf["sampling"]["eligibility"])

    print(f"census: {len(merged):,} series")
    print("\n=== exclusions (a series may fail several rules) ===")
    for column in reasons.columns:
        n = int(reasons[column].sum())
        print(f"  {column:14s} {n:>9,}  ({n / len(merged):6.1%})")
    print(f"  {'ELIGIBLE':14s} {len(eligible):>9,}  ({len(eligible) / len(merged):6.1%})")

    print("\n=== constant series by plugin (a result, not just an exclusion) ===")
    constant_share = merged.groupby("plugin").is_constant.mean().sort_values(ascending=False)
    print((constant_share * 100).round(1).to_string())

    sample = draw(eligible, conf["sampling"]["per_stratum"], conf["seed"])
    columns = [
        "plugin", "metric", "entity", "entity_keys", "year_month",
        "origin", "value_kind", "scope", "controlled",
        "n_samples", "coverage", "dt_median_s", "dt_cv", "missing_frac",
        "quantisation_step", "n_unique", "v_min", "v_max", "v_mean", "v_std",
    ]
    sample[columns].to_csv(args.out, index=False)

    n_strata = sample.groupby(["plugin", "origin", "value_kind"], observed=True).ngroups
    print(f"\nsampled {len(sample):,} series across {n_strata} strata")
    print("\n=== sample per plugin ===")
    print(sample.plugin.value_counts().to_string())
    print("\n=== sample per origin ===")
    print(sample.origin.value_counts().to_string())
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
