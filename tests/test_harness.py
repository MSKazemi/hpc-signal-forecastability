"""Tests for the evaluation harness.

The benchmark's job is to produce skill numbers that can be trusted. These
tests check the two ways that can fail: a model seeing the future, and an error
metric that is not actually scale-free.

A leaking benchmark flatters every model roughly equally, so it would not look
obviously broken — it would just quietly compress the differences between
tiers, which is precisely the signal this study is trying to read.
"""

from __future__ import annotations

import numpy as np
import pytest

from hsf.forecast.harness import (
    LeakageError,
    Split,
    assert_causal,
    iter_evaluations,
    mase,
    mase_denominator,
    rolling_origins,
)
from hsf.forecast.models import Persistence, SeasonalNaive, build_suite

PERIOD = 64
N = 1024


@pytest.fixture
def sine():
    return np.sin(2 * np.pi * np.arange(N) / PERIOD)


# ---------------------------------------------------------------------------
# split construction
# ---------------------------------------------------------------------------


def test_rolling_origins_respect_the_longest_horizon():
    splits = rolling_origins(1000, horizons=[1, 10, 100], n_origins=5)
    assert splits
    for split in splits:
        assert split.origin + split.horizon <= 1000


def test_rolling_origins_leave_a_minimum_training_window():
    splits = rolling_origins(1000, horizons=[10], n_origins=5, min_train_fraction=0.5)
    assert min(s.origin for s in splits) >= 500


def test_rolling_origins_empty_when_series_too_short():
    assert rolling_origins(50, horizons=[96], n_origins=5) == []


# ---------------------------------------------------------------------------
# causality
# ---------------------------------------------------------------------------


def test_assert_causal_rejects_a_test_window_past_the_end():
    with pytest.raises(LeakageError):
        assert_causal(Split(origin=990, horizon=100), n=1000)


def test_assert_causal_rejects_an_empty_training_window():
    with pytest.raises(LeakageError):
        assert_causal(Split(origin=0, horizon=10), n=1000)


def test_assert_causal_rejects_non_increasing_timestamps():
    timestamps = np.arange(100, dtype=float)
    timestamps[60] = timestamps[59]  # a duplicate right at the boundary
    with pytest.raises(LeakageError):
        assert_causal(Split(origin=60, horizon=5), n=100, timestamps=timestamps)


def test_assert_causal_accepts_a_well_formed_split():
    assert_causal(Split(origin=60, horizon=5), n=100, timestamps=np.arange(100, dtype=float))


def test_every_generated_split_is_causal(sine):
    """The splits the harness actually uses must all pass the guard."""
    timestamps = np.arange(N, dtype=float)
    for split in rolling_origins(N, horizons=[1, 4, 16], n_origins=8):
        assert_causal(split, N, timestamps)


# ---------------------------------------------------------------------------
# the metric
# ---------------------------------------------------------------------------


def test_mase_denominator_uses_only_the_training_window():
    """A volatile period after the origin must not change the scaling.

    This is the leak that matters most: if the denominator saw the test window,
    a volatile test period would inflate the denominator and make every model
    look better precisely where forecasting is hardest.
    """
    rng = np.random.default_rng(0)
    train = np.cumsum(rng.standard_normal(100))
    volatile_future = np.cumsum(rng.standard_normal(100)) * 1000.0
    combined = np.concatenate([train, volatile_future])

    assert mase_denominator(combined[:100], seasonal_period=1) == pytest.approx(
        mase_denominator(train, seasonal_period=1)
    )


def test_mase_is_one_when_the_model_matches_naive_error():
    actual = np.array([1.0, 2.0, 3.0])
    predicted = np.array([2.0, 3.0, 4.0])  # constant error of 1.0
    assert mase(actual, predicted, denominator=1.0) == pytest.approx(1.0)


