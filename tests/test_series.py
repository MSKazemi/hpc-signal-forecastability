"""Tests for resampling irregular telemetry onto a regular grid.

Resampling is a modelling decision, not a formatting step: done carelessly it
makes a badly sampled signal look well behaved, which would erase the exact
confound this study has to keep visible (OI-1). These tests pin the behaviour
that keeps it visible.
"""

from __future__ import annotations

import numpy as np
import pytest

from hsf.io.series import resample_to_grid, snap_step


def test_snap_step_picks_documented_cadences():
    assert snap_step(19.4) == 20.0     # IPMI/Ganglia nominal 20 s
    assert snap_step(10.2) == 10.0     # Vertiv/Logics nominal 10 s
    assert snap_step(905.0) == 900.0   # Nagios nominal 15 min
    assert snap_step(4.8) == 5.0       # SLURM nominal 5 s


def test_snap_step_rejects_nonsense():
    assert np.isnan(snap_step(0.0))
    assert np.isnan(snap_step(-5.0))
    assert np.isnan(snap_step(float("nan")))


def test_resample_preserves_a_perfectly_regular_series():
    step = 20.0
    n = 100
    ts = np.arange(n, dtype=np.int64) * int(step * 1e9)
    values = np.arange(n, dtype=float)

    gridded, t_start, filled = resample_to_grid(ts, values, step)

    assert gridded.size == n
    assert t_start == 0
    assert filled == pytest.approx(0.0)
    np.testing.assert_allclose(gridded, values)


def test_gaps_become_nan_and_are_never_interpolated():
    """The single most important property here.

    Interpolation would invent data and hide missingness. A forecaster must see
    the gap, and the analysis must be able to count it.
    """
    step = 20.0
    step_ns = int(step * 1e9)
    # Samples at grid slots 0, 1, then a hole at 2 and 3, then 4.
    ts = np.array([0, 1, 4], dtype=np.int64) * step_ns
    values = np.array([10.0, 11.0, 14.0])

    gridded, _, filled = resample_to_grid(ts, values, step)

    assert gridded.size == 5
    assert np.isnan(gridded[2])
    assert np.isnan(gridded[3])
    assert gridded[0] == 10.0 and gridded[4] == 14.0
    assert filled == pytest.approx(2 / 5)


def test_multiple_samples_in_one_bin_are_averaged():
    step = 20.0
    step_ns = int(step * 1e9)
    # Three samples inside the first bin, one in the second.
    ts = np.array([0, 5 * 10**9, 10 * 10**9, step_ns], dtype=np.int64)
    values = np.array([1.0, 2.0, 3.0, 100.0])

    gridded, _, _ = resample_to_grid(ts, values, step)

    assert gridded[0] == pytest.approx(2.0)
    assert gridded[1] == pytest.approx(100.0)


def test_filled_fraction_reports_real_sparsity():
    """A signal sampled at a tenth of the grid rate must report ~90% filled."""
    step = 2.0
    step_ns = int(step * 1e9)
    ts = (np.arange(20, dtype=np.int64) * 10) * step_ns  # every tenth slot
    values = np.arange(20, dtype=float)

    _, _, filled = resample_to_grid(ts, values, step)
    assert filled == pytest.approx(0.9, abs=0.02)


def test_nan_values_do_not_occupy_their_bin():
    step = 20.0
    step_ns = int(step * 1e9)
    ts = np.array([0, 1, 2], dtype=np.int64) * step_ns
    values = np.array([1.0, np.nan, 3.0])

    gridded, _, filled = resample_to_grid(ts, values, step)

    assert np.isnan(gridded[1])
    assert filled == pytest.approx(1 / 3)


def test_empty_input_is_handled():
    gridded, _, filled = resample_to_grid(np.array([], dtype=np.int64), np.array([]), 20.0)
    assert gridded.size == 0
    assert np.isnan(filled)
