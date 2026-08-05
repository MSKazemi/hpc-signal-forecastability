"""Per-series census.

A *series* here is one ``(plugin, metric, entity, month)`` tuple — for example
node 142's inlet temperature in August 2021. For each one the census records
what it is and how well it was observed, which is exactly the information the
predictability analysis later needs to tell "this signal is intrinsically hard"
apart from "this signal was measured badly" (OI-1).

Nothing here fits a model or looks at predictability; it is pure description.

Memory
------
The largest Ganglia partitions hold well over a hundred million rows, so this
module never materialises a partition as a pandas frame. It pulls the two or
three columns it needs out of Arrow into flat numpy arrays, encodes entity tags
as integer codes, and sorts once. Peak cost is roughly 28 bytes per row
regardless of how wide the original partition is.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pyarrow as pa

from hsf.io.schema import entity_columns


def _permute_all(arrays: dict[str, np.ndarray], order: np.ndarray) -> None:
    """Apply ``order`` to every array in ``arrays``, in place, one at a time.

    Permuting all columns in one expression would hold the old and new copy of
    *every* column simultaneously. Popping each array from the dict first means
    only one column is duplicated at any moment, which on a hundred-million-row
    partition is the difference between running and being OOM-killed on a
    shared machine.
    """
    for name in list(arrays):
        source = arrays.pop(name)  # dict no longer references it
        arrays[name] = source[order]
        del source  # old copy released before the next column is permuted


def _is_non_decreasing(a: np.ndarray) -> bool:
    """Whether ``a`` is already sorted ascending, in one linear pass."""
    return bool(np.all(a[1:] >= a[:-1]))


def _quantisation_step(values: np.ndarray) -> float:
    """Smallest positive gap between distinct observed values.

    Many IPMI sensors report whole degrees, and several Schneider registers are
    fixed-point integers scaled by ten. That resolution places a hard floor on
    achievable forecast error, so it is measured rather than assumed (OI-7).
    Returns NaN when the series has fewer than two distinct values.
    """
    if values.size < 2:
        return float("nan")
    unique = np.unique(values)
    if unique.size < 2:
        return float("nan")
    return float(np.min(np.diff(unique)))


def _sampling_stats(sorted_ts_ns: np.ndarray) -> dict[str, float]:
    """Inter-sample interval statistics, in seconds, from *sorted* timestamps.

    ``dt_cv`` — the coefficient of variation of the interval — is the headline
    number: near zero for a well-behaved 20-second sensor, large for Ganglia,
    whose own documentation warns that its sampling period varies.
    """
    nan = float("nan")
    empty = {
        "dt_median_s": nan,
        "dt_mean_s": nan,
        "dt_cv": nan,
        "dt_p95_s": nan,
        "dt_max_s": nan,
        "duplicate_ts_frac": nan,
    }
    if sorted_ts_ns.size < 3:
        return empty

    dt = np.diff(sorted_ts_ns) / 1e9  # ns -> s
    duplicates = float(np.mean(dt == 0.0))
    positive = dt[dt > 0.0]
    if positive.size == 0:
        return {**empty, "duplicate_ts_frac": duplicates}

    mean = float(positive.mean())
    return {
        "dt_median_s": float(np.median(positive)),
        "dt_mean_s": mean,
        "dt_cv": float(positive.std() / mean) if mean > 0 else nan,
        "dt_p95_s": float(np.percentile(positive, 95)),
        "dt_max_s": float(positive.max()),
        "duplicate_ts_frac": duplicates,
    }


def _coverage(sorted_ts_ns: np.ndarray, dt_median_s: float) -> float:
    """Fraction of expected samples actually present.

    Expected count is the observed span divided by the *median* interval, which
    is robust to the long outage gaps that would otherwise define their own
    apparent cadence.
    """
    if sorted_ts_ns.size < 3 or not np.isfinite(dt_median_s) or dt_median_s <= 0:
        return float("nan")
    span_s = (sorted_ts_ns[-1] - sorted_ts_ns[0]) / 1e9
    expected = span_s / dt_median_s + 1.0
    return float(sorted_ts_ns.size / expected) if expected > 0 else float("nan")


def _entity_codes(table: pa.Table, keys: tuple[str, ...]) -> tuple[np.ndarray, list[str]]:
    """Encode the entity tag columns as a single integer code per row.

    Each key column is dictionary-encoded separately and the codes are combined
    arithmetically, which avoids building a concatenated string key for every
    one of a hundred million rows.
    """
    if not keys:
        return np.zeros(table.num_rows, dtype=np.int64), ["__all__"]

    per_key_codes: list[np.ndarray] = []
    per_key_labels: list[list[str]] = []
    for key in keys:
        encoded = table[key].combine_chunks().dictionary_encode()
        per_key_codes.append(encoded.indices.to_numpy(zero_copy_only=False).astype(np.int64))
        per_key_labels.append([str(v) for v in encoded.dictionary.to_pylist()])

    combined = per_key_codes[0]
    for codes, labels in zip(per_key_codes[1:], per_key_labels[1:], strict=True):
        combined = combined * len(labels) + codes

    # Materialise labels only for the combinations that actually occur.
    present = np.unique(combined)
    remap = np.full(int(present.max()) + 1, -1, dtype=np.int64)
    remap[present] = np.arange(present.size)

    names: list[str] = []
    for raw in present:
        parts: list[str] = []
        remainder = int(raw)
        for labels in reversed(per_key_labels[1:]):
            parts.append(labels[remainder % len(labels)])
            remainder //= len(labels)
        parts.append(per_key_labels[0][remainder])
        names.append("|".join(reversed(parts)))

    return remap[combined], names


def census_for_table(
    table: pa.Table,
    *,
    plugin: str,
    metric: str,
    year_month: str,
) -> pd.DataFrame:
    """Describe every series inside one extracted partition."""
    keys = entity_columns(plugin, table.column_names)

    n_rows = table.num_rows
    ts = (
        table["timestamp"]
        .combine_chunks()
        .cast(pa.timestamp("ns"))
        .to_numpy(zero_copy_only=False)
        .astype("int64", copy=False)
    )

    try:
        # float32 halves the cost and is the storage precision of the source
        # column anyway; per-group statistics are promoted to float64 below.
        values = (
            table["value"].combine_chunks().cast(pa.float32()).to_numpy(zero_copy_only=False)
        )
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError, ValueError):
        # A few Ganglia metrics carry strings (os_name, machine_type, gexec).
        # They are real signals but not numeric ones; record them as such.
        values = np.full(n_rows, np.nan, dtype=np.float32)

    codes, names = _entity_codes(table, keys)
    codes = codes.astype(np.int32, copy=False)
    del table  # release Arrow buffers before allocating the sort permutation

    # Group by entity with a STABLE sort on the integer codes alone.
    #
    # The obvious `np.lexsort((ts, codes))` is a trap at this scale: it sorts on
    # the int64 timestamps as well, and on a 234-million-row Ganglia partition
    # that dominated everything else in the function. Sorting only the int32
    # codes lets numpy use a radix sort, and stability means each entity's rows
    # keep their original relative order — which is already chronological in
    # every ExaData partition observed. Timestamps are therefore re-sorted only
    # within the groups that actually need it, checked in linear time below.
    #
    # Columns are permuted one at a time so only one is ever duplicated.
    order = np.argsort(codes, kind="stable")
    columns = {"ts": ts, "values": values, "codes": codes}
    del ts, values, codes  # only the dict holds them now
    _permute_all(columns, order)
    del order
    ts, values, codes = columns["ts"], columns["values"], columns["codes"]
    columns.clear()

    boundaries = np.flatnonzero(np.diff(codes)) + 1
    starts = np.concatenate(([0], boundaries))
    ends = np.concatenate((boundaries, [codes.size]))

    entity_keys = "|".join(keys) if keys else "__all__"
    rows: list[dict] = []
    for start, end in zip(starts, ends, strict=True):
        group_ts = ts[start:end]
        group_values = values[start:end]

        # Restore chronological order only where the source was not already
        # ordered. The check is O(n); the sort it avoids is O(n log n).
        if group_ts.size > 1 and not _is_non_decreasing(group_ts):
            local = np.argsort(group_ts, kind="stable")
            group_ts = group_ts[local]
            group_values = group_values[local]

        finite = group_values[np.isfinite(group_values)]

        sampling = _sampling_stats(group_ts)
        row: dict[str, object] = {
            "plugin": plugin,
            "metric": metric,
            "year_month": year_month,
            "entity": names[int(codes[start])],
            "entity_keys": entity_keys,
            "n_samples": int(end - start),
            "t_start": pd.Timestamp(int(group_ts[0]), unit="ns", tz="UTC"),
            "t_end": pd.Timestamp(int(group_ts[-1]), unit="ns", tz="UTC"),
            "n_missing": int(group_values.size - finite.size),
            "missing_frac": float(1.0 - finite.size / group_values.size),
            "n_unique": int(np.unique(finite).size) if finite.size else 0,
            "v_min": float(finite.min()) if finite.size else float("nan"),
            "v_max": float(finite.max()) if finite.size else float("nan"),
            "v_mean": float(finite.mean()) if finite.size else float("nan"),
            "v_std": float(finite.std()) if finite.size else float("nan"),
            "quantisation_step": _quantisation_step(finite),
            "is_constant": bool(finite.size > 0 and np.unique(finite).size == 1),
        }
        row.update(sampling)
        row["coverage"] = _coverage(group_ts, sampling["dt_median_s"])
        rows.append(row)

    return pd.DataFrame(rows)
