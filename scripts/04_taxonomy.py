#!/usr/bin/env python3
"""Stage 4 — apply the a-priori taxonomy to every series in the census.

Labels come from ``hsf.taxonomy``, which reads only the plugin and metric
*name*. No value, no cadence, no predictability measure is consulted, so the
labels cannot have been fitted to the results they are later used to explain.

Output: ``data/derived/taxonomy.csv`` (committed) — one row per distinct
(plugin, metric) pair, plus a coverage report over the census.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.taxonomy import classify, scope_for  # noqa: E402


def build(manifest: pd.DataFrame) -> pd.DataFrame:
    pairs = manifest[["plugin", "metric"]].drop_duplicates().sort_values(["plugin", "metric"])
    rows = []
    for plugin, metric in pairs.itertuples(index=False):
        label = classify(plugin, metric)
        rows.append(
            {
                "plugin": plugin,
                "metric": metric,
                "origin": label.origin,
                "value_kind": label.value_kind,
                "scope": scope_for(plugin),
                "controlled": label.controlled,
                "rule": label.rule,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=paths.MANIFEST)
    ap.add_argument("--out", type=Path, default=paths.TAXONOMY)
    args = ap.parse_args()

    paths.ensure_output_dirs()
    manifest = pd.read_parquet(args.manifest, columns=["plugin", "metric"])
    taxonomy = build(manifest)
    taxonomy.to_csv(args.out, index=False)

    print(f"Labelled {len(taxonomy):,} (plugin, metric) pairs -> {args.out}\n")

    print("=== origin x plugin ===")
    print(
        pd.crosstab(taxonomy.origin, taxonomy.plugin).to_string()
    )
    print("\n=== value_kind ===")
    print(taxonomy.value_kind.value_counts().to_string())
    print("\n=== controlled ===")
    print(taxonomy.controlled.value_counts().to_string())

    fallback = taxonomy[taxonomy.rule.str.startswith("plugin-default")]
    print(f"\n=== fell through to a plugin default: {len(fallback)} pairs ===")
    if len(fallback):
        by_plugin = fallback.groupby("plugin").metric.apply(list)
        for plugin, metrics in by_plugin.items():
            shown = ", ".join(metrics[:12])
            more = f" (+{len(metrics) - 12} more)" if len(metrics) > 12 else ""
            print(f"  {plugin}: {shown}{more}")


if __name__ == "__main__":
    main()
