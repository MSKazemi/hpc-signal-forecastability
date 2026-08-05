"""Model-free predictability measures.

Every function here takes a single evenly-spaced series and returns a number
describing *how predictable it could be in principle*. None of them fits a
forecaster, sees a train/test split, or knows what model will later be applied.
That separation is what makes the study's central claim testable: if these
numbers predict the skill a forecaster actually achieves, the difficulty is a
property of the signal rather than of the model.

Each measure is grouped by the mechanism it probes:

============  ==========================================================
entropy       how much genuine novelty each new sample carries
periodicity   how much of the signal repeats on a fixed cycle
memory        how far into the past useful information extends
stationarity  whether the rules generating the signal stay put
shape         quantisation, jumps, and flat runs — structural error floors
============  ==========================================================

Conventions
-----------
* Entropy-like measures are normalised to ``[0, 1]``, where 0 means perfectly
  predictable and 1 means indistinguishable from noise. This makes them
  comparable across signals with wildly different units — watts, degrees, RPM,
  and percentages all appear in this dataset.
* Every function returns ``nan`` rather than raising when the series is too
  short or degenerate. Constant series are extremely common here (roughly a
  third of Vertiv and Schneider series), and they must flow through the
  pipeline as data, not as exceptions.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import signal as sp_signal
from scipy import stats as sp_stats
from scipy.ndimage import uniform_filter1d

NAN = float("nan")

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _clean(x: np.ndarray) -> np.ndarray:
    """Finite values only, as float64."""
    x = np.asarray(x, dtype=np.float64)
    return x[np.isfinite(x)]


def _is_degenerate(x: np.ndarray, minimum: int = 8) -> bool:
    return x.size < minimum or float(np.ptp(x)) == 0.0


# ---------------------------------------------------------------------------
# entropy and complexity
# ---------------------------------------------------------------------------


def permutation_entropy(x: np.ndarray, order: int = 5, delay: int = 1) -> float:
    """Normalised permutation entropy (Bandt & Pompe, 2002).

    Counts how evenly the orderings of successive ``order``-tuples are
    distributed. A monotone ramp uses one ordering and scores 0; white noise
    uses all ``order!`` orderings equally and scores 1.

    It is the natural first measure here because it depends only on the *rank*
    pattern of the samples, so it is invariant to the calibration and unit
    differences that separate an IPMI temperature from a Ganglia counter.
    """
    x = _clean(x)
    n_vectors = x.size - (order - 1) * delay
    if _is_degenerate(x) or n_vectors < 2 or order < 2:
        return NAN

    # Embed, then rank each row; identical values are broken by index order,
    # which is the standard Bandt-Pompe convention.
    embedded = np.empty((n_vectors, order))
    for i in range(order):
        embedded[:, i] = x[i * delay : i * delay + n_vectors]
    patterns = np.argsort(embedded, axis=1, kind="stable")

    # Encode each permutation as an integer via mixed radix.
    weights = order ** np.arange(order)
    codes = patterns @ weights
    _, counts = np.unique(codes, return_counts=True)

    probabilities = counts / counts.sum()
    entropy = -np.sum(probabilities * np.log(probabilities))
    max_entropy = np.log(float(math.factorial(order)))
    return float(entropy / max_entropy) if max_entropy > 0 else NAN


def spectral_entropy(x: np.ndarray) -> float:
    """Normalised Shannon entropy of the power spectral density.

    Concentrated spectra (a strong daily cycle) score near 0; flat spectra
    (white noise) score near 1. This is the frequency-domain counterpart to
    permutation entropy and catches periodic structure that rank statistics
    can miss.
    """
    x = _clean(x)
    if _is_degenerate(x, minimum=16):
        return NAN
    _, psd = sp_signal.periodogram(x - x.mean())
    psd = psd[psd > 0]
    if psd.size < 2:
        return NAN
    probabilities = psd / psd.sum()
    return float(-np.sum(probabilities * np.log(probabilities)) / np.log(probabilities.size))


def lempel_ziv_complexity(x: np.ndarray, max_length: int = 8192) -> float:
    """Normalised Lempel-Ziv complexity of the median-binarised series.

    Counts the distinct substrings needed to build the sequence, normalised by
    the ``n / log2(n)`` rate expected of a random binary string. Sensitive to
    repeated motifs that entropy measures average away — useful for the on/off
    alarm and pump-status signals, where the interesting structure is the
    *pattern* of switching rather than the values.

    Implements Kaspar & Schuster's formulation of LZ76. The ``k_max``
    bookkeeping is essential, not an optimisation: without it the pointer can
    revisit the same position forever.

    The algorithm is quadratic in the worst case, so the series is truncated to
    ``max_length`` samples. Truncation is applied consistently across every
    series in the study, and the normalisation makes the scores comparable.
    """
    x = _clean(x)
    if _is_degenerate(x):
        return NAN
    if x.size > max_length:
        x = x[:max_length]

    bits = (x > np.median(x)).astype(np.uint8)
    n = bits.size
    if n < 2:
        return NAN

    i = 0          # start of the candidate substring being matched
    k = 1          # current match length
    k_max = 1      # longest match found since the last new phrase
    ell = 1        # end of the already-parsed prefix
    complexity = 1

    while True:
        if bits[i + k - 1] == bits[ell + k - 1]:
            k += 1
            if ell + k > n:
                complexity += 1
                break
            continue

        k_max = max(k_max, k)
        i += 1
        if i == ell:
            complexity += 1
            ell += k_max
            if ell + 1 > n:
                break
            i, k, k_max = 0, 1, 1
        else:
            k = 1

    normaliser = n / np.log2(n)
    return float(complexity / normaliser) if normaliser > 0 else NAN


# ---------------------------------------------------------------------------
# periodicity
# ---------------------------------------------------------------------------


def dominant_period_strength(x: np.ndarray, max_period: int | None = None) -> tuple[float, float]:
    """Return ``(period, strength)`` of the strongest spectral peak.

    ``strength`` is the fraction of total spectral power in that peak.
    The period is reported in samples so the caller can convert using the
    series' own cadence — necessary because cadence varies by three orders of
    magnitude across this dataset.
    """
    x = _clean(x)
    if _is_degenerate(x, minimum=32):
        return NAN, NAN
    freqs, psd = sp_signal.periodogram(x - x.mean())
    keep = freqs > 0
    freqs, psd = freqs[keep], psd[keep]
    if psd.size == 0 or psd.sum() == 0:
        return NAN, NAN
    if max_period is not None:
        keep = freqs >= 1.0 / max_period
        if keep.sum() < 2:
            return NAN, NAN
        freqs, psd = freqs[keep], psd[keep]
    peak = int(np.argmax(psd))
    return float(1.0 / freqs[peak]), float(psd[peak] / psd.sum())


def seasonal_strength(x: np.ndarray, period: int) -> float:
    """Strength of a seasonal cycle of known ``period``, in ``[0, 1]``.

    Defined as ``1 - var(residual) / var(residual + seasonal)`` following the
    ``tsfeatures`` convention. Uses a simple period-mean decomposition rather
    than full STL: it is far cheaper across hundreds of thousands of series and
    the two agree closely once the trend is removed.
    """
    x = _clean(x)
    if period < 2 or x.size < 2 * period or _is_degenerate(x):
        return NAN

    # Remove a slow trend so it cannot masquerade as seasonality.
    #
    # Both steps below must be linear in the series length. The obvious
    # implementations are not: a daily period at a 10-second cadence is 8,640
    # steps, so an explicit convolution kernel costs O(n * period) and a Python
    # loop over phases costs the same again. On a month of 10-second data that
    # is billions of operations per series, and the sweep never finishes.
    window = min(period, x.size // 2) | 1
    trend = uniform_filter1d(x, size=window, mode="nearest")
    detrended = x - trend

    phase = np.arange(x.size) % period
    # Phase means by bincount rather than by masking once per phase.
    counts = np.bincount(phase, minlength=period)
    sums = np.bincount(phase, weights=detrended, minlength=period)
    seasonal_means = np.divide(sums, counts, out=np.zeros(period), where=counts > 0)
    seasonal = seasonal_means[phase]
    residual = detrended - seasonal

    denominator = np.var(residual + seasonal)
    if denominator <= 0:
        return NAN
    return float(max(0.0, 1.0 - np.var(residual) / denominator))


# ---------------------------------------------------------------------------
# memory
# ---------------------------------------------------------------------------


def autocorrelation(x: np.ndarray, lag: int = 1) -> float:
    """Autocorrelation at ``lag``."""
    x = _clean(x)
    if _is_degenerate(x) or lag < 1 or x.size <= lag + 1:
        return NAN
    a, b = x[:-lag], x[lag:]
    if np.std(a) == 0 or np.std(b) == 0:
        return NAN
    return float(np.corrcoef(a, b)[0, 1])


def dfa_alpha(x: np.ndarray, min_scale: int = 8, max_scale_fraction: float = 0.25) -> float:
    """Detrended fluctuation analysis scaling exponent.

    Interpretation: ``0.5`` uncorrelated noise, ``1.0`` 1/f (long memory),
    ``1.5`` a random walk. Values above 0.5 mean the past carries information
    about the future beyond the immediate lag, which is precisely the resource
    a forecaster exploits.

    DFA is used rather than a raw Hurst estimator because it tolerates the slow
    drifts that pervade thermal and facility signals.
    """
    x = _clean(x)
    max_scale = int(x.size * max_scale_fraction)
    if _is_degenerate(x, minimum=64) or max_scale <= min_scale:
        return NAN

    profile = np.cumsum(x - x.mean())
    scales = np.unique(np.logspace(np.log10(min_scale), np.log10(max_scale), 16).astype(int))
    scales = scales[scales >= min_scale]
    if scales.size < 4:
        return NAN

    fluctuations = []
    usable_scales = []
    for scale in scales:
        n_windows = profile.size // scale
        if n_windows < 2:
            continue
        windows = profile[: n_windows * scale].reshape(n_windows, scale)
        t = np.arange(scale)
        # Least-squares detrend each window, then take the RMS residual.
        coeffs = np.polyfit(t, windows.T, 1)
        trend = np.outer(coeffs[0], t) + coeffs[1][:, None]
        residual = windows - trend
        rms = np.sqrt(np.mean(residual**2))
        if rms > 0:
            fluctuations.append(rms)
            usable_scales.append(scale)

    if len(fluctuations) < 4:
        return NAN
    slope = np.polyfit(np.log(usable_scales), np.log(fluctuations), 1)[0]
    return float(slope)


# ---------------------------------------------------------------------------
# stationarity
# ---------------------------------------------------------------------------


def drift_ratio(x: np.ndarray, n_blocks: int = 10) -> float:
    """Between-block variance of the mean, relative to within-block variance.

    A stationary series has block means that vary no more than sampling noise
    allows, giving a ratio near zero. Large values indicate the level itself is
    moving — the regime-shift mechanism that OI-2 warns about, measured on the
    signal rather than assumed from the calendar.
    """
    x = _clean(x)
    if _is_degenerate(x) or x.size < n_blocks * 8:
        return NAN
    usable = (x.size // n_blocks) * n_blocks
    blocks = x[:usable].reshape(n_blocks, -1)
    within = float(np.mean(np.var(blocks, axis=1)))
    between = float(np.var(np.mean(blocks, axis=1)))
    if within <= 0:
        return NAN if between <= 0 else float("inf")
    return float(between / within)


def variance_ratio(x: np.ndarray, lag: int = 8) -> float:
    """Lo-MacKinlay variance ratio.

    ``VR = Var(x_t - x_{t-lag}) / (lag * Var(x_t - x_{t-1}))``. Equals 1 for a
    random walk, below 1 for mean-reverting series, above 1 for trending ones.
    Distinguishes "moves a lot" from "moves unpredictably", which raw variance
    cannot.
    """
    x = _clean(x)
    if _is_degenerate(x) or x.size <= lag + 2:
        return NAN
    d1 = np.diff(x)
    dk = x[lag:] - x[:-lag]
    v1 = np.var(d1)
    if v1 <= 0:
        return NAN
    return float(np.var(dk) / (lag * v1))


# ---------------------------------------------------------------------------
# shape: structural floors on achievable error
# ---------------------------------------------------------------------------


def jump_fraction(x: np.ndarray, threshold_sigma: float = 3.0) -> float:
    """Fraction of steps larger than ``threshold_sigma`` robust deviations.

    Jumps are the part of a signal no smooth model can anticipate: a job starts
    and power steps up. A high jump fraction with otherwise low entropy is the
    signature of an event-driven signal, which is a *different* kind of hard
    from a noisy one.
    """
    x = _clean(x)
    if _is_degenerate(x):
        return NAN
    d = np.diff(x)
    if d.size == 0:
        return NAN

    # The robust scale must be estimated from the SIGNED differences. The
    # 1.4826 factor makes the median absolute deviation a consistent estimator
    # of sigma only for a symmetric distribution; applying it to |d|, which is
    # folded and therefore skewed, understates the scale badly enough to flag
    # roughly 9% of pure Gaussian noise as jumps.
    mad = np.median(np.abs(d - np.median(d)))
    scale = 1.4826 * mad
    if scale <= 0:
        # A series that is constant except for rare moves: every move is a jump.
        return float(np.mean(d != 0.0))
    return float(np.mean(np.abs(d) > threshold_sigma * scale))


def flat_run_fraction(x: np.ndarray) -> float:
    """Fraction of consecutive samples that repeat the previous value.

    Directly measures how much of a signal a persistence forecaster gets right
    for free. Setpoints and configuration registers approach 1.0.
    """
    x = _clean(x)
    if x.size < 2:
        return NAN
    return float(np.mean(np.diff(x) == 0.0))


def longest_flat_run(x: np.ndarray) -> int:
    """Length of the longest constant run, in samples."""
    x = _clean(x)
    if x.size == 0:
        return 0
    if x.size == 1:
        return 1
    changes = np.flatnonzero(np.diff(x) != 0.0)
    boundaries = np.concatenate(([-1], changes, [x.size - 1]))
    return int(np.max(np.diff(boundaries)))


def excess_kurtosis(x: np.ndarray) -> float:
    """Excess kurtosis of the first differences — tail weight of the shocks."""
    x = _clean(x)
    if _is_degenerate(x) or x.size < 8:
        return NAN
    d = np.diff(x)
    if np.std(d) == 0:
        return NAN
    return float(sp_stats.kurtosis(d, fisher=True, bias=False))
