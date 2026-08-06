#!/usr/bin/env python3
"""Stage 11 — does the linking protocol work at all?

The study's headline is a *negative* result: predictability measures do not
transfer across signal families. A negative result carries a standing objection
that no amount of care about the data can answer — **the protocol itself may be
broken.** If leave-one-family-out cross-validation on nineteen features and a
thousand series simply cannot recover a relation, then finding no relation on
M100 says nothing about M100.

This stage answers that objection with synthetic data where the ground truth is
known by construction. Three arms run through the *identical* pipeline the real
study uses — the same measure functions, the same forecast harness, the same
``leave_one_family_out`` — differing only in how the series were generated:

``portable``
    A genuine, portable difficulty law. Every family draws its AR(1)
    persistence from the same range, so a model fitted on other families has
    seen the parameter range it must predict. **The protocol must recover this.**
    If R² here is not clearly positive, the protocol is broken and nothing else
    in the study is interpretable.

``disjoint``
    The same law, but each family occupies its own narrow, non-overlapping band
    of the parameter. The relation is exactly as real as in ``portable``; the
    only difference is that predicting a held-out family requires
    *extrapolating* to a parameter range never seen in training. This is the
    hypothesis for what M100 actually does, and the arm exists to show what that
    situation looks like: R² collapses while the within-family ordering survives.

``no_law``
    Skill is permuted across series, destroying any relation while leaving the
    features, the family sizes, and the skill distribution untouched. **The
    protocol must fail here.** If R² is positive, the procedure manufactures
    signal from nothing.

Together the three arms bracket the real result. A protocol that passes
``portable``, fails ``no_law``, and reproduces the observed M100 signature under
``disjoint`` has been shown to work, and the negative result becomes a statement
about the data rather than about the method.

Output: ``results/tables/protocol_control.csv``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402


def build_series(
    rng: np.random.Generator, phi: float, n: int, *, seasonal_amplitude: float, day: int
) -> np.ndarray:
    """One AR(1) series, optionally with a daily cycle.

    ``phi`` is the single knob that controls how forecastable the series is: at
    0 it is white noise and nothing beats the mean, at 0.99 it is nearly a
    random walk and persistence is near-optimal. Everything else — amplitude,
    offset, the seasonal term — is held fixed within an arm so that ``phi`` is
    the only thing a difficulty law could be about.
    """
    innovations = rng.standard_normal(n)
    y = np.empty(n)
    y[0] = innovations[0]
    for t in range(1, n):
        y[t] = phi * y[t - 1] + innovations[t]
    if seasonal_amplitude > 0 and day > 1:
        y = y + seasonal_amplitude * np.sin(2 * np.pi * np.arange(n) / day)
    return y


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--families", type=int, default=15, help="match the real family count")
    ap.add_argument("--per-family", type=int, default=40)
    ap.add_argument("--length", type=int, default=2000)
    args = ap.parse_args()

    with open(args.conf) as fh:
        conf = yaml.safe_load(fh)
    seed = conf["seed"]
    horizon = conf["forecast"]["horizons"][1]
    day = int(round(86400.0 / conf["analysis_grid"]["step_seconds"]))
    paths.ensure_output_dirs()

    # Imported here so the module docstring above stays the first thing read.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "stage06", Path(__file__).resolve().parent / "06_features.py"
    )
    stage06 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage06)

    from hsf.forecast.harness import iter_evaluations
    from hsf.forecast.models import build_suite
    from hsf.link.analysis import FEATURE_COLUMNS, leave_one_family_out

    rng = np.random.default_rng(seed)

    # Both arms share the SAME series, so any difference between them is caused
    # by the family assignment alone and not by the data.
    phis_portable, phis_disjoint, family_ids = [], [], []
    for family in range(args.families):
        # Disjoint: family k owns a narrow band of phi and no other family
        # overlaps it, so a held-out family is always an extrapolation.
        low = family / args.families
        high = (family + 1) / args.families
        for _ in range(args.per_family):
            phis_portable.append(rng.uniform(0.0, 0.99))
            phis_disjoint.append(rng.uniform(low, high) * 0.99)
            family_ids.append(f"family_{family:02d}")

    models = build_suite(["naive", "statistical"])
    n_origins = conf["forecast"]["rolling_origin"]["n_origins"]
    max_train = conf["forecast"]["rolling_origin"].get("max_train_points")

    def evaluate(phis: list[float]) -> pd.DataFrame:
        rows = []
        generator = np.random.default_rng(seed + 1)
        for index, (phi, family) in enumerate(zip(phis, family_ids, strict=True)):
            y = build_series(generator, phi, args.length, seasonal_amplitude=0.0, day=day)
            record = stage06.measure_series(y, float(conf["analysis_grid"]["step_seconds"]), conf)

            # Real skill from the real harness, m=1 (the conservative
            # denominator the study reports as primary).
            best = -np.inf
            for evaluation in iter_evaluations(
                y,
                models=models,
                horizons=[horizon],
                seasonal_period=1,
                n_origins=n_origins,
                max_train=max_train,
            ):
                if np.isfinite(evaluation.get("mase", np.nan)):
                    best = max(best, 1.0 - evaluation["mase"])
            if not np.isfinite(best):
                continue

            record.update(
                {
                    "origin": family,
                    "best_skill": best,
                    "phi": phi,
                    "index": index,
                    # Synthetic series are complete by construction; the real
                    # pipeline gets this from the series loader, not the measures.
                    "filled_fraction": 0.0,
                }
            )
            rows.append(record)
        return pd.DataFrame(rows)

    columns = [c for c in FEATURE_COLUMNS]
    results = []

    for arm, phis in (("portable", phis_portable), ("disjoint", phis_disjoint)):
        data = evaluate(phis)
        cv = leave_one_family_out(data, feature_columns=columns, family="origin", seed=seed)
        if cv.empty:
            raise SystemExit(
                f"arm {arm!r} produced no usable folds: leave_one_family_out needs at least "
                "30 training and 10 test series per fold. Raise --per-family."
            )
        results.append((arm, data, cv))
        print(f"\n=== arm: {arm} ({len(data)} series) ===")
        print(
            f"mean R^2 {cv.r2_forest.mean():+.3f}  median {cv.r2_forest.median():+.3f}  "
            f"{int((cv.r2_forest > 0).sum())}/{len(cv)} positive  "
            f"within-family rho median {cv.spearman_within.median():+.3f}"
        )

    # Negative control: same features, same families, skill shuffled.
    portable_data = results[0][1].copy()
    shuffle_rng = np.random.default_rng(seed + 2)
    portable_data["best_skill"] = shuffle_rng.permutation(portable_data.best_skill.to_numpy())
    cv_null = leave_one_family_out(
        portable_data, feature_columns=columns, family="origin", seed=seed
    )
    results.append(("no_law", portable_data, cv_null))
    print(f"\n=== arm: no_law ({len(portable_data)} series) ===")
    print(
        f"mean R^2 {cv_null.r2_forest.mean():+.3f}  median {cv_null.r2_forest.median():+.3f}  "
        f"{int((cv_null.r2_forest > 0).sum())}/{len(cv_null)} positive  "
        f"within-family rho median {cv_null.spearman_within.median():+.3f}"
    )

    summary = pd.DataFrame(
        [
            {
                "arm": arm,
                "n_series": len(data),
                "mean_r2_forest": cv.r2_forest.mean(),
                "median_r2_forest": cv.r2_forest.median(),
                "min_r2_forest": cv.r2_forest.min(),
                "families_positive": int((cv.r2_forest > 0).sum()),
                "n_families": len(cv),
                "median_spearman_within": cv.spearman_within.median(),
                "mean_r2_level_corrected": cv.r2_level_corrected.mean(),
            }
            for arm, data, cv in results
        ]
    )
    summary.to_csv(paths.TABLES / "protocol_control.csv", index=False)
    print("\n=== summary ===")
    print(summary.round(3).to_string(index=False))
    print(f"\nWrote protocol_control.csv to {paths.TABLES}")

    # The verdict, stated so a reader does not have to derive it.
    portable_r2 = summary.loc[summary.arm == "portable", "mean_r2_forest"].item()
    null_r2 = summary.loc[summary.arm == "no_law", "mean_r2_forest"].item()
    print("\n=== verdict ===")
    if portable_r2 > 0.3 and null_r2 < 0.05:
        print("Protocol VALIDATED: recovers a portable law, and finds none when none exists.")
    else:
        print(
            "Protocol NOT validated: "
            f"portable arm {portable_r2:+.3f} (want > 0.3), no-law arm {null_r2:+.3f} (want < 0.05)."
            "\nEvery negative result in this study is uninterpretable until this passes."
        )


if __name__ == "__main__":
    main()
