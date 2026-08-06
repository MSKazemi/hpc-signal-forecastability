"""Known-answer tests for the predictability measures.

Each measure is checked against series whose predictability is known by
construction: a constant, a ramp, a pure sine, white noise, a random walk. If
a measure cannot separate white noise from a sine wave, no result computed with
it means anything, so these tests gate every downstream claim.

The paper cites this file when it asserts the measures behave as described.
"""

from __future__ import annotations

import numpy as np
import pytest

from hsf.features.measures import (
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
    stationarity_class,
    spectral_entropy,
    variance_ratio,
)

N = 4096
# Chosen to divide N exactly: a non-integer number of cycles leaks power across
# neighbouring frequency bins, which would weaken the spectral assertions for
# reasons that have nothing to do with the measures being tested.
PERIOD = 64


@pytest.fixture
def rng():
    return np.random.default_rng(20230288)


@pytest.fixture
def constant():
    return np.full(N, 7.5)


@pytest.fixture
def ramp():
    return np.linspace(0.0, 100.0, N)


@pytest.fixture
def sine():
    return np.sin(2 * np.pi * np.arange(N) / PERIOD)


@pytest.fixture
def noise(rng):
    return rng.standard_normal(N)


@pytest.fixture
def random_walk(rng):
    return np.cumsum(rng.standard_normal(N))


# ---------------------------------------------------------------------------
# entropy: the ordering noise > sine > ramp is the whole point
# ---------------------------------------------------------------------------


def test_permutation_entropy_orders_signals_by_predictability(ramp, sine, noise):
    assert permutation_entropy(ramp) < 0.05
    assert permutation_entropy(sine) < 0.5
    assert permutation_entropy(noise) > 0.95
    assert permutation_entropy(ramp) < permutation_entropy(sine) < permutation_entropy(noise)


def test_permutation_entropy_is_robust_to_scale_and_offset(sine):
    """Rank-based, so recalibrating a sensor barely moves the score.

    Invariance is exact only in exact arithmetic. Rescaling perturbs the last
    bits of near-equal samples and flips a few ties, which is why the tolerance
    here is 1e-2 rather than machine epsilon. The same mechanism has a real
    consequence for this dataset and is tracked as OI-11: heavily quantised
    signals such as integer-valued IPMI temperatures contain many exact ties,
    and the stable-argsort convention imposes an arbitrary order on them.
    """
    base = permutation_entropy(sine)
    assert permutation_entropy(sine * 1000.0 + 273.15) == pytest.approx(base, abs=1e-2)


def test_permutation_entropy_reports_tie_dominated_series_as_ordered():
    """A heavily tied series scores low because ties resolve to index order.

    This is the bias OI-11 is about: the score below is not evidence that the
    signal is predictable, only that it is quantised. Downstream analysis must
    therefore carry the quantisation step alongside the entropy.
    """
    coarse = np.repeat(np.arange(8.0), 512)  # 8 distinct values, many ties
    assert permutation_entropy(coarse) < 0.2


def test_spectral_entropy_separates_periodic_from_noise(sine, noise):
    assert spectral_entropy(sine) < 0.3
    assert spectral_entropy(noise) > 0.8


def test_lempel_ziv_complexity_orders_signals(sine, noise):
    assert lempel_ziv_complexity(sine) < lempel_ziv_complexity(noise)


# ---------------------------------------------------------------------------
# periodicity
# ---------------------------------------------------------------------------


def test_dominant_period_recovers_a_known_cycle(sine):
    period, strength = dominant_period_strength(sine)
    assert period == pytest.approx(PERIOD, rel=0.02)
    assert strength > 0.9


def test_seasonal_strength_high_for_sine_low_for_noise(sine, noise):
    assert seasonal_strength(sine, PERIOD) > 0.9
    assert seasonal_strength(noise, PERIOD) < 0.2


def test_seasonal_strength_needs_two_full_cycles(sine):
    assert np.isnan(seasonal_strength(sine[: PERIOD + 1], PERIOD))


# ---------------------------------------------------------------------------
# memory
# ---------------------------------------------------------------------------


def test_autocorrelation_known_values(sine, noise):
    assert autocorrelation(noise, lag=1) == pytest.approx(0.0, abs=0.05)
    # One full period back, a sine is perfectly correlated with itself.
    assert autocorrelation(sine, lag=PERIOD) > 0.99


def test_dfa_alpha_distinguishes_noise_from_random_walk(noise, random_walk):
    """0.5 for uncorrelated noise, ~1.5 for a random walk."""
    assert dfa_alpha(noise) == pytest.approx(0.5, abs=0.15)
    assert dfa_alpha(random_walk) == pytest.approx(1.5, abs=0.2)
    assert dfa_alpha(noise) < dfa_alpha(random_walk)


