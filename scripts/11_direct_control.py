#!/usr/bin/env python3
"""Stage 11 — control: is the capacity result an artefact of recursive forecasting?

Every learned model in the main suite forecasts recursively, so error compounds
over multi-step horizons. The observed collapse of the machine-learning and
neural tiers at long horizons could therefore be that compounding rather than
anything about the signals. This is the single most plausible alternative
explanation for the paper's capacity finding, and a caveat is not a test.

This script settles it by fitting the SAME gradient-boosted learner two ways on
the same series, origins and horizons: recursively, and directly for each
horizon. If the direct variant also loses to persistence, recursion was not the
explanation.

Output: ``results/tables/direct_vs_recursive.csv`` (committed).
"""

from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.forecast.harness import mase, mase_denominator, rolling_origins  # noqa: E402
from hsf.forecast.models import (  # noqa: E402
    DirectGradientBoosted,
    GradientBoostedLags,
    Persistence,
)
from hsf.io.series import load_series  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--n-series", type=int, default=120, help="series to run the control on")
    args = ap.parse_args()

    conf = yaml.safe_load(args.conf.read_text())
    grid = conf["analysis_grid"]["step_seconds"]
    horizons = conf["forecast"]["horizons"]
    rolling = conf["forecast"]["rolling_origin"]
    paths.ensure_output_dirs()

    sample = pd.read_csv(paths.DERIVED / "sample.csv")
    # Deterministic slice across strata, same spirit as the main subset.
    sample = (
        sample.sort_values(["plugin", "metric", "entity"])
        .groupby(["plugin", "origin"], observed=True)
        .head(3)
        .head(args.n_series)
    )
    print(f"direct-vs-recursive control on {len(sample):,} series", flush=True)

    rows: list[dict] = []
    for i, g in enumerate(sample.itertuples(), start=1):
        path = (
            paths.INTERIM
            / f"year_month={g.year_month}"
            / f"plugin={g.plugin}_pub"
            / f"metric={g.metric}"
            / "a_0.parquet"
        )
        if not path.exists():
            continue
        try:
            series = load_series(
                path,
                plugin=g.plugin,
                metric=g.metric,
                year_month=g.year_month,
                entities={str(g.entity)},
                step_s=grid,
            )
        except Exception:  # noqa: BLE001
            continue
        if not series:
            continue

        y = series[0].values
        finite = np.isfinite(y)
        pad = np.concatenate(([False], finite, [False]))
        edges = np.flatnonzero(pad[1:] != pad[:-1])
        if edges.size == 0:
            continue
        starts, ends = edges[0::2], edges[1::2]
        best = int(np.argmax(ends - starts))
        y = y[starts[best] : ends[best]]
        if y.size < conf["features"]["min_length"]:
            continue

        splits = rolling_origins(
            y.size,
            horizons=horizons,
            n_origins=rolling["n_origins"],
            min_train_fraction=rolling["min_train_fraction"],
        )
        max_train = rolling.get("max_train_points")

        for split in splits:
            start = max(0, split.origin - max_train) if max_train else 0
            train = y[start : split.origin]
            actual = y[split.test_slice]
            denom = mase_denominator(train, 1)
            if not np.isfinite(denom):
                continue

            scores = {}
            for name, model in (
                ("persistence", Persistence()),
                ("gbt_recursive", GradientBoostedLags()),
                ("gbt_direct", DirectGradientBoosted().set_horizon(split.horizon)),
            ):
                try:
                    pred = model.fit(train, 1).predict(split.horizon)
                    scores[name] = mase(actual, np.asarray(pred, float), denom)
                except Exception:  # noqa: BLE001
                    scores[name] = float("nan")

            rows.append(
                {
                    "plugin": g.plugin,
                    "metric": g.metric,
                    "entity": g.entity,
                    "horizon": split.horizon,
                    "origin": split.origin,
                    **{f"mase_{k}": v for k, v in scores.items()},
                }
            )
        if i % 25 == 0:
            print(f"  {i}/{len(sample)} series", flush=True)

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("control produced no rows")

    for k in ("persistence", "gbt_recursive", "gbt_direct"):
        df[f"skill_{k}"] = 1.0 - df[f"mase_{k}"]

    summary = (
        df.groupby("horizon")[
            ["skill_persistence", "skill_gbt_recursive", "skill_gbt_direct"]
        ]
        .median()
        .round(4)
    )
    summary["n"] = df.groupby("horizon").size()
    out = paths.TABLES / "direct_vs_recursive.csv"
    summary.to_csv(out)

    print(f"\nWrote {out}\n")
    print("=== median skill (1 - MASE), same-step denominator ===")
    print(summary.to_string())
    print("\nDoes forecasting DIRECTLY rescue the learned model?")
    for h in summary.index:
        r, d, p = (
            summary.loc[h, "skill_gbt_recursive"],
            summary.loc[h, "skill_gbt_direct"],
            summary.loc[h, "skill_persistence"],
        )
        verdict = "direct still loses to persistence" if d < p else "DIRECT BEATS PERSISTENCE"
        print(
            f"  h={h:3d}: recursive {r:+.3f}  direct {d:+.3f}  "
            f"persistence {p:+.3f}  -> {verdict}"
        )


if __name__ == "__main__":
    main()
