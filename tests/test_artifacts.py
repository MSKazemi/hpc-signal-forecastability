"""Contract tests for the committed derived tables.

The tables under ``data/derived/`` are what a reader reproduces results from,
and what the paper's numbers are read out of. These tests assert the properties
the analysis silently relies on, so that a corrupted or half-written table fails
loudly here rather than becoming a wrong number in a figure.

Every test skips cleanly when its input is absent, so a fresh clone that has not
run the pipeline still has a green suite.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hsf import paths

pytestmark = pytest.mark.filterwarnings("ignore::FutureWarning")


def _load(path):
    if not path.exists():
        pytest.skip(f"{path.name} not built yet")
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


# ---------------------------------------------------------------------------
# inventory
# ---------------------------------------------------------------------------


def test_inventory_covers_the_whole_campaign():
    inventory = _load(paths.DERIVED / "inventory.parquet")
    assert set(inventory.columns) >= {"archive_month", "plugin", "metric", "size_bytes"}
    # 31 monthly archives, 2020-03 to 2022-09 inclusive.
    assert inventory.archive_month.nunique() == 31
    assert inventory.size_bytes.min() > 0


def test_inventory_shows_only_ipmi_present_every_month():
    """The campaign's central structural fact; the paper states it as a result."""
    inventory = _load(paths.DERIVED / "inventory.parquet")
    months = inventory.archive_month.nunique()
    per_pair = inventory.groupby(["plugin", "metric"]).archive_month.nunique()
    always = per_pair[per_pair == months]
    assert len(always) > 0
    assert set(always.index.get_level_values("plugin")) == {"ipmi"}


# ---------------------------------------------------------------------------
# census
# ---------------------------------------------------------------------------


def test_manifest_has_the_columns_the_analysis_needs():
    manifest = _load(paths.MANIFEST)
    required = {
        "plugin", "metric", "entity", "year_month", "n_samples",
        "dt_median_s", "dt_jitter", "gap_frac", "coverage",
        "quantisation_step", "is_constant", "v_min", "v_max",
    }
    missing = required - set(manifest.columns)
    assert not missing, f"census is missing {sorted(missing)}"


def test_census_rows_are_unique_per_series():
    """A duplicated series would silently double-weight it in every statistic."""
    manifest = _load(paths.MANIFEST)
    keys = ["plugin", "metric", "entity", "year_month"]
    assert not manifest.duplicated(keys).any()


def test_census_values_are_physically_possible():
    manifest = _load(paths.MANIFEST)
    assert (manifest.n_samples > 0).all()
    finite_range = manifest.dropna(subset=["v_min", "v_max"])
    assert (finite_range.v_min <= finite_range.v_max).all()
    coverage = manifest.coverage.dropna()
    assert (coverage > 0).all()


def test_jitter_and_cv_are_not_the_same_measure():
    """The distinction OI-1 turns on.

    dt_cv is inflated by long outages; dt_jitter is not. If the two ever agree
    closely, the robust measure has stopped being robust and the sampling
    result must not be trusted.
    """
    manifest = _load(paths.MANIFEST)
    both = manifest[["dt_cv", "dt_jitter"]].dropna()
    if len(both) < 100:
        pytest.skip("too few series with both measures")
    # They should be related but far from identical.
    correlation = both.corr().iloc[0, 1]
    assert correlation < 0.99, "dt_jitter is tracking dt_cv; it is not robust"


def test_constant_series_are_a_large_and_uneven_share():
    """A headline result: the share of dead signals differs sharply by family."""
    manifest = _load(paths.MANIFEST)
    share = manifest.groupby("plugin").is_constant.mean()
    assert share.max() > 0.3
    assert share.max() - share.min() > 0.2


# ---------------------------------------------------------------------------
# taxonomy and sample
# ---------------------------------------------------------------------------


def test_every_censused_metric_has_a_taxonomy_label():
    manifest = _load(paths.MANIFEST)
    taxonomy = _load(paths.TAXONOMY)
    pairs = set(map(tuple, manifest[["plugin", "metric"]].drop_duplicates().to_numpy()))
    labelled = set(map(tuple, taxonomy[["plugin", "metric"]].to_numpy()))
    assert not pairs - labelled


def test_taxonomy_records_a_rule_for_every_label():
    taxonomy = _load(paths.TAXONOMY)
    assert taxonomy.rule.notna().all()
    assert (taxonomy.rule.str.len() > 0).all()


def test_sample_is_drawn_only_from_eligible_series():
    sample = _load(paths.DERIVED / "sample.csv")
    assert (sample.n_samples >= 2000).all()
    assert (sample.coverage >= 0.5).all()


def test_sample_is_stratified_not_dominated_by_one_family():
    sample = _load(paths.DERIVED / "sample.csv")
    share = sample.origin.value_counts(normalize=True)
    assert share.max() < 0.35, "one origin dominates the sample"


# ---------------------------------------------------------------------------
# features and skill
# ---------------------------------------------------------------------------


def test_features_are_in_their_declared_ranges():
    features = _load(paths.FEATURES)
    for column in ["permutation_entropy", "spectral_entropy", "daily_seasonal_strength"]:
        values = features[column].dropna()
        if values.empty:
            continue
        assert values.between(-1e-9, 1 + 1e-9).all(), f"{column} outside [0, 1]"

    for column in ["flat_run_fraction", "jump_fraction", "filled_fraction"]:
        values = features[column].dropna()
        if not values.empty:
            assert values.between(-1e-9, 1 + 1e-9).all(), f"{column} outside [0, 1]"

    acf = features.acf1.dropna()
    if not acf.empty:
        assert acf.between(-1 - 1e-9, 1 + 1e-9).all()


def test_features_contain_no_infinities():
    features = _load(paths.FEATURES)
    numeric = features.select_dtypes("number")
    assert not np.isinf(numeric.to_numpy(dtype=float, na_value=0.0)).any()


def test_skill_is_finite_or_explicitly_undefined():
    """MASE must be a real number or nan — never inf.

    An infinite MASE means a denominator slipped through the degeneracy guard,
    which would poison every aggregate it enters.
    """
    skill = _load(paths.SKILL)
    mase = skill.mase.dropna()
    assert np.isfinite(mase).all()
    assert (mase >= 0).all()


def test_skill_covers_every_model_and_horizon():
    skill = _load(paths.SKILL)
    assert skill.model.nunique() >= 8
    assert skill.horizon.nunique() >= 2
    assert (skill.n_train > 0).all()
