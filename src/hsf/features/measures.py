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


def permutation_entropy(
    x: np.ndarray, order: int = 5, delay: int = 1, tie_policy: str = "index", seed: int = 0
) -> float:
    """Normalised permutation entropy (Bandt & Pompe, 2002).

    Counts how evenly the orderings of successive ``order``-tuples are
    distributed. A monotone ramp uses one ordering and scores 0; white noise
    uses all ``order!`` orderings equally and scores 1.

    It is the natural first measure here because it depends only on the *rank*
    pattern of the samples, so it is invariant to the calibration and unit
    differences that separate an IPMI temperature from a Ganglia counter.

    **Ties, and why the convention matters here (OI-11).** When samples inside a
    window are equal, the ordering is not defined by the data and some rule must
    supply one. The standard Bandt-Pompe convention breaks ties by index, which
    manufactures a *consistent* ordering out of no information and so reports the
    series as more ordered than it is. That bias is not incidental on this
    dataset: IPMI temperatures are integers, Schneider registers are fixed-point,
    and roughly a third of Vertiv and Schneider series are outright constant, so
    ties are the common case and their prevalence varies systematically by
    plugin — exactly the axis the study compares along.

    ``tie_policy="random"`` breaks ties uniformly at random instead. A truly
    tie-free series is unaffected; a tie-dominated one moves toward its honest
    (higher) entropy. Both are computed in the pipeline so the family ordering
    can be checked to survive the choice, which is what OI-11's fallback (c)
    asks for. The default stays ``"index"`` so the headline measure remains the
    one the literature defines.
    """
    x = _clean(x)
    n_vectors = x.size - (order - 1) * delay
    if _is_degenerate(x) or n_vectors < 2 or order < 2:
        return NAN

    embedded = np.empty((n_vectors, order))
    for i in range(order):
        embedded[:, i] = x[i * delay : i * delay + n_vectors]

    if tie_policy == "random":
        # Perturb by less than the smallest non-zero gap, so only exact ties are
        # reordered and the genuine ordering of distinct values is untouched.
        finite_gaps = np.diff(np.unique(x))
        smallest = float(finite_gaps.min()) if finite_gaps.size else 1.0
        rng = np.random.default_rng(seed)
        embedded = embedded + rng.uniform(0.0, smallest * 1e-6, size=embedded.shape)
    elif tie_policy != "index":
        raise ValueError(f"unknown tie_policy {tie_policy!r}; use 'index' or 'random'")

    patterns = np.argsort(embedded, axis=1, kind="stable")

    # Encode each permutation as an integer via mixed radix.
    weights = order ** np.arange(order)
    codes = patterns @ weights
    _, counts = np.unique(codes, return_counts=True)

    probabilities = counts / counts.sum()
    entropy = -np.sum(probabilities * np.log(probabilities))
    max_entropy = np.log(float(math.factorial(order)))
    if max_entropy <= 0:
        return NAN
    # Clamp to [0, 1]. A perfectly ordered series gives -sum(1 * log 1) = -0.0,
    # which is numerically zero but prints as "-0.000" and reads like an error
    # in a results table.
    return float(min(1.0, max(0.0, entropy / max_entropy)))


