"""The fixed entity panel.

M100 has roughly 980 compute nodes, and the extracted partitions hold about 55
billion rows in total. Describing and forecasting every node of every metric is
neither affordable nor necessary: node-level series of the same metric are
highly redundant, since nodes share racks, inlet air, cooling zones, and
workload (which is also why they are not independent samples — OI-9).

This module therefore fixes a **panel**: a bounded subset of entities, chosen
once and used everywhere. Two properties make it a defensible sample rather
than a convenience:

*Deterministic.* Membership is a stable hash of the entity label and the
project seed. It does not depend on file order, row order, or how many workers
ran, so a re-run reproduces the same panel exactly, and so does anyone else's.

*Consistent across metrics and months.* Because the hash sees only the label,
node 142 is either in the panel for every metric and every month, or in none.
That turns the panel into a genuine longitudinal panel: cross-metric
comparisons are made on the same physical machines rather than on a different
random slice each time, which removes a confound the study would otherwise have
to carry.

The panel is a two-stage sample — entities here, then series in
``scripts/05_sample.py`` — and is reported as such.
"""

from __future__ import annotations

import hashlib

import numpy as np


def _rank_key(label: str, seed: int) -> int:
    """Stable 64-bit hash of a label under a seed.

    Uses blake2b rather than Python's ``hash``, which is randomised per process
    and would silently produce a different panel in every worker.
    """
    digest = hashlib.blake2b(f"{seed}:{label}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def select_panel(labels, max_entities: int, seed: int) -> set[str]:
    """The ``max_entities`` labels with the smallest hash, as a set.

    Returns every label when there are no more than ``max_entities`` of them,
    so small plugins — Vertiv's 25 devices, Schneider's two panels, Weather's
    single facility series — are never sampled at all.
    """
    unique = sorted({str(x) for x in labels})
    if max_entities <= 0 or len(unique) <= max_entities:
        return set(unique)
    ranked = sorted(unique, key=lambda label: _rank_key(label, seed))
    return set(ranked[:max_entities])


def panel_mask(labels: np.ndarray, panel: set[str]) -> np.ndarray:
    """Boolean mask selecting rows whose entity is in ``panel``."""
    return np.fromiter((str(x) in panel for x in labels), dtype=bool, count=len(labels))
