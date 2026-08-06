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
from scipy import stats
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
    "sample_entropy",
    "compression_ratio",
    "lempel_ziv",
    "dominant_period_strength",
    "daily_seasonal_strength",
    "acf1",
    "acf_day",
    "dfa_alpha",
    "drift_ratio",
    "variance_ratio_8",
    # Formally tested stationarity, not proxied. The ADF/KPSS pair is what
    # decides whether drift or persistence is the right baseline for a series,
    # which is exactly the distinction the error_counter family turns on.
    "adf_pvalue",
    "kpss_pvalue",
    "changepoint_rate",
    # Direction. Nothing else in the suite can tell a monotone counter from any
    # other signal: permutation entropy scores it 0.000, the same value an
    # alarm state gets for the opposite structural reason (OI-11).
    "monotone_fraction",
    "reset_rate",
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
#
# ``log_step_s`` is deliberately absent. Every series is resampled onto the same
# 15-minute analysis grid before anything is measured (OI-4), so the column is
# constant across the whole sample: it scored a correlation of -1.8e-16 and a
# permutation importance of exactly 0.0, which are the signatures of a column
# with no variance rather than of a measure that was tried and failed. Native
# cadence survives regridding as metadata and is carried by ``nominal_step_s``
# from the manifest, which is the covariate the study actually wanted.
INSTRUMENT_COLUMNS = ["log_quantisation_step", *SAMPLING_COLUMNS]


def prepare(
    features: pd.DataFrame, skill: pd.DataFrame, *, horizon: int, seasonal_tag: str = "m1"
) -> pd.DataFrame:
    """Join predictability features to observed skill at one horizon.

    Skill is reduced to the median across rolling origins for the best model in
    the suite: the question is how well the signal *can* be forecast, so the
    per-series summary is the best any tier managed, not an average over models
    that includes deliberately weak baselines.
    """
    keys = ["plugin", "metric", "entity", "year_month"]

    subset = skill[(skill.horizon == horizon) & (skill.seasonal_tag == seasonal_tag)].copy()
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

    **R² conflates two distinct failures, and they have different meanings.** A
    held-out family has both a *level* (its mean skill) and an *ordering* (which
    of its series are easier than others). R² punishes an error in either, but
    only the level error is inevitable here: training-set mean skill is nearly
    constant across folds while held-out mean skill is not, so a model fitted on
    the other families has no information at all about where a new family sits.
    Three extra columns separate the two failures:

    ``spearman_within``
        Rank correlation between predicted and observed skill *inside* the
        held-out family. This is transfer of ordering, and it is unaffected by
        any constant offset.
    ``level_bias``
        Predicted minus observed mean skill for the held-out family — the
        offset itself, in skill units.
    ``r2_level_corrected``
        R² after shifting the predictions to the held-out family's true mean,
        i.e. what the model would score if an oracle told it the level. The gap
        between this and ``r2_forest`` is the share of the failure that is
        purely not knowing the offset.

    Reporting only the mean R² would collapse all three into one number and
    attribute an unavoidable failure to the predictability measures.
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
        predicted = model.predict(x_test)

        # Ordering transfer, immune to a constant offset. Undefined when the
        # held-out family has no spread in skill to rank.
        if np.std(y_test) > 0 and np.std(predicted) > 0:
            rho, rho_p = stats.spearmanr(y_test, predicted)
        else:
            rho, rho_p = np.nan, np.nan

        # What the model would score if it were handed the held-out family's
        # true mean. The gap to r2_forest is the cost of not knowing the level.
        centred = predicted - predicted.mean() + y_test.mean()

        rows.append(
            {
                "held_out_family": held_out,
                "n_train": len(train),
                "n_test": len(test),
                "r2_forest": r2_score(y_test, predicted),
                "r2_ridge": r2_score(y_test, linear.predict(x_test)),
                "r2_baseline": r2_score(y_test, baseline),
                "spearman_within": float(rho),
                "spearman_p": float(rho_p),
                "level_bias": float(predicted.mean() - y_test.mean()),
                "r2_level_corrected": r2_score(y_test, centred),
                "test_skill_mean": float(y_test.mean()),
                "train_skill_mean": float(y_train.mean()),
            }
        )
    return pd.DataFrame(rows)


def random_group_null(
    data: pd.DataFrame,
    *,
    feature_columns: list[str],
    target: str = "best_skill",
    family: str = "origin",
    n_draws: int = 100,
    seed: int = 0,
    n_estimators: int = 150,
) -> pd.DataFrame:
    """What R² would this protocol give if the groups were arbitrary?

    The study's headline is that grouping by *signal family* breaks transfer.
    That is a claim about the family axis specifically, and it needs a null:
    with 1,082 series, 19 features and fifteen folds, some spread of held-out R²
    is guaranteed whatever the grouping. This re-runs the identical procedure
    with random groups whose sizes match the real families exactly, so the only
    thing that changes is *which* series are held out together.

    If the real families score no worse than random groups, the failure is
    generic small-sample instability and the paper's causal story is wrong. If
    they score clearly worse, the family axis is doing real work and the claim
    is earned rather than assumed.

    Sizes are matched rather than drawn uniformly because fold size drives R²
    variance directly; unmatched groups would confound the two.
    """
    usable = data.dropna(subset=[target]).copy()
    keep = [c for c in feature_columns if usable[c].notna().any()]
    if not keep:
        return pd.DataFrame()

    sizes = usable[family].value_counts().sort_index().to_numpy()
    rng = np.random.default_rng(seed)
    x_all = usable[keep].astype(float)
    y_all = usable[target].to_numpy()

    rows = []
    for draw in range(n_draws):
        # Shuffle series, then cut into blocks matching the real family sizes.
        order = rng.permutation(len(usable))
        labels = np.empty(len(usable), dtype=int)
        start = 0
        for group_id, size in enumerate(sizes):
            labels[order[start : start + size]] = group_id
            start += size

        scores = []
        for group_id, size in enumerate(sizes):
            test_mask = labels == group_id
            if test_mask.sum() < 10 or (~test_mask).sum() < 30:
                continue
            medians = x_all[~test_mask].median()
            x_train = x_all[~test_mask].fillna(medians).to_numpy()
            x_test = x_all[test_mask].fillna(medians).to_numpy()
            model = RandomForestRegressor(
                n_estimators=n_estimators, min_samples_leaf=5, random_state=seed, n_jobs=-1
            ).fit(x_train, y_all[~test_mask])
            scores.append(r2_score(y_all[test_mask], model.predict(x_test)))

        if scores:
            rows.append(
                {
                    "draw": draw,
                    "mean_r2": float(np.mean(scores)),
                    "median_r2": float(np.median(scores)),
                    "min_r2": float(np.min(scores)),
                    "frac_positive": float(np.mean(np.asarray(scores) > 0)),
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