def test_mase_is_scale_free():
    """Rescaling the whole series must not change MASE.

    Mandatory here: the benchmark spans watts, degrees, RPM, and packet counts,
    and any metric that is not scale-free would rank signals by their units.
    """
    rng = np.random.default_rng(0)
    y = np.cumsum(rng.standard_normal(200))
    train, actual = y[:150], y[150:160]
    predicted = np.full(10, train[-1])

    plain = mase(actual, predicted, mase_denominator(train, 1))
    scaled = mase(actual * 1000, predicted * 1000, mase_denominator(train * 1000, 1))
    assert plain == pytest.approx(scaled, rel=1e-9)


def test_mase_denominator_is_nan_for_a_constant_window():
    assert np.isnan(mase_denominator(np.ones(100), seasonal_period=1))


# ---------------------------------------------------------------------------
# end-to-end behaviour
# ---------------------------------------------------------------------------


def test_a_perfectly_periodic_series_has_an_undefined_denominator(sine):
    """MASE has no content when seasonal naive is already exact.

    A pure sine sampled at an integer number of points per cycle has a
    seasonal-naive error of zero, up to floating-point noise around 1e-16.
    Dividing by that would yield an arbitrary ratio of rounding errors, so the
    harness reports nan instead.
    """
    assert np.isnan(mase_denominator(sine[:512], seasonal_period=PERIOD))


def test_seasonal_naive_scores_about_one_on_a_noisy_cycle(sine):
    """Calibration check: MASE is defined so that seasonal naive scores ~1.

    Its test error and the in-sample denominator both equal the noise level, so
    the ratio must land near one. If this drifts, the metric is miswired and
    every skill number in the study is on the wrong scale.
    """
    rng = np.random.default_rng(0)
    noisy = sine + 0.1 * rng.standard_normal(N)
    records = list(
        iter_evaluations(
            noisy,
            models=[SeasonalNaive()],
            horizons=[PERIOD],
            seasonal_period=PERIOD,
            n_origins=3,
        )
    )
    assert records
    assert all(0.7 < r["mase"] < 1.3 for r in records)


def test_persistence_is_worse_than_seasonal_naive_on_a_noisy_cycle(sine):
    rng = np.random.default_rng(0)
    noisy = sine + 0.1 * rng.standard_normal(N)
    scores: dict[str, list[float]] = {}
    for record in iter_evaluations(
        noisy,
        models=[Persistence(), SeasonalNaive()],
        horizons=[PERIOD // 2],
        seasonal_period=PERIOD,
        n_origins=3,
    ):
        scores.setdefault(record["model"], []).append(record["mase"])

    assert np.mean(scores["persistence"]) > np.mean(scores["seasonal_naive"])


def test_every_model_in_the_suite_produces_a_finite_score(sine):
    rng = np.random.default_rng(1)
    y = sine + 0.1 * rng.standard_normal(N)
    records = list(
        iter_evaluations(
            y,
            models=build_suite(),
            horizons=[1, 8],
            seasonal_period=PERIOD,
            n_origins=2,
        )
    )
    assert records
    by_model: dict[str, list[float]] = {}
    for record in records:
        by_model.setdefault(record["model"], []).append(record["mase"])
    assert len(by_model) == len(build_suite())
    for name, scores in by_model.items():
        assert all(np.isfinite(s) for s in scores), f"{name} produced a non-finite MASE"


def test_a_failing_model_is_recorded_not_raised(sine):
    """One bad fit must not abort a sweep over hundreds of thousands of series."""

    class Broken:
        name = "broken"

        def fit(self, y, seasonal_period):
            raise RuntimeError("deliberate failure")

        def predict(self, horizon):  # pragma: no cover - never reached
            raise AssertionError

    records = list(
        iter_evaluations(
            sine, models=[Broken()], horizons=[4], seasonal_period=PERIOD, n_origins=2
        )
    )
    assert records
    assert all(np.isnan(r["mase"]) for r in records)
    assert all("deliberate failure" in r["error"] for r in records)


def test_constant_series_yields_nan_rather_than_exploding():
    """Constant series are roughly a third of some plugins; they must flow through."""
    records = list(
        iter_evaluations(
            np.full(512, 42.0),
            models=build_suite(),
            horizons=[4],
            seasonal_period=PERIOD,
            n_origins=2,
        )
    )
    assert records
    assert all(np.isnan(r["mase"]) for r in records)
