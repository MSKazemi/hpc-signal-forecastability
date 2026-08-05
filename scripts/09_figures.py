#!/usr/bin/env python3
"""Stage 9 — regenerate every figure from committed derived data.

Each figure is built from a committed table, so every visual claim in the paper
is traceable to a number a reader can check. Figures whose inputs do not exist
yet are skipped with a message rather than faked.

Output: ``results/figures/*.pdf``, copied into ``paper/figures/``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.viz import (  # noqa: E402
    CATEGORICAL,
    INK_MUTED,
    INK_PRIMARY,
    apply_style,
    plugin_colour,
    save,
)

PLUGIN_ORDER = ["ipmi", "ganglia", "slurm", "nagios", "vertiv", "schneider", "logics", "weather"]


def fig_coverage(inventory: pd.DataFrame, out: Path) -> None:
    """Metric count per plugin per month.

    Job: change over time across eight identities. A heatmap rather than eight
    lines — the point is the pattern of appearance and disappearance, which
    spaghetti would bury, and magnitude here is a count best read as intensity.
    """
    pivot = inventory.pivot_table(
        index="plugin", columns="archive_month", values="metric", aggfunc="nunique", fill_value=0
    )
    pivot = pivot.reindex([p for p in PLUGIN_ORDER if p in pivot.index])

    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    data = pivot.to_numpy(dtype=float)

    # A linear ramp maps Weather's 10 metrics and Vertiv's 25 to almost the
    # same near-white as an absent month, so "collected, but few metrics" and
    # "not collected at all" become indistinguishable — the precise confusion
    # the caption warns about. A log norm separates them, and absent cells get
    # their own flat grey rather than the bottom of the data ramp.
    cmap = plt.get_cmap("Blues").with_extremes(bad="#efefed")
    mesh = ax.imshow(
        np.where(data > 0, data, np.nan),
        aspect="auto", cmap=cmap,
        norm=LogNorm(vmin=max(1.0, np.nanmin(np.where(data > 0, data, np.nan))),
                     vmax=np.nanmax(data)),
    )

    ax.set_yticks(range(len(pivot.index)), pivot.index)
    step = 3
    ax.set_xticks(
        range(0, len(pivot.columns), step), pivot.columns[::step], rotation=45, ha="right"
    )
    ax.set_xlabel("month")
    ax.grid(False)
    ax.set_title("Metrics collected per plugin per month", loc="left", color=INK_PRIMARY)

    bar = fig.colorbar(mesh, ax=ax, pad=0.015, fraction=0.03)
    bar.set_label("distinct metrics (log)", fontsize=8)
    bar.outline.set_visible(False)

    ax.text(
        0.0, -0.52, "grey = plugin not collected that month",
        transform=ax.transAxes, fontsize=7.5, color=INK_MUTED,
    )
    save(fig, out)


def fig_constant_share(manifest: pd.DataFrame, out: Path) -> None:
    """Share of series that never change, by plugin.

    Job: magnitude comparison across categories -> horizontal bars, sorted,
    every bar directly labelled so the value never depends on reading a colour
    or estimating against a grid line.
    """
    share = (
        manifest.groupby("plugin").is_constant.mean().sort_values() * 100
    )
    counts = manifest.groupby("plugin").size()

    fig, ax = plt.subplots(figsize=(5.4, 2.8))
    colours = [plugin_colour(p) for p in share.index]
    bars = ax.barh(share.index, share.to_numpy(), color=colours, height=0.68)

    for bar, plugin, value in zip(bars, share.index, share.to_numpy(), strict=True):
        ax.text(
            value + 1.2, bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}%  (n={counts[plugin]:,})",
            va="center", fontsize=7.5, color=INK_PRIMARY,
        )

    ax.set_xlim(0, max(share.max() * 1.35, 10))
    ax.set_xlabel("series that are constant over the month (%)")
    ax.set_ylabel("")
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "Much of what is monitored never changes", loc="left", color=INK_PRIMARY
    )
    save(fig, out)


def fig_sampling_irregularity(manifest: pd.DataFrame, out: Path) -> None:
    """Distribution of inter-sample interval variability, by plugin.

    Job: compare distributions -> box plots on a log axis, because the values
    span orders of magnitude. This figure is the evidence for OI-1.

    Plots dt_jitter, the interquartile spread of the interval relative to its
    median, NOT dt_cv. dt_cv is computed over every interval and a single
    multi-day outage inflates it enormously, which made IPMI look like the
    least regular plugin — the opposite of what the dataset documentation
    reports. Outages are a real problem but a different one, and they are
    counted separately as gap_frac.
    """
    usable = manifest[manifest.dt_jitter.notna() & (manifest.dt_jitter > 0)]
    order = [p for p in PLUGIN_ORDER if p in set(usable.plugin)]
    data = [usable.loc[usable.plugin == p, "dt_jitter"].to_numpy() for p in order]

    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    box = ax.boxplot(
        data, orientation="horizontal", tick_labels=order, widths=0.6,
        showfliers=False, patch_artist=True
    )
    for patch, plugin in zip(box["boxes"], order, strict=True):
        patch.set_facecolor(plugin_colour(plugin))
        patch.set_alpha(0.85)
        patch.set_edgecolor("none")
    for element in ("medians", "whiskers", "caps"):
        for artist in box[element]:
            artist.set_color(INK_PRIMARY)
            artist.set_linewidth(1.0)

    ax.set_xscale("log")
    ax.axvline(0.1, color=INK_MUTED, linestyle="--", linewidth=0.9)
    ax.text(0.105, len(order) + 0.35, "regular", fontsize=7.5, color=INK_MUTED)
    ax.set_xlabel("interval jitter: (p75 - p25) / median   (log scale)")
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "Sampling regularity differs by orders of magnitude", loc="left", color=INK_PRIMARY
    )
    save(fig, out)


def fig_predictability_landscape(features: pd.DataFrame, out: Path) -> None:
    """Where each signal family sits in predictability space.

    Job: identity across two continuous measures -> scatter. Entropy is plotted
    against quantisation-independent structure so the OI-11 bias is visible
    rather than hidden.
    """
    usable = features.dropna(subset=["permutation_entropy", "flat_run_fraction"])
    if usable.empty:
        print("  (no usable feature rows; skipping landscape)")
        return

    families = list(usable.groupby("plugin").size().sort_values(ascending=False).index)
    fig, ax = plt.subplots(figsize=(5.6, 4.0))

    for i, plugin in enumerate(families):
        subset = usable[usable.plugin == plugin]
        ax.scatter(
            subset.flat_run_fraction, subset.permutation_entropy,
            s=14, alpha=0.7, linewidths=0.5, edgecolors="white",
            color=plugin_colour(plugin), label=f"{plugin} (n={len(subset)})",
            zorder=3 + i,
        )

    ax.set_xlabel("fraction of steps that repeat the previous value")
    ax.set_ylabel("permutation entropy (0 = ordered, 1 = noise)")
    ax.set_ylim(-0.03, 1.05)
    ax.legend(loc="lower left", ncol=2, fontsize=7)
    ax.set_title("The predictability landscape", loc="left", color=INK_PRIMARY)
    save(fig, out)


def fig_skill_by_tier(skill: pd.DataFrame, out: Path) -> None:
    """Does skill keep improving as models get stronger?

    Job: change across an ordered set of model tiers -> the saturation test
    that the study's central argument depends on.
    """
    tiers = {
        "persistence": "naive", "seasonal_naive": "naive", "drift": "naive", "mean": "naive",
        "theta": "statistical", "ets": "statistical", "ar": "statistical",
        "gbt": "ml",
    }
    usable = skill[skill.mase.notna()].copy()
    if usable.empty:
        print("  (no defined skill; skipping tier figure)")
        return
    usable["tier"] = usable.model.map(tiers)

    order = ["naive", "statistical", "ml"]
    horizons = sorted(usable.horizon.unique())

    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    for i, horizon in enumerate(horizons):
        subset = usable[usable.horizon == horizon]
        medians = [subset.loc[subset.tier == t, "skill"].median() for t in order]
        ax.plot(
            order, medians, marker="o", color=CATEGORICAL[i % len(CATEGORICAL)],
            label=f"h = {horizon}",
        )
        ax.annotate(
            f"h={horizon}", (len(order) - 1, medians[-1]),
            textcoords="offset points", xytext=(6, 0), fontsize=7.5,
            color=CATEGORICAL[i % len(CATEGORICAL)], va="center",
        )

    ax.axhline(0.0, color=INK_MUTED, linewidth=0.9, linestyle="--")
    ax.text(0.02, 0.01, "no better than seasonal naive", fontsize=7.5, color=INK_MUTED)
    ax.set_ylabel("median skill  (1 - MASE)")
    ax.set_xlabel("model tier")
    ax.legend(title="horizon (steps)", loc="best")
    ax.set_title("Does more model capacity buy skill?", loc="left", color=INK_PRIMARY)
    save(fig, out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=paths.FIGURES)
    ap.add_argument("--paper-dir", type=Path, default=paths.PAPER / "figures")
    args = ap.parse_args()

    apply_style()
    paths.ensure_output_dirs()
    args.out.mkdir(parents=True, exist_ok=True)

    built: list[Path] = []

    inventory_path = paths.DERIVED / "inventory.parquet"
    if inventory_path.exists():
        fig_coverage(pd.read_parquet(inventory_path), args.out / "coverage.pdf")
        built.append(args.out / "coverage.pdf")

    if paths.MANIFEST.exists():
        manifest = pd.read_parquet(paths.MANIFEST)
        fig_constant_share(manifest, args.out / "constant_share.pdf")
        fig_sampling_irregularity(manifest, args.out / "sampling_irregularity.pdf")
        built += [args.out / "constant_share.pdf", args.out / "sampling_irregularity.pdf"]

    if paths.FEATURES.exists():
        fig_predictability_landscape(pd.read_parquet(paths.FEATURES), args.out / "landscape.pdf")
        built.append(args.out / "landscape.pdf")
    else:
        print("  (features.parquet missing; skipping landscape)")

    if paths.SKILL.exists():
        fig_skill_by_tier(pd.read_parquet(paths.SKILL), args.out / "skill_by_tier.pdf")
        built.append(args.out / "skill_by_tier.pdf")
    else:
        print("  (skill.parquet missing; skipping tier figure)")

    args.paper_dir.mkdir(parents=True, exist_ok=True)
    for path in built:
        if path.exists():
            shutil.copy2(path, args.paper_dir / path.name)

    print(f"\nBuilt {len(built)} figures in {args.out}")
    for path in built:
        print(f"  {path.name}")


if __name__ == "__main__":
    main()
