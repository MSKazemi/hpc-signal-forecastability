"""The tiered forecaster suite.

Tiers of increasing model complexity. What is implemented **today**:

===========  =====================================================
naive        persistence, seasonal naive, drift, training mean
statistical  Theta, damped Holt exponential smoothing, ridge AR(p)
ml           gradient-boosted trees on lagged values
===========  =====================================================

Not yet implemented, and tracked as OI-6: a neural tier (TCN / N-BEATS /
PatchTST). Until it exists, no claim of the form "not even deep models can beat
this" is licensed, and the paper must say only that skill saturates across the
three tiers that were actually run.

Note also that ``ar`` here is a ridge-regularised autoregression, not a full
ARIMA — there is no differencing or moving-average term, and no order
selection. It is a competent linear baseline, not a claim to have run ARIMA.

The tiers exist to support a specific argument. If skill saturates between the
statistical and machine-learning tiers and does not improve further, then model
capacity is not the binding constraint and the ceiling is a property of the
signal. If instead skill climbs steadily with capacity, the study's thesis is
wrong and must be reported as wrong. The suite is therefore designed to be able
to *falsify* the claim, not only to support it.

Every model here is deliberately cheap. This machine has 24 CPU threads and no
GPU, and the sweep covers many thousands of series; a model that cannot fit in
a second is not usable at this scale. The capacity limitation is a stated
threat to validity, not a hidden one.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# tier 1 — naive
# ---------------------------------------------------------------------------


class Persistence:
    """Repeat the last observed value. The reference every forecaster must beat."""

    name = "persistence"

    def fit(self, y: np.ndarray, seasonal_period: int) -> Persistence:
        finite = y[np.isfinite(y)]
        self._last = float(finite[-1]) if finite.size else float("nan")
        return self

    def predict(self, horizon: int) -> np.ndarray:
        return np.full(horizon, self._last)


class SeasonalNaive:
    """Repeat the value from one seasonal period ago.

    This is also the MASE denominator's model, so its skill is near zero by
    construction on the training window. It appears in the suite because on the
    *test* window it can do markedly better or worse than that, and the gap is
    itself informative about seasonal stability.
    """

    name = "seasonal_naive"

    def fit(self, y: np.ndarray, seasonal_period: int) -> SeasonalNaive:
        self._period = seasonal_period if 0 < seasonal_period < y.size else 1
        self._tail = y[-self._period :]
        return self

    def predict(self, horizon: int) -> np.ndarray:
        repeats = int(np.ceil(horizon / self._period))
        return np.tile(self._tail, repeats)[:horizon]


class Drift:
    """Extrapolate the straight line through the first and last training points."""

    name = "drift"

    def fit(self, y: np.ndarray, seasonal_period: int) -> Drift:
        finite = y[np.isfinite(y)]
        if finite.size < 2:
            self._last, self._slope = (
                float(finite[-1]) if finite.size else float("nan"),
                0.0,
            )
        else:
            self._last = float(finite[-1])
            self._slope = (finite[-1] - finite[0]) / (finite.size - 1)
        return self

    def predict(self, horizon: int) -> np.ndarray:
        return self._last + self._slope * np.arange(1, horizon + 1)


class TrainingMean:
    """Predict the training mean.

    Included because for a strongly mean-reverting signal it is genuinely hard
    to beat, and a suite whose weakest member is persistence would overstate
    how much the sophisticated models contribute.
    """

    name = "mean"

    def fit(self, y: np.ndarray, seasonal_period: int) -> TrainingMean:
        finite = y[np.isfinite(y)]
        self._mean = float(finite.mean()) if finite.size else float("nan")
        return self

    def predict(self, horizon: int) -> np.ndarray:
        return np.full(horizon, self._mean)


# ---------------------------------------------------------------------------
# tier 2 — statistical
# ---------------------------------------------------------------------------


class Theta:
    """The Theta method (Assimakopoulos & Nikolopoulos, 2000).

    Winner of the M3 competition and still a strong baseline. Implemented
    directly as simple exponential smoothing of the series plus half the
    ordinary-least-squares drift, which is the standard equivalence.
    """

    name = "theta"

    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha

    def fit(self, y: np.ndarray, seasonal_period: int) -> Theta:
        finite = y[np.isfinite(y)]
        if finite.size < 3:
            self._level, self._slope = (
                float(finite[-1]) if finite.size else float("nan"),
                0.0,
            )
            return self

        t = np.arange(finite.size)
        slope = np.polyfit(t, finite, 1)[0]

        level = float(finite[0])
        for value in finite[1:]:
            level = self.alpha * value + (1 - self.alpha) * level

        self._level = level
        self._slope = float(slope) * 0.5
        return self

    def predict(self, horizon: int) -> np.ndarray:
        return self._level + self._slope * np.arange(1, horizon + 1)


class ExponentialSmoothing:
    """Holt's linear trend method with damping.

    Damping matters for this data: undamped trends extrapolate a warming node
    to implausible temperatures over a 24-hour horizon.
    """

    name = "ets"

    def __init__(self, alpha: float = 0.3, beta: float = 0.1, phi: float = 0.95):
        self.alpha, self.beta, self.phi = alpha, beta, phi

    def fit(self, y: np.ndarray, seasonal_period: int) -> ExponentialSmoothing:
        finite = y[np.isfinite(y)]
        if finite.size < 2:
            self._level, self._trend = (
                float(finite[-1]) if finite.size else float("nan"),
                0.0,
            )
            return self

        level = float(finite[0])
        trend = float(finite[1] - finite[0])
        for value in finite[1:]:
            previous = level
            level = self.alpha * value + (1 - self.alpha) * (level + self.phi * trend)
            trend = self.beta * (level - previous) + (1 - self.beta) * self.phi * trend

        self._level, self._trend = level, trend
        return self

    def predict(self, horizon: int) -> np.ndarray:
        steps = np.arange(1, horizon + 1)
        # Damped trend: the sum of a geometric series in phi.
        damping = np.cumsum(self.phi**steps)
        return self._level + self._trend * damping


class AutoRegressive:
    """AR(p) fitted by ordinary least squares, forecast recursively.

    Ridge-regularised because many series here are near-constant or heavily
    quantised, which makes the normal equations singular often enough that an
    unregularised solve would fail on a large fraction of the sweep.
    """

    name = "ar"

    def __init__(self, order: int = 24, ridge: float = 1e-6):
        self.order, self.ridge = order, ridge

    def fit(self, y: np.ndarray, seasonal_period: int) -> AutoRegressive:
        finite = y[np.isfinite(y)]
        p = min(self.order, max(1, finite.size // 4))
        self._p = p

        if finite.size <= p + 1:
            self._coef = np.zeros(p)
            self._intercept = float(finite[-1]) if finite.size else float("nan")
            self._history = finite
            return self

        # Centre before solving so the intercept is well conditioned.
        self._mean = float(finite.mean())
        centred = finite - self._mean

        n_rows = centred.size - p
        design = np.lib.stride_tricks.sliding_window_view(centred[:-1], p)[-n_rows:]
        target = centred[p:]

        gram = design.T @ design + self.ridge * np.eye(p) * max(1.0, design.size)
        self._coef = np.linalg.solve(gram, design.T @ target)
        self._intercept = 0.0
        self._history = centred[-p:]
        return self

    def predict(self, horizon: int) -> np.ndarray:
        history = list(self._history)
        out = []
        for _ in range(horizon):
            window = np.array(history[-self._p :])
            if window.size < self._p:
                window = np.pad(window, (self._p - window.size, 0))
            nxt = float(window[::-1] @ self._coef) + self._intercept
            out.append(nxt)
            history.append(nxt)
        return np.array(out) + getattr(self, "_mean", 0.0)


# ---------------------------------------------------------------------------
# tier 3 — machine learning
# ---------------------------------------------------------------------------


class GradientBoostedLags:
    """Gradient-boosted trees on lagged values, forecast recursively.

    Uses scikit-learn's histogram-based implementation so the suite has no
    dependency beyond the core set. Direct multi-horizon models would be
    stronger, but recursive forecasting keeps a single fitted model per series
    and the sweep affordable; the choice is recorded as a limitation.
    """

    name = "gbt"

    def __init__(self, n_lags: int = 24, max_iter: int = 60, seed: int = 0):
        self.n_lags, self.max_iter, self.seed = n_lags, max_iter, seed

    def fit(self, y: np.ndarray, seasonal_period: int) -> GradientBoostedLags:
        from sklearn.ensemble import HistGradientBoostingRegressor

        finite = y[np.isfinite(y)]
        p = min(self.n_lags, max(1, finite.size // 4))
        self._p = p

        if finite.size <= p + 8 or np.ptp(finite) == 0:
            self._model = None
            self._fallback = float(finite[-1]) if finite.size else float("nan")
            self._history = finite
            return self

        n_rows = finite.size - p
        design = np.lib.stride_tricks.sliding_window_view(finite[:-1], p)[-n_rows:]
        target = finite[p:]

        self._model = HistGradientBoostingRegressor(
            max_iter=self.max_iter,
            learning_rate=0.1,
            early_stopping=False,
            random_state=self.seed,
        ).fit(design, target)
        self._history = finite[-p:]
        return self

    def predict(self, horizon: int) -> np.ndarray:
        if self._model is None:
            return np.full(horizon, self._fallback)
        history = list(self._history)
        out = []
        for _ in range(horizon):
            window = np.array(history[-self._p :]).reshape(1, -1)
            nxt = float(self._model.predict(window)[0])
            out.append(nxt)
            history.append(nxt)
        return np.array(out)


# ---------------------------------------------------------------------------
# suite assembly
# ---------------------------------------------------------------------------

NAIVE_TIER = (Persistence, SeasonalNaive, Drift, TrainingMean)
STATISTICAL_TIER = (Theta, ExponentialSmoothing, AutoRegressive)
ML_TIER = (GradientBoostedLags,)

TIERS: dict[str, tuple] = {
    "naive": NAIVE_TIER,
    "statistical": STATISTICAL_TIER,
    "ml": ML_TIER,
}


def build_suite(tiers: list[str] | None = None) -> list:
    """Instantiate one forecaster per model in the requested tiers."""
    selected = tiers or list(TIERS)
    return [cls() for tier in selected for cls in TIERS[tier]]
