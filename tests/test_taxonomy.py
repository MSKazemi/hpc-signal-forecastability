"""Tests for the a-priori signal taxonomy.

The taxonomy defines the strata the whole study is organised around, so a
mislabelled family would propagate into every result. These tests pin the
classifications that carry the argument, and in particular the panel-prefix
normalisation, whose absence silently misfiled an entire plugin.
"""

from __future__ import annotations

import pytest

from hsf.taxonomy import classify, normalise_metric, scope_for


@pytest.mark.parametrize(
    ("plugin", "metric", "origin"),
    [
        # IPMI: the sensors the study's thermal claims rest on.
        ("ipmi", "p0_core3_temp", "thermal"),
        ("ipmi", "ambient", "thermal"),
        ("ipmi", "pcie", "thermal"),
        ("ipmi", "total_power", "power"),
        ("ipmi", "fan1_0", "fan_flow"),
        ("ipmi", "ps0_input_voltag", "electrical"),
        # Ganglia: counters must not be read as ordinary continuous signals.
        ("ganglia", "Gpu0_gpu_temp", "thermal"),
        ("ganglia", "Gpu0_ecc_sbe_aggregate_total", "error_counter"),
        ("ganglia", "Gpu1_total_energy_consumption", "error_counter"),
        ("ganglia", "cpu_user", "cpu_utilisation"),
        ("ganglia", "mem_free", "memory"),
        ("ganglia", "bytes_in", "network"),
        ("ganglia", "disk_free", "storage"),
        ("ganglia", "boottime", "system_meta"),
        # Scheduler and alarms.
        ("slurm", "s21.jobs.tot_jobs", "scheduler"),
        ("nagios", "state", "alarm_state"),
        # Facility.
        ("logics", "Pue", "facility_power"),
        ("logics", "Corrente_L1", "electrical"),
        ("vertiv", "Return_Air_Temperature", "thermal"),
        ("vertiv", "Return_Humidity", "humidity"),
        ("vertiv", "Fan_Speed", "fan_flow"),
        # Weather's bare `humidity` is the OUTDOOR reading and must stay
        # exogenous rather than being captured by the room-humidity rule.
        ("weather", "humidity", "weather"),
        ("weather", "temp", "thermal"),
    ],
)
def test_known_metrics_get_the_right_origin(plugin, metric, origin):
    assert classify(plugin, metric).origin == origin


# --- the panel-prefix bug --------------------------------------------------
#
# Schneider exposes every register as "PLC_PLC_Q101.<name>". With the prefix
# left in place, every rule anchored with ^ failed against it and a whole
# family fell through to the plugin default.


def test_panel_prefix_is_stripped():
    assert normalise_metric("PLC_PLC_Q101.Rif_auto_ty141") == "Rif_auto_ty141"
    assert normalise_metric("PLC_PLC_Q102.Alm_w1") == "Alm_w1"
    assert normalise_metric("ambient") == "ambient"


@pytest.mark.parametrize(
    ("metric", "origin"),
    [
        ("PLC_PLC_Q101.Alm_w1", "alarm_state"),
        ("PLC_PLC_Q101.P101_fault", "alarm_state"),
        ("PLC_PLC_Q101.Rif_auto_ty141", "setpoint_config"),
        ("PLC_PLC_Q101.Max_portata", "setpoint_config"),
        ("PLC_PLC_Q101.Min_ana_out_ty141", "setpoint_config"),
        ("PLC_PLC_Q101.T_mandata_hmi", "thermal"),
        ("PLC_PLC_Q101.T_ritorno_hmi", "thermal"),
        ("PLC_PLC_Q101.In_marcia_p101", "alarm_state"),
    ],
)
def test_prefixed_schneider_metrics_are_classified(metric, origin):
    assert classify("schneider", metric).origin == origin


def test_prefixed_and_bare_names_agree():
    """The prefix must change nothing but the string."""
    for name in ["Alm_w1", "Max_portata", "T_mandata_hmi", "Cmd_valvola_1"]:
        assert (
            classify("schneider", name).origin
            == classify("schneider", f"PLC_PLC_Q101.{name}").origin
        )


# --- other axes ------------------------------------------------------------


def test_control_loops_are_flagged():
    """Vertiv and Schneider actively drive their quantities toward a target."""
    assert classify("vertiv", "Supply_Air_Temperature").controlled
    assert classify("schneider", "PLC_PLC_Q101.Cmd_valvola_1").controlled
    # An IPMI sensor merely observes.
    assert not classify("ipmi", "p0_core3_temp").controlled


def test_counters_are_marked_monotone():
    assert classify("ganglia", "Gpu0_ecc_dbe_aggregate_total").value_kind == "monotone_counter"


def test_scope_follows_the_plugin():
    assert scope_for("ipmi") == "node"
    assert scope_for("vertiv") == "device"
    assert scope_for("schneider") == "panel"
    assert scope_for("slurm") == "partition"
    assert scope_for("weather") == "facility"


def test_every_label_records_the_rule_that_produced_it():
    """Auditability: no label may appear without a traceable reason."""
    for plugin, metric in [("ipmi", "ambient"), ("schneider", "PLC_PLC_Q101.Td_pid_valvole")]:
        assert classify(plugin, metric).rule
