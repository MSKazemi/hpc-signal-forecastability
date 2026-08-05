"""Per-plugin schema knowledge.

Every ExaMon parquet partition carries ``timestamp`` and ``value``, plus a
plugin-specific set of tag columns identifying *which* entity the measurement
belongs to. A series is one (metric, entity) pair, so knowing the entity
columns is what turns a partition into a set of time series.

Column sets below were confirmed by reading the actual partitions, not only the
dataset documentation; the two disagree in places (Nagios carries more tags
than its metric table implies).
"""

from __future__ import annotations

# Tag columns that identify an entity, per plugin family.
ENTITY_COLUMNS: dict[str, tuple[str, ...]] = {
    "ipmi": ("node",),
    "ganglia": ("node",),
    # Nagios keys a series by node *and* by which check is being reported.
    "nagios": ("node", "description"),
    # SLURM time series are aggregates per partition/QoS, not per node.
    "slurm": ("partition", "qos"),
    "vertiv": ("device",),
    "logics": ("panel", "device"),
    "schneider": ("panel",),
    # Weather is a single facility-wide series: no entity dimension at all.
    "weather": (),
}

# Additional tag columns that exist but do not identify a distinct series;
# they are metadata about the reading.
CONTEXT_COLUMNS: dict[str, tuple[str, ...]] = {
    "nagios": ("host_group", "nagiosdrained", "state_type"),
    "slurm": ("user_id", "job_state"),
}

# Plugins that do not produce time series at all.
#
# ``job_table`` is a wide table of per-job submission records — one row per job,
# no ``value`` column. It enters this study only as an exogenous covariate
# (see OI-8), never as a signal to be forecast.
NON_TIMESERIES_PLUGINS: frozenset[str] = frozenset({"job_table"})


def entity_columns(plugin_family: str, available: list[str] | None = None) -> tuple[str, ...]:
    """Entity columns for ``plugin_family``, intersected with what is present.

    ``available`` guards against schema drift across the campaign: SLURM, for
    instance, does not carry ``qos`` in every month. Columns that are declared
    but absent are silently dropped rather than raising, because a missing tag
    means a coarser entity, not a broken file.
    """
    declared = ENTITY_COLUMNS.get(plugin_family, ())
    if available is None:
        return declared
    present = set(available)
    return tuple(c for c in declared if c in present)


def is_timeseries_plugin(plugin_family: str) -> bool:
    return plugin_family not in NON_TIMESERIES_PLUGINS
