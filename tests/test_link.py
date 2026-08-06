"""Tests for the linking analysis' transfer diagnostics.

The headline of this study is a negative result, so the diagnostics that
qualify it carry as much weight as the headline itself and are tested here
against cases whose answer is known by construction.
"""

from __future__ import annotations

import numpy as np
import pytest


def test_extrapolation_distance_separates_interleaved_from_disjoint_folds():
    """The measure must tell "never seen this region" from "seen it, law fails".

    Two synthetic folds with identical sizes: one whose test points are drawn
    from the same distribution as training (interpolation), one whose test
    points are shifted far away (extrapolation). Without this distinction a
    family that transfers badly because nothing in training resembles it is
    indistinguishable from one where the relation genuinely does not hold.
    """
    from hsf.link.analysis import _extrapolation_distance

    rng = np.random.default_rng(0)
    train = rng.standard_normal((200, 5))
    interleaved = rng.standard_normal((40, 5))
    far_away = rng.standard_normal((40, 5)) + 20.0

    assert _extrapolation_distance(train, interleaved) < 3.0
    assert _extrapolation_distance(train, far_away) > 10.0


def test_extrapolation_distance_is_scale_invariant():
    """A feature measured in kilowatts must not outvote one measured in a ratio."""
    from hsf.link.analysis import _extrapolation_distance

    rng = np.random.default_rng(1)
    train = rng.standard_normal((150, 4))
    test = rng.standard_normal((30, 4)) + 5.0

    stretched = np.array([1.0, 1000.0, 1.0, 0.001])
    plain = _extrapolation_distance(train, test)
    rescaled = _extrapolation_distance(train * stretched, test * stretched)
    assert rescaled == pytest.approx(plain, rel=1e-6)


def test_mae_skill_credits_a_good_prediction_that_r2_condemns():
    """The case that made this study read as a null result.

    A held-out family whose series nearly all share the same skill has almost no
    variance about its own mean, and R^2 divides by exactly that. A model that
    predicts every one of them to within a thirtieth of the baseline's error
    still scores a large negative R^2 — because R^2's implicit comparator is an
    oracle that already knows the family's mean, which is the one thing a model
    predicting an unseen family cannot know.

    This is not a hypothetical: it is the alarm_state fold, where MAE 0.036
    against a baseline of 0.600 was reported as R^2 = -2.05.
    """
    from sklearn.metrics import mean_absolute_error, r2_score

    rng = np.random.default_rng(0)
    # A homogeneous family: every series has skill near 0.99.
    truth = 0.99 + rng.normal(0, 0.02, 100)
    # The model is nearly right; the family-blind baseline is the training mean.
    predicted = truth + rng.normal(0, 0.03, 100)
    baseline = np.full(100, 0.40)

    mae_skill = 1.0 - mean_absolute_error(truth, predicted) / mean_absolute_error(truth, baseline)

    assert r2_score(truth, predicted) < 0, "R^2 condemns this prediction"
    assert mae_skill > 0.8, "against what a model can actually know, it is excellent"


def test_leave_one_family_out_reports_both_criteria():
    """Both statistics must be emitted, so neither can be quoted alone."""
    import pandas as pd

    from hsf.link.analysis import leave_one_family_out

    rng = np.random.default_rng(2)
    n_per = 40
    frames = []
    for family in range(5):
        feature = rng.uniform(0, 1, n_per)
        frames.append(
            pd.DataFrame(
                {
                    "flat_run_fraction": feature,
                    "excess_kurtosis": rng.normal(0, 1, n_per),
                    "origin": f"family_{family}",
                    "best_skill": feature + rng.normal(0, 0.05, n_per),
                }
            )
        )
    data = pd.concat(frames, ignore_index=True)

    cv = leave_one_family_out(
        data, feature_columns=["flat_run_fraction", "excess_kurtosis"], family="origin"
    )
    for column in ("r2_forest", "mae_skill", "mae_baseline", "spearman_within", "skill_sd_test"):
        assert column in cv.columns, f"{column} missing"
    # A genuinely portable law, with families drawn from the same distribution.
    assert cv.mae_skill.median() > 0
