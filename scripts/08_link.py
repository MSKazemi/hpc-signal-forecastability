#!/usr/bin/env python3
"""Stage 8 — the linking analysis: does predictability explain observed skill?

This is where the study's claim is tested, and where it can fail. The headline
number is the out-of-sample R² of a model that predicts forecast skill from
model-free predictability measures, cross-validated by **holding out an entire
signal family**. Random splits would let the model memorise family quirks; a
held-out family forces the relation to transfer to physics it has never seen.

Three results are written, and the second and third exist to attack the first:

1. ``link_cv.csv``          — leave-one-family-out R², against a mean baseline
2. ``link_importance.csv``  — which measures carry the weight
3. ``link_ablation.csv``    — what survives when instrument covariates, or the
                              tie-biased entropy (OI-11), are removed

If the R² collapses once the instrument covariates are dropped, then what the
model learned was how the signal was *sampled*, not what it *is* — and the
paper must say so.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.link.analysis import (  # noqa: E402
    FEATURE_COLUMNS,
    INSTRUMENT_COLUMNS,
    cluster_robust_correlation,
    feature_importance,
    leave_one_family_out,
    prepare,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--features", type=Path, default=paths.FEATURES)
    ap.add_argument("--skill", type=Path, default=paths.SKILL)
    ap.add_argument("--sample", type=Path, default=paths.DERIVED / "sample.csv")
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--horizon", type=int, default=None)
    args = ap.parse_args()

    with open(args.conf) as fh:
        conf = yaml.safe_load(fh)
    seed = conf["seed"]
    horizon = args.horizon or conf["forecast"]["horizons"][1]
    paths.ensure_output_dirs()

    features = pd.read_parquet(args.features)
    skill = pd.read_parquet(args.skill)

    # Taxonomy labels and the quantisation step live in the sample table.
    sample = pd.read_csv(args.sample)
    label_columns = [
        "plugin", "metric", "entity", "year_month",
        "origin", "value_kind", "scope", "controlled", "quantisation_step",
    ]
    features = features.merge(
        sample[label_columns],
        on=["plugin", "metric", "entity", "year_month"],
        how="left",
        validate="one_to_one",
    )

    data = prepare(features, skill, horizon=horizon)
    if data.empty:
        raise SystemExit(f"no series with defined skill at horizon {horizon}")

    print(f"horizon {horizon}: {len(data):,} series with defined skill")
    print(f"median best skill: {data.best_skill.median():.3f}")
    print("\n=== median best skill by origin ===")
    print(data.groupby("origin").best_skill.median().sort_values().round(3).to_string())

    full = FEATURE_COLUMNS + INSTRUMENT_COLUMNS

    # 1. The headline test.
    cv = leave_one_family_out(data, feature_columns=full, family="origin", seed=seed)
    cv.to_csv(paths.TABLES / "link_cv.csv", index=False)
    print("\n=== leave-one-family-out R^2 (held-out family) ===")
    print(cv.round(3).to_string(index=False))
    if len(cv):
        print(
            f"\nmean R^2: forest {cv.r2_forest.mean():.3f}, ridge {cv.r2_ridge.mean():.3f}, "
            f"baseline {cv.r2_baseline.mean():.3f}"
        )

    # 2. Which measures matter.
    importance = feature_importance(data, feature_columns=full, seed=seed)
    importance.to_csv(paths.TABLES / "link_importance.csv", index=False)
    print("\n=== permutation importance (top 10) ===")
    print(importance.head(10).round(4).to_string(index=False))

    # 3. Ablations that try to break the headline.
    ablations = {
        "full": full,
        "signal_only": FEATURE_COLUMNS,                       # drop instrument covariates
        "instrument_only": INSTRUMENT_COLUMNS,                # only how it was sampled
        "no_entropy": [c for c in full if "entropy" not in c],  # OI-11 robustness
    }
    rows = []
    for name, columns in ablations.items():
        result = leave_one_family_out(data, feature_columns=columns, family="origin", seed=seed)
        if len(result):
            rows.append(
                {
                    "ablation": name,
                    "n_features": len(columns),
                    "mean_r2_forest": result.r2_forest.mean(),
                    "mean_r2_ridge": result.r2_ridge.mean(),
                    "mean_r2_baseline": result.r2_baseline.mean(),
                }
            )
    ablation = pd.DataFrame(rows)
    ablation.to_csv(paths.TABLES / "link_ablation.csv", index=False)
    print("\n=== ablations ===")
    print(ablation.round(3).to_string(index=False))

    # 4. Cluster-robust marginal correlations (OI-9).
    correlations = []
    for column in full:
        stats = cluster_robust_correlation(data, column, "best_skill", cluster="metric")
        correlations.append({"feature": column, **stats})
    correlation_table = pd.DataFrame(correlations).sort_values("r", key=abs, ascending=False)
    correlation_table.to_csv(paths.TABLES / "link_correlations.csv", index=False)
    print("\n=== cluster-robust correlation with skill (clustered by metric) ===")
    print(correlation_table.round(3).to_string(index=False))

    print(f"\nWrote link_*.csv to {paths.TABLES}")


if __name__ == "__main__":
    main()
