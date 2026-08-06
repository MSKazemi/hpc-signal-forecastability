#!/usr/bin/env python3
"""Stage 8 — the linking analysis: does predictability explain observed skill?

This is where the study's claim is tested, and where it can fail. The headline
number is the out-of-sample R² of a model that predicts forecast skill from
model-free predictability measures, cross-validated by **holding out an entire
signal family**. Random splits would let the model memorise family quirks; a
held-out family forces the relation to transfer to physics it has never seen.

Five results are written, and all but the first exist to attack it:

1. ``link_cv.csv``          — leave-one-family-out R², against a mean baseline,
                              decomposed into level and ordering transfer
2. ``link_importance.csv``  — which measures carry the weight
3. ``link_ablation.csv``    — what survives when instrument covariates, or the
                              tie-biased entropy (OI-11), are removed
4. ``link_correlations.csv``— cluster-robust marginal correlations (OI-9)
5. ``link_null.csv``        — the same protocol run with *random* groups, so the
                              claim "grouping by family breaks transfer" has a
                              null distribution to be measured against

If the R² collapses once the instrument covariates are dropped, then what the
model learned was how the signal was *sampled*, not what it *is* — and the
paper must say so. If random groups score no better than real families, then
the family axis explains nothing and the headline is small-sample noise rather
than a finding about signal physics.
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
    random_group_null,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--features", type=Path, default=paths.FEATURES)
    ap.add_argument("--skill", type=Path, default=paths.SKILL)
    ap.add_argument("--sample", type=Path, default=paths.DERIVED / "sample.csv")
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--horizon", type=int, default=None)
    ap.add_argument(
        "--null-draws",
        type=int,
        default=100,
        help="random-group draws for the transfer null; 0 skips it",
    )
    ap.add_argument(
        "--seasonal-tag",
        default="m1",
        choices=["daily", "m1"],
        help="which MASE denominator to analyse; m1 is the conservative one",
    )
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
        "dt_jitter", "gap_frac", "coverage",
    ]
    features = features.merge(
        sample[label_columns],
        on=["plugin", "metric", "entity", "year_month"],
        how="left",
        validate="one_to_one",
    )

    data = prepare(features, skill, horizon=horizon, seasonal_tag=args.seasonal_tag)
    if data.empty:
        raise SystemExit(f"no series with defined skill at horizon {horizon}")

    print(f"horizon {horizon}, denominator {args.seasonal_tag}: "
          f"{len(data):,} series with defined skill")
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
        # The mean alone is not a summary of this distribution: one bad fold can
        # dominate it while most folds are positive. Report the shape.
        print(
            f"\nmean R^2: forest {cv.r2_forest.mean():.3f}, ridge {cv.r2_ridge.mean():.3f}, "
            f"baseline {cv.r2_baseline.mean():.3f}"
        )
        print(
            f"forest R^2 distribution: median {cv.r2_forest.median():.3f}, "
            f"range [{cv.r2_forest.min():.3f}, {cv.r2_forest.max():.3f}], "
            f"{int((cv.r2_forest > 0).sum())}/{len(cv)} families positive"
        )
        print("\n=== transfer decomposed: level vs ordering ===")
        print(
            f"mean R^2 given the true level: {cv.r2_level_corrected.mean():.3f} "
            f"(vs {cv.r2_forest.mean():.3f} without it)"
        )
        rho = cv.spearman_within.dropna()
        if len(rho):
            print(
                f"within-family Spearman rho: median {rho.median():.3f}, "
                f"{int((rho > 0).sum())}/{len(rho)} folds positive, "
                f"{int((cv.spearman_p < 0.05).sum())}/{len(cv)} significant at 0.05"
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

    # 5. The null the headline needs: is the family axis actually what breaks
    #    transfer, or would any fifteen-way split of this data look the same?
    null = random_group_null(
        data, feature_columns=full, family="origin", n_draws=args.null_draws, seed=seed
    )
    null.to_csv(paths.TABLES / "link_null.csv", index=False)
    if len(null) and len(cv):
        observed = cv.r2_forest.mean()
        # One-sided: how often does an arbitrary grouping do as badly as the
        # real families? A small p means the family axis carries real structure.
        p_value = float((null.mean_r2 <= observed).mean())
        print(f"\n=== random-group null ({len(null)} draws, sizes matched to real families) ===")
        print(
            f"null mean R^2: median {null.mean_r2.median():.3f}, "
            f"2.5-97.5% [{null.mean_r2.quantile(0.025):.3f}, {null.mean_r2.quantile(0.975):.3f}]"
        )
        print(f"observed (real families): {observed:.3f}   p = {p_value:.3f}")
        print(
            f"null families positive: median {null.frac_positive.median():.2f} "
            f"vs observed {float((cv.r2_forest > 0).mean()):.2f}"
        )

    print(f"\nWrote link_*.csv to {paths.TABLES}")


if __name__ == "__main__":
    main()
