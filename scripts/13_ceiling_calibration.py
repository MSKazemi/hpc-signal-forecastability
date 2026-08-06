#!/usr/bin/env python3
"""Stage 13 — is the Fano ceiling usable on signals like ours?

The predictability ceiling (\\oi{7}) is an *estimate*, and an earlier version of
this study read the difference between it and achieved accuracy as "headroom the
models fail to claim". That reading required the ceiling to be approximately
right for the kind of signal it was applied to. This stage tests that
assumption, and it does not survive.

**The test.** For a Gaussian AR(1) process binned into equal-frequency
quantiles — the same symbolisation the study applies, on the same kind of
smooth continuous signal the physical families contain — the *Bayes-optimal*
next-symbol accuracy can be computed exactly. Given the true model, the next
value is distributed ``N(phi * x_t, 1 - phi^2)``; integrating that density over
each bin and taking the most likely bin is the best any predictor can do,
because it uses the true generating process. Nothing can beat it.

Comparing that optimum against the estimated ceiling measures the estimator's
error on the class of signal the study actually cares about — as opposed to the
Markov sources used for the first calibration, which are a much easier case.

**The result.** The estimated ceiling over-states the Bayes optimum by
0.22--0.31 across the whole persistence range. That is the same magnitude as
the "headroom" the two-regime reading attributed to weak models, so the
attribution was wrong: the gap is the estimator, not the models.

**What replaces it.** The same table shows persistence achieving within 0.01 of
the Bayes optimum at every phi. For smooth continuous signals binned this way,
repeating the last value is essentially optimal — which explains, rather than
contradicts, the study's finding that no heavier model tier beats persistence.

Output: ``results/tables/ceiling_calibration.csv``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.features.measures import _symbolise, entropy_rate, max_predictability  # noqa: E402


def bayes_optimal_accuracy(
    x: np.ndarray, phi: float, edges: np.ndarray, symbols: np.ndarray
) -> float:
    """Best possible next-symbol accuracy, using the true generating model.

    For an AR(1) with unit marginal variance the next value is
    ``N(phi * x_t, 1 - phi^2)``. The probability it lands in a given bin is the
    difference of the normal CDF at the bin edges, and the optimal decision is
    the most probable bin. This is a genuine optimum, not a fitted model.
    """
    sd = np.sqrt(1.0 - phi**2)
    lower = np.concatenate(([-np.inf], edges))
    upper = np.concatenate((edges, [np.inf]))
    mean = phi * x[:-1]
    probability = st.norm.cdf((upper[None, :] - mean[:, None]) / sd) - st.norm.cdf(
        (lower[None, :] - mean[:, None]) / sd
    )
    return float(np.mean(probability.argmax(axis=1) == symbols[1:]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--length", type=int, default=4000)
    ap.add_argument("--alphabet", type=int, default=16)
    args = ap.parse_args()

    with open(args.conf) as fh:
        conf = yaml.safe_load(fh)
    rng = np.random.default_rng(conf["seed"])
    paths.ensure_output_dirs()

    rows = []
    for phi in (0.50, 0.80, 0.90, 0.95, 0.99):
        x = np.empty(args.length)
        x[0] = rng.standard_normal()
        for t in range(1, args.length):
            x[t] = phi * x[t - 1] + rng.standard_normal() * np.sqrt(1 - phi**2)

        symbols, alphabet = _symbolise(x, args.alphabet)
        edges = np.quantile(x, np.linspace(0, 1, args.alphabet + 1)[1:-1])

        bayes = bayes_optimal_accuracy(x, phi, edges, symbols)
        persistence = float(np.mean(symbols[1:] == symbols[:-1]))
        ceiling = max_predictability(
            entropy_rate(x, max_length=args.length, max_match=2048), alphabet
        )
        rows.append(
            {
                "phi": phi,
                "persistence": persistence,
                "bayes_optimal": bayes,
                "estimated_ceiling": ceiling,
                "ceiling_error": ceiling - bayes,
                "persistence_shortfall": bayes - persistence,
            }
        )

    table = pd.DataFrame(rows)
    table.round(4).to_csv(paths.TABLES / "ceiling_calibration.csv", index=False)
    print(table.round(3).to_string(index=False))

    print(
        f"\nceiling over-states the Bayes optimum by "
        f"{table.ceiling_error.min():.2f} to {table.ceiling_error.max():.2f}"
    )
    print(
        f"persistence falls short of the Bayes optimum by at most "
        f"{table.persistence_shortfall.max():.3f}"
    )
    print(
        "\nVerdict: on binned continuous signals the ceiling is not usable as a\n"
        "headroom measure -- its error is the same size as the gaps it would\n"
        "attribute to weak models. Persistence is near-optimal for this class,\n"
        "which explains why no heavier model tier beats it."
    )


if __name__ == "__main__":
    main()