def spectral_entropy(x: np.ndarray, method: str = "welch") -> float:
    """Normalised Shannon entropy of the power spectral density.

    Concentrated spectra (a strong daily cycle) score near 0; flat spectra
    (white noise) score near 1. This is the frequency-domain counterpart to
    permutation entropy and catches periodic structure that rank statistics
    can miss.

    Its complement is exactly the forecastability index :math:`\\Omega` of
    Goerg's Forecastable Component Analysis (JMLR W&CP 28(2), 2013): a flat
    spectrum means nothing to extrapolate, a peaked one means a cycle a model
    can lock onto. Reporting :math:`\\Omega` separately would add a column that
    is ``1 - spectral_entropy`` and no information, so it is not computed.

    **Estimator.** The raw periodogram is not a consistent estimator of the
    spectral density — its variance does not shrink as the series grows, so
    every bin stays noisy however much data there is, and an entropy computed
    over those bins is biased toward the flat (unpredictable) end regardless of
    the signal. Welch's method averages over overlapping segments and *is*
    consistent, at the cost of frequency resolution. ``method="periodogram"``
    keeps the original estimator so the two can be compared directly; the
    default is Welch because a measure whose noise floor does not fall with
    sample size cannot support a between-family comparison.
    """
    x = _clean(x)
    if _is_degenerate(x, minimum=16):
        return NAN
    centred = x - x.mean()
    if method == "welch":
        # Eight segments is the usual variance/resolution compromise; with the
        # 512-sample minimum length of this study that leaves >=128 points per
        # segment, enough to resolve a daily cycle on the 15-minute grid.
        nperseg = int(min(centred.size, max(64, centred.size // 8)))
        _, psd = sp_signal.welch(centred, nperseg=nperseg)
    elif method == "periodogram":
        _, psd = sp_signal.periodogram(centred)
    else:
        raise ValueError(f"unknown method {method!r}; use 'welch' or 'periodogram'")
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


# ---------------------------------------------------------------------------
# direction: monotonicity and counters
#
# Nothing above distinguishes a monotone counter from any other signal, and
# that gap is not academic: the linking analysis' worst held-out family is
# ``error_counter``, where a drift forecast is near-perfect and no measure in
# the suite anticipates it. Permutation entropy actively misleads here — a
# monotone series uses exactly one ordering pattern and therefore scores 0,
# the same value an alarm state scores for the opposite reason (OI-11).
# ---------------------------------------------------------------------------


def monotone_fraction(x: np.ndarray) -> float:
    """How close the series is to moving in one direction only.

    The larger of the up-share and down-share of first differences, ignoring
    exact repeats. A monotone counter scores 1.0; a mean-reverting sensor sits
    near 0.5. Repeats are excluded rather than counted as "not rising" so that
    the measure separates *direction* from *stasis*, which
    :func:`flat_run_fraction` already reports — otherwise a constant series
    would score 1.0 here and be indistinguishable from a ramp.
    """
    x = _clean(x)
    if x.size < 3:
        return NAN
    d = np.diff(x)
    moving = d[d != 0.0]
    if moving.size == 0:
        return NAN
    return float(max(np.mean(moving > 0), np.mean(moving < 0)))


def reset_rate(x: np.ndarray, per: int = 1000) -> float:
    """Counter wraps per ``per`` samples.

    A reset is a downward step larger than the median upward step by a wide
    margin, in a series that otherwise rises. Monitoring counters — bytes sent,
    ECC errors, packets dropped — are trivially forecastable by drift *between*
    resets and discontinuous *at* them, so the reset rate is the part of a
    counter's behaviour a forecaster cannot see coming, and it is the natural
    companion to :func:`monotone_fraction`.

    Returns 0.0 for a series with no downward moves at all, and ``nan`` when the
    series is not predominantly rising, where "reset" has no meaning.
    """
    x = _clean(x)
    if x.size < 3:
        return NAN
    d = np.diff(x)
    up, down = d[d > 0], d[d < 0]
    if up.size == 0 or up.size < down.size:
        return NAN
    if down.size == 0:
        return 0.0
    # A wrap is far larger than an ordinary increment, not merely negative:
    # noisy counters wobble by one unit without having reset.
    threshold = 10.0 * float(np.median(up))
    resets = int(np.count_nonzero(-down > threshold))
    return float(resets * per / d.size)


# ---------------------------------------------------------------------------
# stationarity, formally tested
#
# "HPC signals are non-stationary" is the usual informal explanation for why
# they forecast badly, and until now this study asserted it without a single
# hypothesis test. ADF and KPSS have opposite nulls, so running both classifies
# a series rather than merely scoring it — and the classification is what
# decides whether *drift* or *persistence* is the right naive model, which is
# precisely where the error_counter family breaks the linking analysis.
# ---------------------------------------------------------------------------


def adf_pvalue(x: np.ndarray, max_length: int = 4000) -> float:
    """p-value of the Augmented Dickey-Fuller test. Null: a unit root.

    Small p means the series is stationary around a constant. The lag order is
    chosen by AIC rather than fixed, because cadence varies across this dataset
    and a fixed lag would mean different things in different families.
    """
    from statsmodels.tsa.stattools import adfuller

    x = _clean(x)
    if _is_degenerate(x, minimum=32):
        return NAN
    if x.size > max_length:
        x = x[:max_length]
    try:
        return float(adfuller(x, autolag="AIC")[1])
    except Exception:
        # Near-degenerate series make the regression singular. That is data,
        # not an error: it flows through as nan like every other measure here.
        return NAN


def kpss_pvalue(x: np.ndarray, max_length: int = 4000) -> float:
    """p-value of the KPSS test. Null: stationarity around a constant.

    The complement of :func:`adf_pvalue`: *small* p here means non-stationary.
    statsmodels interpolates from a lookup table and warns when the statistic
    falls outside it; the warning is expected on this data and is suppressed,
    since the clipped p-value is still on the correct side of any threshold
    used to classify the series.
    """
    import warnings

    from statsmodels.tsa.stattools import kpss

    x = _clean(x)
    if _is_degenerate(x, minimum=32):
        return NAN
    if x.size > max_length:
        x = x[:max_length]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return float(kpss(x, regression="c", nlags="auto")[1])
    except Exception:
        return NAN


def stationarity_class(adf_p: float, kpss_p: float, alpha: float = 0.05) -> str:
    """Four-cell classification from the ADF/KPSS pair.

    Running the two tests together is more informative than either alone
    because they disagree in interpretable ways:

    ``stationary``
        ADF rejects the unit root, KPSS does not reject stationarity.
    ``unit_root``
        ADF fails to reject, KPSS rejects — a random walk, where persistence is
        the right baseline and differencing is required before modelling.
    ``both_reject``
        Both reject. Neither simple model fits: usually fractional integration
        or a structural break masquerading as a trend.
    ``inconclusive``
        Neither rejects, which on short or heavily quantised series usually
        means the tests are underpowered rather than that the series is benign.
    """
    if not (np.isfinite(adf_p) and np.isfinite(kpss_p)):
        return "unknown"
    adf_rejects = adf_p < alpha            # rejects "has a unit root"
    kpss_rejects = kpss_p < alpha          # rejects "is stationary"
    if adf_rejects and not kpss_rejects:
        return "stationary"
    if not adf_rejects and kpss_rejects:
        return "unit_root"
    if adf_rejects and kpss_rejects:
        return "both_reject"
    return "inconclusive"


def changepoint_rate(
    x: np.ndarray, per: int = 1000, min_size: int = 10, max_splits: int = 40
) -> float:
    """Mean-shift changepoints per ``per`` samples, by binary segmentation.

    Detected with a least-squares cost and a BIC-style penalty: a split is kept
    only when it reduces the residual sum of squares by more than
    ``sigma^2 * log(n)``, which is the standard penalty for one extra mean
    parameter. ``sigma^2`` is estimated from the first differences rather than
    from the series' own variance, so a series with genuine level shifts does
    not inflate its own detection threshold and hide them.

    This is the measure ``conf/experiment.yaml`` has declared under
    ``features.changepoints`` since the pre-registration without ever being
    implemented. Level shifts are the mechanism by which an exogenous event — a
    job starting, a chiller switching stage — makes a signal unforecastable
    from its own past, so the rate is a direct proxy for that class of
    difficulty.
    """
    x = _clean(x)
    if x.size < 4 * min_size or float(np.ptp(x)) == 0.0:
        return NAN

    n = x.size
    # Robust noise scale: for white noise, var(diff) = 2 * var(x).
    d = np.diff(x)
    sigma2 = float(np.median(np.abs(d - np.median(d))) * 1.4826) ** 2 / 2.0
    if sigma2 <= 0:
        sigma2 = float(np.var(d)) / 2.0
    if sigma2 <= 0:
        return 0.0
    penalty = sigma2 * math.log(n)

    prefix = np.concatenate(([0.0], np.cumsum(x)))
    prefix_sq = np.concatenate(([0.0], np.cumsum(x * x)))

    def cost(a: int, b: int) -> float:
        """Residual sum of squares of x[a:b] about its own mean."""
        length = b - a
        if length <= 0:
            return 0.0
        total = prefix[b] - prefix[a]
        return float(prefix_sq[b] - prefix_sq[a] - total * total / length)

    # Greedy binary segmentation: repeatedly split the segment that gains most.
    segments = [(0, n)]
    found = 0
    while found < max_splits:
        best_gain, best = 0.0, None
        for a, b in segments:
            if b - a < 2 * min_size:
                continue
            base = cost(a, b)
            candidates = np.arange(a + min_size, b - min_size + 1)
            if candidates.size == 0:
                continue
            # Vectorised cost of both halves for every admissible split point.
            left_n = candidates - a
            right_n = b - candidates
            left_sum = prefix[candidates] - prefix[a]
            right_sum = prefix[b] - prefix[candidates]
            left_sq = prefix_sq[candidates] - prefix_sq[a]
            right_sq = prefix_sq[b] - prefix_sq[candidates]
            split_cost = (
                left_sq - left_sum**2 / left_n + right_sq - right_sum**2 / right_n
            )
            gains = base - split_cost
            index = int(np.argmax(gains))
            if gains[index] > best_gain:
                best_gain, best = float(gains[index]), (a, b, int(candidates[index]))
        if best is None or best_gain <= penalty:
            break
        a, b, cut = best
        segments.remove((a, b))
        segments.extend([(a, cut), (cut, b)])
        found += 1

    return float(found * per / n)


# ---------------------------------------------------------------------------
# complexity measures that survive quantisation
#
# Permutation entropy correlates at +0.53 with the log number of distinct
# values (OI-11): it partly measures a sensor's resolution rather than its
# signal. Both measures below are indifferent to how finely the values are
# represented, so they provide a check on that bias rather than repeating it.
# ---------------------------------------------------------------------------


def sample_entropy(
    x: np.ndarray, m: int = 2, r_times_sd: float = 0.2, max_length: int = 2000
) -> float:
    """Sample entropy (Richman & Moorman, 2000): -log P(match extends).

    The negative log probability that two windows which match to within a
    tolerance ``r`` over ``m`` samples still match over ``m + 1``. Low values
    mean the immediate past reliably determines what comes next.

    Unlike permutation entropy it compares *amplitudes* rather than ranks, so
    it does not invent an ordering out of tied values, and unlike approximate
    entropy it excludes self-matches and so is not biased toward regularity on
    short series. Declared in ``conf/experiment.yaml`` since the
    pre-registration; implemented here.

    Quadratic in series length, so the series is truncated to ``max_length``
    consistently across the study.
    """
    x = _clean(x)
    if _is_degenerate(x, minimum=m + 2):
        return NAN
    if x.size > max_length:
        x = x[:max_length]
    sd = float(np.std(x))
    if sd == 0:
        return NAN
    tolerance = r_times_sd * sd

    def matches(width: int) -> int:
        count = x.size - width + 1
        if count < 2:
            return 0
        windows = np.lib.stride_tricks.sliding_window_view(x, width)[:count]
        total = 0
        for i in range(count - 1):
            distance = np.max(np.abs(windows[i + 1 :] - windows[i]), axis=1)
            total += int(np.count_nonzero(distance <= tolerance))
        return total

    b = matches(m)
    a = matches(m + 1)
    if b == 0 or a == 0:
        # No template match at either length: the tolerance is too tight for
        # this series to say anything, which is not the same as zero entropy.
        return NAN
    return float(-math.log(a / b))


def _symbolise(x: np.ndarray, max_alphabet: int = 16) -> tuple[np.ndarray, int]:
    """Map a series to a small integer alphabet, preserving its own resolution.

    A series that is already discrete — an alarm state, an integer temperature,
    a fixed-point register — keeps its own levels when it has few enough of
    them, because binning it further would destroy real structure. A continuous
    series is cut at equal-frequency quantiles, which is the maximum-entropy
    choice and so does not flatter predictability.
    """
    values = np.unique(x)
    if values.size <= max_alphabet:
        return np.searchsorted(values, x), int(values.size)
    edges = np.quantile(x, np.linspace(0, 1, max_alphabet + 1)[1:-1])
    return np.searchsorted(edges, x), max_alphabet


def entropy_rate(x: np.ndarray, max_alphabet: int = 16, max_length: int = 2000,
                 max_match: int = 512) -> float:
    """Lempel-Ziv estimate of the entropy rate, in bits per symbol.

    Uses the Kontoyiannis et al. (1998) estimator
    ``S = n log2(n) / sum_i Lambda_i``, where ``Lambda_i`` is the length of the
    shortest substring starting at position ``i`` that has not appeared before
    it. Long matches mean the past predicts the future and the rate is low.

    Unlike every other complexity measure in this module, the entropy rate has
    an operational meaning: it bounds how well *any* predictor can do
    (:func:`max_predictability`). That is what makes it worth the cost.

    ``max_match`` caps the match length, and the direction of that bias needs
    stating carefully because it runs the *wrong* way for a bound. Capping can
    only shorten matches, which raises the estimated rate and therefore
    **lowers** the derived ceiling — making the bound tighter than the truth,
    which is exactly how an upper bound stops being one. It is set high enough
    that it almost never binds: typical match length is about
    ``log2(n) / S`` symbols, so at ``n = 2000`` and the rates seen in this data
    it sits near 16, far below the cap. A series predictable enough to hit the
    cap would have its ceiling *under*-reported, so the cap is a floor on
    honesty rather than a source of over-claiming.
    """
    x = _clean(x)
    if x.size < 32:
        return NAN
    if x.size > max_length:
        x = x[:max_length]

    symbols, alphabet = _symbolise(x, max_alphabet)
    if alphabet <= 1:
        return 0.0  # a constant series carries no information per symbol

    # A string turns the substring search into a C-speed operation; without it
    # the estimator is unusably slow at these lengths.
    text = "".join(chr(33 + int(s)) for s in symbols)
    n = len(text)

    total = 1  # Lambda_0 is 1 by definition: nothing precedes the first symbol
    for i in range(1, n):
        length = 1
        while length <= max_match and i + length <= n and text[i : i + length] in text[:i]:
            length += 1
        total += length
    if total <= 0:
        return NAN
    return float(n * math.log2(n) / total)


def max_predictability(rate: float, n_states: int) -> float:
    """Fano upper bound on the accuracy of any next-step predictor.

    Solves, for ``Pi``, the limiting case of Fano's inequality used by Song
    et al. (*Science* 327:1018, 2010) to bound the predictability of human
    mobility::

        S = -[Pi log2 Pi + (1-Pi) log2(1-Pi)] + (1-Pi) log2(N-1)

    where ``S`` is the entropy rate in bits per symbol and ``N`` the number of
    distinct states. The result is the largest fraction of next symbols that
    *any* model could get right, given the uncertainty actually present in the
    sequence. It fits no forecaster and so is a property of the signal.

    This is the only measure in the study that yields a *ceiling* rather than a
    score, which is what makes it able to separate "the signal is hard" from
    "our models are weak": a family whose achieved accuracy sits near its own
    ceiling is intrinsically hard, and one far below it is badly modelled.

    **It is an estimate of the ceiling, not a bound, and must never be called
    one.** The Fano solve below is exact given ``rate``, but ``rate`` comes from
    a Lempel-Ziv estimator that is biased *upward* at the series lengths this
    study has, which biases the ceiling *downward*. Measured against Markov
    chains whose true rate is known in closed form, at ``n = 2000``:

    ========  ==========  =========  ==========  ========
    p(stay)   true rate   estimated  true ceil.  estimated
    ========  ==========  =========  ==========  ========
    0.99      0.076       0.127      0.992       0.986
    0.95      0.290       0.348      0.962       0.953
    0.85      0.686       0.712      0.887       0.882
    ========  ==========  =========  ==========  ========

    **The sign of that bias depends on where the source sits, and an earlier
    version of this docstring got it wrong by generalising from the predictable
    end.** Calibrated against a 16-state Markov source at ``n = 2000``:

    ========  ==========  ==========  ==========
    p(stay)   true rate   true ceil.  ceil. error
    ========  ==========  ==========  ==========
    0.05      3.978       0.109       **+0.219**
    0.20      3.741       0.250       **+0.118**
    0.40      3.186       0.438       +0.043
    0.60      2.420       0.625       -0.006
    0.80      1.429       0.812       -0.052
    0.95      0.456       0.953       -0.023
    ========  ==========  ==========  ==========

    The estimator saturates near 3.6 bits: on i.i.d. uniform symbols, whose true
    rate is 4.0, it returns 3.48 at ``n = 1000`` and only 3.62 at
    ``n = 16000``, so the ceiling is over-stated by roughly 0.24 and that error
    does **not** shrink with more data. Near-random series therefore get a
    ceiling that is far too generous, while near-deterministic ones get one
    slightly too tight (which is why 18% of M100 series exceed it).

    What this licenses: within the entropy range M100 actually occupies
    (estimated rates 0.03--2.97 bits), the error is bounded by about
    :math:`\\pm 0.05`, so headroom larger than that is evidence and headroom
    smaller than that is not. It does *not* license reading headroom as a lower
    bound, and it does not license the measure at all on series whose estimated
    rate approaches 3.5 bits.

    Returns 1.0 for a deterministic sequence and 1/N for a maximally uncertain
    one. The right-hand side is monotone decreasing in ``Pi``, so the root is
    unique and a bisection is safe.
    """
    if not np.isfinite(rate) or n_states < 2:
        return NAN
    upper = math.log2(n_states)
    if rate <= 0:
        return 1.0
    if rate >= upper:
        return 1.0 / n_states

    def fano(pi: float) -> float:
        if pi <= 0.0 or pi >= 1.0:
            binary = 0.0
        else:
            binary = -(pi * math.log2(pi) + (1 - pi) * math.log2(1 - pi))
        return binary + (1 - pi) * math.log2(n_states - 1) - rate

    low, high = 1.0 / n_states, 1.0 - 1e-12
    if fano(low) < 0:
        return 1.0 / n_states
    for _ in range(200):
        mid = 0.5 * (low + high)
        if fano(mid) > 0:
            low = mid
        else:
            high = mid
    return float(0.5 * (low + high))


def predictability_ceiling(x: np.ndarray, max_alphabet: int = 16) -> tuple[float, float, int]:
    """Entropy rate, Fano ceiling, and alphabet size for one series.

    Returned together because the ceiling is uninterpretable without the
    alphabet it was computed on: a series binned into two states has a very
    different ceiling from the same series binned into sixteen, and comparing
    families requires knowing which was used.
    """
    x = _clean(x)
    if x.size < 32:
        return NAN, NAN, 0
    _, alphabet = _symbolise(x[: min(x.size, 2000)], max_alphabet)
    if alphabet <= 1:
        # A constant series is perfectly predictable, not undefined. This is not
        # a corner case here: constants run from 8% of out-of-band sensors to
        # 65% of alarm-state signals, so returning nan would silently drop the
        # most predictable third of the sample from any ceiling comparison.
        return 0.0, 1.0, 1
    rate = entropy_rate(x, max_alphabet=max_alphabet)
    return rate, max_predictability(rate, alphabet), alphabet


def symbolic_persistence_accuracy(x: np.ndarray, max_alphabet: int = 16) -> float:
    """Accuracy of "repeat the last symbol", on the alphabet the ceiling uses.

    The ceiling from :func:`max_predictability` is a bound on next-symbol
    accuracy, so comparing anything to it requires an accuracy measured on the
    *same* symbolisation. This supplies one, using persistence — which this
    study finds is the strongest forecaster on this data at every horizon, so it
    is the fair achieved-performance comparator rather than a straw man.

    The pair (achieved, ceiling) is what separates the study's two candidate
    explanations for poor forecast skill. A family sitting near its ceiling is
    at the information limit and no model can help it; a family far below has
    predictability that the models are failing to extract. Neither number alone
    can make that distinction, which is why \\oi{7} went unresolved for so long.
    """
    x = _clean(x)
    if x.size < 32:
        return NAN
    symbols, alphabet = _symbolise(x[: min(x.size, 2000)], max_alphabet)
    if alphabet <= 1:
        return 1.0  # a constant series is repeated correctly every step
    return float(np.mean(symbols[1:] == symbols[:-1]))


def symbolic_markov_accuracy(
    x: np.ndarray, max_alphabet: int = 16, train_fraction: float = 0.5
) -> float:
    """Next-symbol accuracy of a first-order Markov predictor, fitted causally.

    Companion to :func:`symbolic_persistence_accuracy`, and the reason both
    exist. The ceiling from :func:`max_predictability` says how much
    predictability is *present*; persistence says how much the study's best
    forecaster actually *takes*. Neither shows that the difference between them
    is reachable — a gap could in principle be information no estimator can use.

    This is the cheapest possible test of that. The transition matrix is
    estimated on the first ``train_fraction`` of the series and the most likely
    successor is predicted on the remainder, so it is strictly causal and uses
    no more information than persistence does. If even this recovers part of the
    gap, the headroom is real and reachable rather than a defect of the bound.

    Unseen states at prediction time fall back to persistence, which is the
    conservative choice: it cannot invent accuracy the model did not earn.
    """
    x = _clean(x)
    if x.size < 64:
        return NAN
    symbols, alphabet = _symbolise(x[: min(x.size, 2000)], max_alphabet)
    if alphabet <= 1:
        return 1.0

    cut = int(symbols.size * train_fraction)
    if cut < 8 or symbols.size - cut < 8:
        return NAN

    counts = np.zeros((alphabet, alphabet))
    np.add.at(counts, (symbols[: cut - 1], symbols[1:cut]), 1.0)
    seen = counts.sum(axis=1) > 0
    successor = counts.argmax(axis=1)

    current = symbols[cut - 1 : -1]
    actual = symbols[cut:]
    predicted = np.where(seen[current], successor[current], current)
    return float(np.mean(predicted == actual))


def compression_ratio(x: np.ndarray, levels: int = 256, max_length: int = 16384) -> float:
    """Compressed size of the 8-bit-quantised series, as a fraction of raw.

    A crude but assumption-free complexity measure: a general-purpose
    compressor finds repeated motifs, periodicity, and constant runs without
    being told to look for any of them. Constant and step-like series compress
    to almost nothing; white noise barely compresses at all, so the ratio runs
    from near 0 (predictable) to near 1 (not).

    Its value here is that it is *independent of the sensor's resolution* — the
    series is requantised to a fixed 256 levels of its own range first, so a
    16-bit and a 4-bit sensor with the same shape score alike. That makes it a
    control on permutation entropy, which is contaminated by exactly that
    difference (OI-11).
    """
    import zlib

    x = _clean(x)
    if x.size < 16:
        return NAN
    span = float(np.ptp(x))
    if span == 0:
        # A constant series is perfectly predictable; report the floor rather
        # than nan so the constant-heavy families stay in the analysis.
        return 0.0
    if x.size > max_length:
        x = x[:max_length]
    scaled = np.clip(((x - x.min()) / span * (levels - 1)).round(), 0, levels - 1)
    raw = scaled.astype(np.uint8).tobytes()
    return float(len(zlib.compress(raw, 9)) / len(raw))
