"""A-priori signal taxonomy.

Every series is labelled along four axes *before* any predictability is
measured. The labels come from the plugin and the metric name only — never
from the data — so the later finding "predictability differs by signal class"
cannot be a relabelling of the result it is meant to explain.

Each rule records the pattern that fired, so every label in
``data/derived/taxonomy.csv`` is auditable back to a line in this file.

The four axes
-------------
``origin``
    What physical or logical process produces the signal. This is the axis the
    study's hypothesis is about: thermal diffusion, a control loop, a user
    submitting jobs, and the weather should not be equally predictable.
``value_kind``
    How the value is encoded. A monotone counter, a binary alarm, and a
    continuous float have different achievable error by construction.
``scope``
    What the measurement is attached to — one node, one cooling device, one
    scheduler partition, or the whole facility. Aggregation averages noise
    away, so scope is a confound that must be carried, not ignored.
``controlled``
    Whether a controller is actively driving the quantity. A setpoint held by a
    PID loop is predictable for reasons that have nothing to do with the
    physics of the underlying plant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Axis vocabularies
# ---------------------------------------------------------------------------

ORIGINS = (
    "thermal",           # temperatures of silicon, air, or fluid
    "power",             # electrical power and energy of IT equipment
    "electrical",        # voltage, current, frequency, power factor
    "cpu_utilisation",   # processor occupancy
    "gpu_utilisation",   # accelerator occupancy
    "memory",            # memory and swap occupancy
    "storage",           # disk capacity and I/O
    "network",           # interconnect and Ethernet traffic
    "error_counter",     # ECC, CRC, retirement, XID — monotone fault counts
    "fan_flow",          # fans, pumps, valves, flow rate
    "scheduler",         # queue depth, allocation, waiting time
    "alarm_state",       # discrete health or alarm indicators
    "setpoint_config",   # controller setpoints, limits, gains, configuration
    "facility_power",    # room-level power, PUE, chillers, CRACs
    "weather",           # exogenous outdoor conditions
    "system_meta",       # boottime, os_name, cpu_num — descriptive constants
    "other",
)

VALUE_KINDS = ("continuous", "quantised", "monotone_counter", "binary", "categorical")

SCOPES = ("node", "device", "panel", "partition", "facility")


@dataclass(frozen=True)
class Label:
    origin: str
    value_kind: str
    controlled: bool
    rule: str


# ---------------------------------------------------------------------------
# Metric-name rules, evaluated in order; the first match wins.
#
# Patterns are matched case-insensitively against the metric name. Ordering
# matters: "gpu_temp" must reach the thermal rule before the generic gpu rule,
# and "power_management_limit" must be read as configuration, not power.
# ---------------------------------------------------------------------------

_RULES: list[tuple[str, str, str, bool]] = [
    # (regex, origin, value_kind, controlled)

    # --- configuration, limits, and controller gains --------------------------
    (r"set_?point|_limit$|limit_violation|^kp_|kp_pid|max_ana|manuale_|abilita_|"
     r"power_management_limit|app_clock|_config$|_str$|show_flags|profile",
     "setpoint_config", "quantised", True),

    # --- monotone fault and traffic counters ---------------------------------
    (r"ecc_|retired_pages|xid_errors|crc_error|recovery_error|replay_error|"
     r"_violation$|violation_",
     "error_counter", "monotone_counter", False),
    (r"total_energy_consumption|^energia$|^mwh$|^mvarh$|_total$",
     "error_counter", "monotone_counter", False),

    # --- thermal --------------------------------------------------------------
    (r"temp|temperature|dew_point|feels_like|_t_mandata|_t_ritorno|delta_temp",
     "thermal", "quantised", False),

    # --- fans, pumps, valves, flow -------------------------------------------
    (r"^fan|fan_|valvola|valve|portata|pompe|_p10[1-4]|compressor|"
     r"humidifier|dehumidifier|reheat|pressure_drop|static_pressure",
     "fan_flow", "continuous", True),

    # --- electrical -----------------------------------------------------------
    (r"volt|tensione|corrente|^amps?$|frequenza|fattore_di_potenza|^mvar$|"
     r"output_curre|input_voltag",
     "electrical", "continuous", False),

    # --- facility power and efficiency ---------------------------------------
    (r"^pue$|^dcie$|^tot(_|$)|^pit$|^pt$|chiller|cdz|qpompe|servizi|^mw$",
     "facility_power", "continuous", False),

    # --- IT power -------------------------------------------------------------
    (r"power|potenza|watt", "power", "continuous", False),

    # --- accelerator ----------------------------------------------------------
    (r"^gpu\d|^gv100|gpu_util|mem_copy_util|nvlink|_pstate$|sm_clock|memory_clock|fb_",
     "gpu_utilisation", "quantised", False),

    # --- processor ------------------------------------------------------------
    (r"^cpu_|^load_|proc_run|proc_total|cluster_cpu", "cpu_utilisation", "continuous", False),

    # --- memory ---------------------------------------------------------------
    (r"^mem_|^swap_|memory_util|memory_alloc|memory_idle|memory_down|memory_eligible",
     "memory", "continuous", False),

    # --- storage --------------------------------------------------------------
    (r"^disk_|part_max_used", "storage", "continuous", False),

    # --- network --------------------------------------------------------------
    (r"^bytes_|^pkts_", "network", "continuous", False),

    # --- scheduler ------------------------------------------------------------
    (r"jobs\.|nodes_|cpus_|gpus_|total_nodes|num_nodes|job_id|waiting_hour|"
     r"tot_node_hour|eligible|alloc|idle|mixed",
     "scheduler", "quantised", False),

    # --- discrete health ------------------------------------------------------
    (r"^state$|allarme|^alm_|status|stato|comlost|bad_values|in_marcia",
     "alarm_state", "categorical", False),

    # --- weather --------------------------------------------------------------
    (r"^clouds$|^humidity$|^pressure$|^uvi$|^visibility$|^wind_", "weather", "continuous", False),

    # --- descriptive ----------------------------------------------------------
    (r"boottime|machine_type|os_name|os_release|gexec|cpu_num|cpu_speed|"
     r"^prototype$|^gateway$|^address$|deviceid|id_modbus",
     "system_meta", "categorical", False),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), o, v, c) for p, o, v, c in _RULES]

# Plugin-level defaults, used when no metric rule fires.
_PLUGIN_DEFAULT: dict[str, tuple[str, str, bool]] = {
    "weather": ("weather", "continuous", False),
    "nagios": ("alarm_state", "categorical", False),
    "slurm": ("scheduler", "quantised", False),
    "schneider": ("setpoint_config", "quantised", True),
    "logics": ("facility_power", "continuous", False),
    "vertiv": ("fan_flow", "continuous", True),
    "ipmi": ("other", "quantised", False),
    "ganglia": ("other", "continuous", False),
}

# Which plugins run their quantity under closed-loop control. A Vertiv air
# handler and the Schneider PLC actively drive their measurements toward a
# target; an IPMI thermal sensor merely observes.
_CONTROLLED_PLUGINS = frozenset({"vertiv", "schneider"})

_SCOPE_BY_PLUGIN: dict[str, str] = {
    "ipmi": "node",
    "ganglia": "node",
    "nagios": "node",
    "slurm": "partition",
    "vertiv": "device",
    "logics": "device",
    "schneider": "panel",
    "weather": "facility",
}


def classify(plugin: str, metric: str) -> Label:
    """Label one (plugin, metric) pair. Metric rules take precedence."""
    for pattern, origin, value_kind, controlled in _COMPILED:
        if pattern.search(metric):
            return Label(
                origin=origin,
                value_kind=value_kind,
                controlled=controlled or plugin in _CONTROLLED_PLUGINS,
                rule=f"metric:{pattern.pattern[:40]}",
            )

    origin, value_kind, controlled = _PLUGIN_DEFAULT.get(plugin, ("other", "continuous", False))
    return Label(
        origin=origin,
        value_kind=value_kind,
        controlled=controlled or plugin in _CONTROLLED_PLUGINS,
        rule=f"plugin-default:{plugin}",
    )


def scope_for(plugin: str) -> str:
    return _SCOPE_BY_PLUGIN.get(plugin, "facility")