# ---------------------------------------------------------------------------
# stationarity
# ---------------------------------------------------------------------------


def test_drift_ratio_small_for_stationary_large_for_trending(noise, ramp):
    assert drift_ratio(noise) < 0.1
    assert drift_ratio(ramp) > 1.0


def test_variance_ratio_is_one_for_a_random_walk(random_walk):
    assert variance_ratio(random_walk, lag=8) == pytest.approx(1.0, abs=0.35)


def test_variance_ratio_detects_mean_reversion_at_the_full_period(sine):
    """A sine returns exactly to where it started after one full period.

    The lag matters: at half a period the same signal is at its maximum
    excursion and the ratio is far ABOVE one. Mean reversion is a statement
    about a particular horizon, not a property of the series alone.
    """
    assert variance_ratio(sine, lag=PERIOD) < 0.1
    assert variance_ratio(sine, lag=PERIOD // 2) > 1.0


# ---------------------------------------------------------------------------
# shape
# ---------------------------------------------------------------------------


def test_jump_fraction_detects_injected_steps(noise, rng):
    assert jump_fraction(noise) < 0.02
    jumpy = noise.copy()
    jumpy[500:] += 50.0  # a single large level shift
    assert jump_fraction(jumpy) > 0.0


def test_flat_run_measures_on_a_staircase():
    staircase = np.repeat(np.arange(64.0), 16)
    assert flat_run_fraction(staircase) == pytest.approx(15 / 16, abs=0.01)
    assert longest_flat_run(staircase) == 16


def test_flat_run_fraction_is_one_for_a_constant(constant):
    assert flat_run_fraction(constant) == 1.0
    assert longest_flat_run(constant) == N


def test_excess_kurtosis_heavier_for_spiky_differences(noise):
    spiky = noise.copy()
    spiky[::500] += 100.0
    assert excess_kurtosis(spiky) > excess_kurtosis(noise)


# ---------------------------------------------------------------------------
# degenerate inputs must return nan, never raise
#
# Roughly a third of the Vertiv and Schneider series in this dataset are
# constant, so degenerate input is the common case, not an edge case.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "measure",
    [
        permutation_entropy,
        spectral_entropy,
        lempel_ziv_complexity,
        dfa_alpha,
        drift_ratio,
        variance_ratio,
        jump_fraction,
        excess_kurtosis,
    ],
)
def test_constant_series_returns_nan(measure, constant):
    assert np.isnan(measure(constant))


@pytest.mark.parametrize(
    "measure",
    [
        permutation_entropy,
        spectral_entropy,
        lempel_ziv_complexity,
        dfa_alpha,
        drift_ratio,
        variance_ratio,
        jump_fraction,
        excess_kurtosis,
    ],
)
def test_short_series_returns_nan(measure):
    assert np.isnan(measure(np.array([1.0, 2.0, 3.0])))


def test_measures_ignore_nan_padding(sine):
    """Gaps are pervasive in this data; they must not silently corrupt a score."""
    padded = sine.copy()
    padded[::97] = np.nan
    assert permutation_entropy(padded) == pytest.approx(permutation_entropy(sine), abs=0.2)
    assert not np.isnan(spectral_entropy(padded))


# ---------------------------------------------------------------------------
# direction: separating a counter from every other kind of signal
#
# These exist because the linking analysis' worst held-out family is
# error_counter, and no measure in the original suite could see it coming.
# ---------------------------------------------------------------------------


def test_monotone_fraction_separates_counters_from_sensors(ramp, sine, noise, random_walk):
    assert monotone_fraction(ramp) == pytest.approx(1.0)
    # A mean-reverting signal moves up as often as down.
    assert monotone_fraction(sine) == pytest.approx(0.5, abs=0.02)
    assert monotone_fraction(noise) == pytest.approx(0.5, abs=0.05)
    assert monotone_fraction(random_walk) == pytest.approx(0.5, abs=0.05)


def test_monotone_fraction_is_not_fooled_by_a_constant(constant):
    """A constant never moves, so it has no direction — nan, not 1.0.

    Reporting 1.0 would make every setpoint register look like a counter, which
    is the exact confusion this measure exists to prevent.
    """
    assert np.isnan(monotone_fraction(constant))


def test_reset_rate_counts_counter_wraps():
    counter = np.tile(np.arange(500, dtype=float), 4)  # 4 cycles => 3 wraps
    rate = reset_rate(counter, per=1000)
    assert rate == pytest.approx(3 * 1000 / (counter.size - 1), rel=0.01)


def test_reset_rate_ignores_ordinary_noise_on_a_rising_counter(rng):
    """A one-unit wobble is not a reset; only a wrap is."""
    noisy = np.cumsum(rng.uniform(0.5, 1.5, N)) + rng.normal(0, 0.1, N)
    assert reset_rate(noisy) == 0.0


