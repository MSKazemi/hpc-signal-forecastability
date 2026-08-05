"""Rolling-origin evaluation harness.

The study's claim is that forecast skill is bounded by properties of the signal
rather than by the forecaster. That claim is only worth anything if the skill
numbers are honest, so this module is deliberately strict:

* Every split is verified to be strictly causal before it is used. A model
  never sees a sample at or after the origin it forecasts from.
* Errors are scaled by a denominator computed **from the training window only**.
  Scaling by test-set statistics is the most common silent leak in forecasting
  benchmarks and it flatters every model equally, which would hide exactly the
  effect being measured.
* Skill is reported per (series, model, horizon, origin). Aggregation happens
  later, in the analysis, never here — a mean computed too early cannot be
  un-computed.

Metric
------
MASE (Hyndman & Koehler, 2006): mean absolute error divided by the mean
absolute error of an in-sample seasonal naive forecast. It is scale-free, which
is mandatory here — a benchmark spanning watts, degrees Celsius, RPM, packets
per second, and monotone energy counters cannot be averaged in raw units.

``skill = 1 - MASE``: positive means better than seasonal naive, zero means no
better, negative means worse.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class LeakageError(AssertionError):
    """Raised when a split would let a model see the future."""


class Forecaster(Protocol):
    """Minimal forecaster interface.

    ``fit`` receives only the training window. ``predict`` receives only a
    horizon length. There is deliberately no way to pass test data in.
    """

    name: str

    def fit(self, y: np.ndarray, seasonal_period: int) -> Forecaster: ...

    def predict(self, horizon: int) -> np.ndarray: ...


@dataclass(frozen=True)
class Split:
    """One rolling-origin split: train on ``[0, origin)``, score ``[origin, origin+h)``."""

    origin: int
    horizon: int

    @property
    def test_slice(self) -> slice:
        return slice(self.origin, self.origin + self.horizon)


def rolling_origins(
    n: int,
    *,
    horizons: Sequence[int],
    n_origins: int,
    min_train_fraction: float = 0.5,
) -> list[Split]:
    """Evenly spaced origins that leave room for the longest horizon.

    The first origin sits at ``min_train_fraction`` of the series so that even
    the earliest split has a usable training window; the last leaves exactly
    enough room to score the longest horizon.
    """
    max_horizon = max(horizons)
    first = int(n * min_train_fraction)
    last = n - max_horizon
    if last <= first:
        return []

    if n_origins == 1:
        origin_points = [last]
    else:
        origin_points = np.unique(np.linspace(first, last, n_origins).astype(int)).tolist()

    return [Split(origin=int(o), horizon=int(h)) for o in origin_points for h in horizons]


def assert_causal(split: Split, n: int, timestamps: np.ndarray | None = None) -> None:
    """Fail loudly if a split is not strictly causal.

    Called for every split of every series. The cost is negligible next to
    fitting a model, and a benchmark that silently leaks is worse than no
    benchmark.
    """
    if split.origin <= 0:
        raise LeakageError(f"origin {split.origin} leaves no training data")
    if split.origin + split.horizon > n:
        raise LeakageError(
            f"origin {split.origin} + horizon {split.horizon} exceeds series length {n}"
        )
    if timestamps is not None:
        train_end = timestamps[split.origin - 1]
        test_start = timestamps[split.origin]
        if not train_end < test_start:
            raise LeakageError(
                f"training window ends at {train_end} but the test window starts at "
                f"{test_start}; timestamps must be strictly increasing"
            )


def mase_denominator(
    train: np.ndarray, seasonal_period: int, *, relative_floor: float = 1e-8
) -> float:
    """In-sample mean absolute seasonal-naive error of the *training* window.

    Computed from training data only — this is the whole point.

    Returns nan when the denominator is degenerate, which happens far more often
    in this dataset than in a typical forecasting benchmark:

    * a **constant** window gives a denominator of exactly zero, and roughly a
      third of the Vertiv and Schneider series are constant;
    * a **near-perfectly periodic** window gives a denominator at the level of
      floating-point noise (order 1e-16), which does not raise anything but
      turns MASE into an arbitrary ratio of two rounding errors.

    Both cases mean the same thing — seasonal naive is already essentially
    perfect, so "how many times better than seasonal naive" has no content. The
    honest answer is "undefined", not a large number. The denominator is
    therefore required to exceed ``relative_floor`` times the training range;
    otherwise nan is returned and the series is excluded from skill statistics
    rather than contributing a spurious value.
    """
    m = seasonal_period if 0 < seasonal_period < train.size else 1
    diffs = np.abs(train[m:] - train[:-m])
    diffs = diffs[np.isfinite(diffs)]
    if diffs.size == 0:
        return float("nan")

    denominator = float(diffs.mean())
    if denominator <= 0:
        return float("nan")

    finite = train[np.isfinite(train)]
    scale = float(np.ptp(finite)) if finite.size else 0.0
    if scale > 0 and denominator < relative_floor * scale:
        return float("nan")
    return denominator


def mase(actual: np.ndarray, predicted: np.ndarray, denominator: float) -> float:
    """Mean absolute scaled error for one forecast window."""
    if not np.isfinite(denominator) or denominator <= 0:
        return float("nan")
    errors = np.abs(actual - predicted)
    errors = errors[np.isfinite(errors)]
    if errors.size == 0:
        return float("nan")
    return float(errors.mean() / denominator)


def iter_evaluations(
    y: np.ndarray,
    *,
    models: Sequence[Forecaster],
    horizons: Sequence[int],
    seasonal_period: int,
    n_origins: int,
    min_train_fraction: float = 0.5,
    timestamps: np.ndarray | None = None,
) -> Iterator[dict]:
    """Evaluate every model at every horizon from every origin.

    Yields one record per (model, horizon, origin). Models are re-fitted at each
    origin on that origin's training window, which is the expensive but correct
    choice: fitting once on the full series and predicting backwards would leak.

    A model that raises is recorded with ``mase = nan`` and its error message,
    rather than aborting the run — a single ill-conditioned ARIMA must not
    destroy a sweep over hundreds of thousands of series.
    """
    n = y.size
    splits = rolling_origins(
        n, horizons=horizons, n_origins=n_origins, min_train_fraction=min_train_fraction
    )

    # Group by origin so each training window is prepared once per model.
    origins = sorted({s.origin for s in splits})
    horizons_by_origin: dict[int, list[int]] = {
        o: sorted(s.horizon for s in splits if s.origin == o) for o in origins
    }

    for origin in origins:
        train = y[:origin]
        if train.size < 2 or not np.isfinite(train).any():
            continue
        denominator = mase_denominator(train, seasonal_period)
        origin_horizons = horizons_by_origin[origin]
        max_h = max(origin_horizons)

        for model in models:
            try:
                fitted = model.fit(train, seasonal_period)
                prediction = np.asarray(fitted.predict(max_h), dtype=np.float64)
                if prediction.size != max_h:
                    raise ValueError(
                        f"{model.name} returned {prediction.size} points for horizon {max_h}"
                    )
                error = None
            except Exception as exc:  # noqa: BLE001 - one bad fit must not kill the sweep
                prediction = np.full(max_h, np.nan)
                error = f"{type(exc).__name__}: {exc}"

            for horizon in origin_horizons:
                split = Split(origin=origin, horizon=horizon)
                assert_causal(split, n, timestamps)
                actual = y[split.test_slice]
                yield {
                    "model": model.name,
                    "origin": origin,
                    "horizon": horizon,
                    "n_train": int(train.size),
                    "mase": mase(actual, prediction[:horizon], denominator),
                    "mase_denominator": denominator,
                    "error": error,
                }
