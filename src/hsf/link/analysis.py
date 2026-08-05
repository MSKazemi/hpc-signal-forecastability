"""The linking analysis: does model-free predictability explain observed skill?

This is the study's central claim, and the module is written so that the claim
can lose. Three design choices do the work:

**Leave-one-family-out cross-validation.** Splitting series at random would let
the model memorise family-specific quirks and report a flattering R². Holding
out an entire signal family forces the relation to generalise to physics it has
never seen. If predictability measures capture something real about why
forecasting is hard, they must transfer from thermal signals to scheduler
signals; if they only capture "which plugin is this", they will not.

**A baseline that must be beaten.** Predicting the training-mean skill for every
series is the null. An R² is reported against it, so "the features explain
skill" means "better than knowing nothing", not "better than zero".

**Quantisation carried alongside entropy.** Permutation entropy is biased
downward by ties (OI-11), and quantisation varies systematically by plugin, so
an entropy-only model could reproduce family differences that are really
resolution differences. The quantisation step is therefore always in the design
matrix, and the analysis reports what happens when entropy is removed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# The predictability measures offered to the model. Observation-quality columns
# are included deliberately: if sampling irregularity explains more than signal
# structure does, that is the finding and it must be visible (OI-1).
FEATURE_COLUMNS = [
    "permutation_entropy",
    "spectral_entropy",
    "lempel_ziv",
    "dominant_period_strength",
    "daily_seasonal_strength",
    "acf1",
    "acf_day",
    "dfa_alpha",
    "drift_ratio",
    "variance_ratio_8",
    "jump_fraction",
    "flat_run_fraction",
    "excess_kurtosis",
    "filled_fraction",
]

# Observation-quality covariates, kept apart from the signal measures so their
# contribution can be isolated. These describe the INSTRUMENT, not the
# phenomenon, and OI-1 turns on being able to separate the two. dt_jitter and
# gap_frac are deliberately both present: fine-grained jitter and coarse
# outages are different problems for a forecaster, and an earlier single
# combined measure (dt_cv) conflated them badly enough to invert the ranking.
SAMPLING_COLUMNS = ["dt_jitter", "gap_frac", "coverage"]

# Carried separately so their contribution can be isolated from signal
# structure. These describe the INSTRUMENT, not the phenomenon.
INSTRUMENT_COLUMNS = ["log_quantisation_step", "log_step_s", *SAMPLING_COLUMNS]


def prepare(features: pd.DataFrame, skill: pd.DataFrame, *, horizon: int) -> pd.DataFrame:
    """Join predictability features to observed skill at one horizon.

    Skill is reduced to the median across rolling origins for the best model in
    the suite: the question is how well the signal *can* be forecast, so the
    per-series summary is the best any tier managed, not an average over models
    that includes deliberately weak baselines.
    """
    keys = ["plugin", "metric", "entity", "year_month"]

    subset = skill[(skill.horizon == horizon) & (skill.seasonal_tag == "daily")].copy()
    subset = subset[subset.mase.notna()]
    if subset.empty:
        return pd.DataFrame()

    # Median over origins first (robust to one unlucky window), then best model.
    per_model = subset.groupby([*keys, "model"], observed=True).skill.median().reset_index()
    best = per_model.groupby(keys, observed=True).skill.max().reset_index()
    best = best.rename(columns={"skill": "best_skill"})

    merged = features.merge(best, on=keys, how="inner", validate="one_to_one")

    # Instrument covariates on a log scale: both span orders of magnitude.
    step = merged.get("quantisation_step")
    merged["log_quantisation_step"] = (
        np.log10(step.where(step > 0)) if step is not None else np.nan
    )
    merged["log_step_s"] = np.log10(merged.step_s.where(merged.step_s > 0))
    return merged


def leave_one_family_out(
    data: pd.DataFrame,
    *,
    feature_columns: list[str],
    target: str = "best_skill",
    family: str = "origin",
    seed: int = 0,
) -> pd.DataFrame:
    """Fit on every family but one, predict the held-out family, repeat.

    Returns one row per held-out family with the R² of the model and of the
    train-mean baseline, both evaluated on the held-out family. A model that
    beats the baseline has learned something that transfers.
    """
    usable = data.dropna(subset=[target]).copy()
    matrix = usable[feature_columns].astype(float)
    # Median imputation, fitted per training split below; here only the columns
    # that are entirely missing are dropped.
    keep = [c for c in feature_columns if matrix[c].notna().any()]
    if not keep:
        return pd.DataFrame()

    rows = []
    for held_out in sorted(usable[family].dropna().unique()):
        test_mask = usable[family] == held_out
        train, test = usable[~test_mask], usable[test_mask]
        if len(train) < 30 or len(test) < 10:
            continue

        medians = train[keep].astype(float).median()
        x_train = train[keep].astype(float).fillna(medians).to_numpy()
        x_test = test[keep].astype(float).fillna(medians).to_numpy()
        y_train = train[target].to_numpy()
        y_test = test[target].to_numpy()

        model = make_pipeline(
            StandardScaler(),
            RandomForestRegressor(
                n_estimators=300, min_samples_leaf=5, random_state=seed, n_jobs=-1
            ),
        ).fit(x_train, y_train)
        linear = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(x_train, y_train)

        baseline = np.full_like(y_test, y_train.mean())
        rows.append(
            {
                "held_out_family": held_out,
                "n_train": len(train),
                "n_test": len(test),
                "r2_forest": r2_score(y_test, model.predict(x_test)),
                "r2_ridge": r2_score(y_test, linear.predict(x_test)),
                "r2_baseline": r2_score(y_test, baseline),
                "test_skill_mean": float(y_test.mean()),
                "train_skill_mean": float(y_train.mean()),
            }
        )
    return pd.DataFrame(rows)


def feature_importance(
    data: pd.DataFrame,
    *,
    feature_columns: list[str],
    target: str = "best_skill",
    seed: int = 0,
    n_repeats: int = 10,
) -> pd.DataFrame:
    """Permutation importance on a held-out split.

    Permutation importance is used rather than impurity importance because the
    latter is biased toward high-cardinality continuous features, and this
    design matrix mixes near-binary flags with continuous measures.
    """
    usable = data.dropna(subset=[target]).copy()
    keep = [c for c in feature_columns if usable[c].notna().any()]
    if not keep or len(usable) < 60:
        return pd.DataFrame()

    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(len(usable))
    cut = int(len(usable) * 0.7)
    train_idx, test_idx = shuffled[:cut], shuffled[cut:]

    medians = usable.iloc[train_idx][keep].astype(float).median()
    x = usable[keep].astype(float).fillna(medians).to_numpy()
    y = usable[target].to_numpy()

    model = RandomForestRegressor(
        n_estimators=300, min_samples_leaf=5, random_state=seed, n_jobs=-1
    ).fit(x[train_idx], y[train_idx])

    result = permutation_importance(
        model, x[test_idx], y[test_idx], n_repeats=n_repeats, random_state=seed, n_jobs=-1
    )
    return (
        pd.DataFrame(
            {
                "feature": keep,
                "importance_mean": result.importances_mean,
                "importance_std": result.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )


def cluster_robust_correlation(
    data: pd.DataFrame, x: str, y: str, cluster: str
) -> dict[str, float]:
    """Correlation with a cluster bootstrap over ``cluster``.

    Series from the same metric are not independent observations — 980 nodes
    share racks, inlet air, and workload — so a naive confidence interval would
    be far too narrow (OI-9). Resampling whole clusters rather than rows keeps
    the interval honest.
    """
    usable = data[[x, y, cluster]].dropna()
    if len(usable) < 30:
        return {"r": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": len(usable)}

    r = float(np.corrcoef(usable[x], usable[y])[0, 1])
    groups = [g for _, g in usable.groupby(cluster, observed=True)]
    rng = np.random.default_rng(0)

    draws = []
    for _ in range(1000):
        picked = rng.integers(0, len(groups), len(groups))
        resampled = pd.concat([groups[i] for i in picked], ignore_index=True)
        if resampled[x].std() > 0 and resampled[y].std() > 0:
            draws.append(np.corrcoef(resampled[x], resampled[y])[0, 1])

    if not draws:
        return {"r": r, "lo": float("nan"), "hi": float("nan"), "n": len(usable)}
    return {
        "r": r,
        "lo": float(np.percentile(draws, 2.5)),
        "hi": float(np.percentile(draws, 97.5)),
        "n": len(usable),
        "n_clusters": len(groups),
    }
