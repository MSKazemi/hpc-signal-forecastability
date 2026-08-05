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
    "humidity",          # room humidity, a control-loop output
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
    # Schneider exposes matching Max_* and Min_* limit registers; both are
    # configuration, so the pattern covers each rather than only the maxima.
    (r"set_?point|_limit$|limit_violation|^kp_|kp_pid|^max_|^min_|out_pid|"
     r"manuale_|abilita_|diff_minuti|^rif_|^sel_|^start_|^set_|"
     r"power_management_limit|app_clock|_config$|_str$|show_flags|profile",
     "setpoint_config", "quantised", True),

    # --- monotone fault and traffic counters ---------------------------------
    (r"ecc_|retired_pages|xid_errors|crc_error|recovery_error|replay_error|"
     r"_violation$|violation_",
     "error_counter", "monotone_counter", False),
    (r"total_energy_consumption|^energia$|^mwh$|^mvarh$|_total$",
     "error_counter", "monotone_counter", False),

    # --- humidity -------------------------------------------------------------
    # Kept apart from thermal: room humidity is actively driven by the
    # humidifier/dehumidifier stage of a CRAC unit, so it is a control-loop
    # output whose predictability has a different source from a temperature.
    # Matches Return_Humidity, Ext_Air_Sensor_A_Humidity, Adjusted_Humidity —
    # but deliberately NOT the bare `humidity` metric, which is Weather's
    # outdoor reading and belongs to the exogenous family further down.
    (r"_humidity|humidity_|^adjusted_humidity$", "humidity", "continuous", False),

    # --- thermal --------------------------------------------------------------
    # `ambient` is the node inlet temperature and `pcie` the PCIe slot
    # temperature; both are documented in degrees Celsius.
    # Schneider names its process temperatures T_mandata (supply), T_ritorno
    # (return) and T_scambio (heat exchange), in Italian and abbreviated.
    (r"temp|temperature|dew_point|feels_like|delta_temp|"
     r"^t_mandata|^t_ritorno|^t_scambio|^ambient$|^pcie$",
     "thermal", "quantised", False),

    # --- discrete health and status ------------------------------------------
    # Deliberately ahead of the mechanism rules below. A signal that reports
    # *whether* something is running is a discrete state, whatever equipment it
    # belongs to: In_marcia_p101 is pump 101's on/off status, not a flow
    # measurement, and its predictability comes from switching behaviour rather
    # than from fluid dynamics.
    (r"^state$|allarme|^alm_|_fault$|status|stato|comlost|bad_values|in_marcia",
     "alarm_state", "categorical", False),

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
    (r"^mem_|^swap_|memory_util|mem_util|memory_alloc|memory_idle|memory_down|memory_eligible",
     "memory", "continuous", False),

    # --- storage --------------------------------------------------------------
    (r"^disk_|part_max_used", "storage", "continuous", False),

    # --- network --------------------------------------------------------------
    (r"^bytes_|^pkts_", "network", "continuous", False),

    # --- scheduler ------------------------------------------------------------
    (r"jobs\.|nodes_|cpus_|gpus_|total_nodes|num_nodes|job_id|waiting_hour|"
     r"tot_node_hour|eligible|alloc|idle|mixed",
     "scheduler", "quantised", False),

    # --- actuator position and controller references --------------------------
    # Posizione_ty14x is the measured valve position and Rif_* the reference the
    # controller is driving toward: both are the actuated side of the cooling
    # control loop rather than a sensed physical quantity.
    (r"posizione_|^rif_|_inverter$", "fan_flow", "continuous", True),

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


# Schneider exposes every register as "PLC_PLC_Q101.<name>". Left in place, the
# prefix defeats every rule anchored with ^ — Rif_auto_ty141 never matched ^rif_
# — which silently pushed a whole family to the plugin default. The prefix is
# stripped before matching so anchors mean what they appear to mean.
_PANEL_PREFIX = re.compile(r"^PLC_PLC_Q\d+\.", re.IGNORECASE)


def normalise_metric(metric: str) -> str:
    """Metric name with any PLC panel prefix removed."""
    return _PANEL_PREFIX.sub("", metric)


def classify(plugin: str, metric: str) -> Label:
    """Label one (plugin, metric) pair. Metric rules take precedence."""
    name = normalise_metric(metric)
    for pattern, origin, value_kind, controlled in _COMPILED:
        if pattern.search(name):
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
