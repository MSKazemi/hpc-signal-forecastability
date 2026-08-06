#!/usr/bin/env python3
"""Stage 13 — how close does forecasting get to an information-theoretic ceiling?

OPEN_ISSUES records the irreducible-error floor as planned and never computed.
This stage computes it, in the form the literature uses for symbolic sequences:
the entropy rate of the symbolised series, converted through Fano's inequality
into an upper bound on the fraction of steps any predictor could get right.

The bound is on a *symbolised* series, so it answers "how predictable is the
next bin" rather than "how small can the MASE be". Those are different
questions and the comparison below is therefore indicative, not a bound on the
regression error. Reporting it anyway is worthwhile because a family whose
ceiling is low cannot be rescued by any model, and knowing which families those
are changes where effort should go.

Output: ``results/tables/ceiling.csv`` (committed).
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
from hsf.features.measures import predictability_ceiling  # noqa: E402
from hsf.io.series import load_series  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "experiment.yaml")
    ap.add_argument("--out", type=Path, default=paths.TABLES / "ceiling.csv")
    args = ap.parse_args()

    conf = yaml.safe_load(args.conf.read_text())
    grid = conf["analysis_grid"]["step_seconds"]
    paths.ensure_output_dirs()

    sample = pd.read_csv(paths.DERIVED / "sample.csv")
    groups = list(sample.groupby(["year_month", "plugin", "metric"], observed=True))
    print(f"{len(sample):,} series in {len(groups):,} partitions", flush=True)

    rows: list[dict] = []
    for i, ((ym, plugin, metric), grp) in enumerate(groups, start=1):
        path = (
            paths.INTERIM
            / f"year_month={ym}" / f"plugin={plugin}_pub" / f"metric={metric}" / "a_0.parquet"
        )
        if not path.exists():
            continue
        try:
            series = load_series(
                path, plugin=plugin, metric=metric, year_month=ym,
                entities=set(grp.entity.astype(str)), step_s=grid,
            )
        except Exception:  # noqa: BLE001
            continue
        for s in series:
            finite = s.values[np.isfinite(s.values)]
            if finite.size < conf["features"]["min_length"]:
                continue
            rate, ceiling, alphabet = predictability_ceiling(finite)
            rows.append({
                "plugin": plugin, "metric": metric, "entity": s.entity, "year_month": ym,
                "entropy_rate": rate, "ceiling": ceiling, "alphabet": alphabet,
            })
        if i % 100 == 0:
            print(f"  {i}/{len(groups)}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print(f"\nWrote {args.out} ({len(df):,} series)")

    tax = pd.read_csv(paths.TAXONOMY)
    df = df.merge(tax[["plugin", "metric", "origin"]], on=["plugin", "metric"], how="left")
    per = df.groupby("origin").agg(
        n=("ceiling", "size"), ceiling=("ceiling", "median"), rate=("entropy_rate", "median")
    ).sort_values("ceiling")
    print("\n=== Fano predictability ceiling by family (median) ===")
    print(per.round(3).to_string())
    print(f"\noverall median ceiling {df.ceiling.median():.3f}, "
          f"IQR [{df.ceiling.quantile(.25):.3f}, {df.ceiling.quantile(.75):.3f}]")


if __name__ == "__main__":
    main()
