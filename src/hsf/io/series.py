"""Turning irregular ExaMon partitions into evenly-spaced series.

Every measure and every forecaster in this study assumes a regular grid. The
raw data is not on one: nominal cadences range from 5 seconds to 15 minutes,
and the *actual* intervals wander badly — Ganglia's coefficient of variation
on inter-sample interval exceeds 8 on some metrics against a nominal 20 s.

Resampling is therefore not a formatting step, it is a modelling decision, and
it is made explicitly here rather than implicitly somewhere downstream:

* The grid step is chosen per series from its own **median** observed interval,
  rounded to a sensible unit. Median rather than mean, because outages produce
  enormous gaps that would otherwise define the cadence.
* Aggregation within a bin uses the **mean**, and bins with no observation are
  left as ``nan`` rather than interpolated. Interpolating would invent data and
  would make a badly sampled signal look well behaved, which is precisely the
  confound this study has to keep visible (OI-1).
* The fraction of bins that had to be filled is returned alongside the series,
  so downstream analysis can condition on it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from hsf.io.schema import entity_columns

# Grid steps we are willing to snap to, in seconds. Chosen to match the
# cadences the plugins actually document (5 s SLURM, 10 s Vertiv/Logics,
# 20 s IPMI/Ganglia, 10 min weather, 15 min Nagios and the aggregated arm).
_ALLOWED_STEPS_S = np.array([1, 5, 10, 15, 20, 30, 60, 300, 600, 900, 1800, 3600], dtype=float)


@dataclass
class Series:
    """One regularly-sampled series, plus how much of it is real."""

    plugin: str
    metric: str
    entity: str
    year_month: str
    step_s: float
    values: np.ndarray          # may contain nan where no sample landed
    t_start_ns: int
    filled_fraction: float      # share of grid points with no observation

    @property
    def timestamps_ns(self) -> np.ndarray:
        step_ns = int(self.step_s * 1e9)
        return self.t_start_ns + step_ns * np.arange(self.values.size, dtype=np.int64)

    @property
    def n_observed(self) -> int:
        return int(np.isfinite(self.values).sum())


def snap_step(median_interval_s: float) -> float:
    """Snap a measured cadence to the nearest documented grid step.

    Snapping keeps the grid comparable across the many series of one plugin,
    which matters because horizons are expressed in steps: without it, "12
    steps ahead" would mean a slightly different duration on every node.
    """
    if not np.isfinite(median_interval_s) or median_interval_s <= 0:
        return float("nan")
    ratios = np.abs(np.log(_ALLOWED_STEPS_S / median_interval_s))
    return float(_ALLOWED_STEPS_S[int(np.argmin(ratios))])


def resample_to_grid(
    ts_ns: np.ndarray, values: np.ndarray, step_s: float
) -> tuple[np.ndarray, int, float]:
    """Bin ``values`` onto a regular grid of ``step_s`` seconds.

    Returns ``(gridded_values, t_start_ns, filled_fraction)``. Empty bins are
    ``nan``; they are never interpolated.
    """
    if ts_ns.size == 0 or not np.isfinite(step_s) or step_s <= 0:
        return np.array([]), 0, float("nan")

    step_ns = int(step_s * 1e9)
    t_start = int(ts_ns[0])
    index = (ts_ns - t_start) // step_ns
    n_bins = int(index[-1]) + 1
    if n_bins <= 0:
        return np.array([]), t_start, float("nan")

    finite = np.isfinite(values)
    sums = np.bincount(index[finite], weights=values[finite], minlength=n_bins)
    counts = np.bincount(index[finite], minlength=n_bins)

    gridded = np.full(n_bins, np.nan)
    occupied = counts > 0
    gridded[occupied] = sums[occupied] / counts[occupied]

    return gridded, t_start, float(1.0 - occupied.mean())


def _entity_labels(table: pa.Table, keys: tuple[str, ...]) -> np.ndarray:
    """One ``"a|b"`` label per row identifying its entity."""
    if not keys:
        return np.full(table.num_rows, "__all__", dtype=object)
    if len(keys) == 1:
        return np.asarray([str(v) for v in table[keys[0]].to_pylist()], dtype=object)
    columns = [table[k].to_pylist() for k in keys]
    return np.asarray(
        ["|".join(str(v) for v in row) for row in zip(*columns, strict=True)], dtype=object
    )


def _filter_by_entities(table: pa.Table, keys: tuple[str, ...], entities: set[str]) -> pa.Table:
    """Keep only rows belonging to ``entities``, working entirely in Arrow.

    Entity labels are ``"a|b"`` joins of the key columns. Rather than building
    that string per row, the wanted labels are split back into their per-column
    components and matched with ``is_in`` on each key, which Arrow evaluates
    vectorised. For the single-key case — every plugin except Nagios and
    Logics — this is one membership test.
    """
    if len(keys) == 1:
        keep = pc.is_in(table[keys[0]], value_set=pa.array(sorted(entities)))
        return table.filter(keep)

    # Multi-key: narrow with a cheap membership test on each key, then make the
    # exact label match on what survives, which is a small fraction of rows.
    wanted_parts = [set() for _ in keys]
    for label in entities:
        parts = label.split("|")
        for i, part in enumerate(parts[: len(keys)]):
            wanted_parts[i].add(part)

    keep = None
    for key, allowed in zip(keys, wanted_parts, strict=True):
        mask = pc.is_in(table[key], value_set=pa.array(sorted(allowed)))
        keep = mask if keep is None else pc.and_(keep, mask)
    narrowed = table.filter(keep)
    if narrowed.num_rows == 0:
        return narrowed

    labels = _entity_labels(narrowed, keys)
    exact = np.fromiter((label in entities for label in labels), dtype=bool, count=len(labels))
    return narrowed.filter(pa.array(exact))


def load_series(
    partition_path,
    *,
    plugin: str,
    metric: str,
    year_month: str,
    entities: set[str] | None = None,
    step_s: float | None = None,
) -> list[Series]:
    """Read one partition and return its series on a regular grid.

    ``entities`` restricts the read to a chosen sample, which is how the sweep
    stays affordable: a single Ganglia partition holds nearly a thousand nodes
    and the study forecasts a stratified subset of them.
    """
    schema = pq.read_schema(partition_path)
    keys = entity_columns(plugin, list(schema.names))
    table = pq.read_table(partition_path, columns=["timestamp", "value", *keys])

    # Restrict to the requested entities IN ARROW, before anything becomes a
    # Python object. Building label strings first and filtering afterwards
    # means calling to_pylist() on a column of 234 million values, which
    # allocates a Python string per row; it does not finish in useful time.
    if entities is not None and keys:
        table = _filter_by_entities(table, keys, entities)
        if table.num_rows == 0:
            return []

    ts = (
        table["timestamp"]
        .combine_chunks()
        .cast(pa.timestamp("ns"))
        .to_numpy(zero_copy_only=False)
        .astype("int64", copy=False)
    )
    try:
        values = table["value"].combine_chunks().cast(pa.float64()).to_numpy(zero_copy_only=False)
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError, ValueError):
        return []

    # Safe now: only the selected entities remain, so this is a small column.
    label_array = _entity_labels(table, keys)
    del table

    out: list[Series] = []
    for entity in np.unique(label_array):
        if entities is not None and entity not in entities:
            continue
        mask = label_array == entity
        entity_ts = ts[mask]
        entity_values = values[mask]
        if entity_ts.size < 3:
            continue
        order = np.argsort(entity_ts, kind="stable")
        entity_ts, entity_values = entity_ts[order], entity_values[order]

        if step_s is None:
            intervals = np.diff(entity_ts) / 1e9
            intervals = intervals[intervals > 0]
            if intervals.size == 0:
                continue
            resolved = snap_step(float(np.median(intervals)))
        else:
            resolved = step_s
        if not np.isfinite(resolved):
            continue

        gridded, t_start, filled = resample_to_grid(entity_ts, entity_values, resolved)
        if gridded.size == 0:
            continue
        out.append(
            Series(
                plugin=plugin,
                metric=metric,
                entity=str(entity),
                year_month=year_month,
                step_s=resolved,
                values=gridded,
                t_start_ns=t_start,
                filled_fraction=filled,
            )
        )
    return out