def test_reset_rate_undefined_for_a_signal_that_is_not_rising(sine):
    assert np.isnan(reset_rate(sine))


# ---------------------------------------------------------------------------
# stationarity, formally tested
# ---------------------------------------------------------------------------


def test_stationarity_tests_separate_noise_from_a_random_walk(noise, random_walk):
    # White noise: ADF rejects the unit root, KPSS does not reject stationarity.
    assert stationarity_class(adf_pvalue(noise), kpss_pvalue(noise)) == "stationary"
    # A random walk is the textbook unit-root process.
    assert stationarity_class(adf_pvalue(random_walk), kpss_pvalue(random_walk)) == "unit_root"


def test_stationarity_class_covers_every_cell():
    assert stationarity_class(0.01, 0.50) == "stationary"
    assert stationarity_class(0.50, 0.01) == "unit_root"
    assert stationarity_class(0.01, 0.01) == "both_reject"
    assert stationarity_class(0.50, 0.50) == "inconclusive"
    assert stationarity_class(np.nan, 0.5) == "unknown"


def test_changepoint_rate_finds_planted_level_shifts(rng):
    """Three shifts planted; the estimate must be close, not exact."""
    segments = [rng.normal(loc, 1.0, 1000) for loc in (0.0, 10.0, 0.0, 10.0)]
    shifted = np.concatenate(segments)
    found = changepoint_rate(shifted, per=1000) * shifted.size / 1000
    assert 3 <= found <= 5


def test_changepoint_rate_is_near_zero_for_stationary_noise(noise):
    assert changepoint_rate(noise, per=1000) * noise.size / 1000 <= 2


# ---------------------------------------------------------------------------
# complexity measures that survive quantisation (the OI-11 control)
# ---------------------------------------------------------------------------


def test_sample_entropy_orders_signals_by_predictability(sine, noise, constant):
    assert sample_entropy(sine) < sample_entropy(noise)
    assert np.isnan(sample_entropy(constant))


def test_compression_ratio_orders_signals_by_predictability(constant, sine, noise):
    assert compression_ratio(constant) == 0.0
    assert compression_ratio(sine) < compression_ratio(noise)
    assert compression_ratio(noise) > 0.7


def test_compression_ratio_is_blind_to_sensor_resolution(sine):
    """The point of the measure: shape, not bit depth.

    Permutation entropy correlates at +0.53 with the log number of distinct
    values (OI-11). A measure used to control for that bias must not share it,
    so the same waveform sampled coarsely and finely must score alike.
    """
    coarse = np.round(sine * 8) / 8
    fine = np.round(sine * 4096) / 4096
    assert compression_ratio(coarse) == pytest.approx(compression_ratio(fine), abs=0.1)


# ---------------------------------------------------------------------------
# tie handling (OI-11 fallback (c))
# ---------------------------------------------------------------------------


def test_random_tie_breaking_raises_entropy_of_a_tie_dominated_series():
    """A staircase scores as ordered only because ties are broken by index.

    The index convention invents a consistent ordering where the data supplies
    none, so a coarsely quantised sensor scores as predictable when what was
    measured is its resolution. Breaking ties at random removes the invention.
    """
    staircase = np.repeat(np.arange(8, dtype=float), N // 8)
    assert permutation_entropy(staircase, tie_policy="index") < 0.2
    assert permutation_entropy(staircase, tie_policy="random") > permutation_entropy(
        staircase, tie_policy="index"
    )


def test_tie_policy_does_not_move_a_tie_free_series(noise):
    assert permutation_entropy(noise, tie_policy="random") == pytest.approx(
        permutation_entropy(noise, tie_policy="index"), abs=0.01
    )


def test_unknown_tie_policy_is_rejected(sine):
    with pytest.raises(ValueError):
        permutation_entropy(sine, tie_policy="nonsense")


# ---------------------------------------------------------------------------
# spectral estimator (Welch vs the inconsistent periodogram)
# ---------------------------------------------------------------------------


def test_welch_and_periodogram_agree_on_the_ordering(sine, noise):
    for method in ("welch", "periodogram"):
        assert spectral_entropy(sine, method=method) < spectral_entropy(noise, method=method)


def test_welch_estimate_is_less_noisy_across_realisations(rng):
    """Why the default changed: the periodogram's variance does not shrink.

    Ten independent white-noise realisations should give ten similar
    forecastability scores. The periodogram's do not converge as n grows, so
    its spread across realisations is materially wider than Welch's.
    """
    draws = [rng.standard_normal(N) for _ in range(10)]
    welch = np.std([spectral_entropy(d, method="welch") for d in draws])
    periodogram = np.std([spectral_entropy(d, method="periodogram") for d in draws])
    assert welch < periodogram
