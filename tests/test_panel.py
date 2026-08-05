"""Tests for the fixed entity panel.

The panel is a sampling decision that every later result inherits, so its two
load-bearing properties are pinned here: it must be identical on every run and
in every worker process, and it must be identical across metrics and months so
that cross-metric comparisons are made on the same physical machines.
"""

from __future__ import annotations

from hsf.io.panel import select_panel

NODES = [str(i) for i in range(980)]


def test_panel_is_capped():
    assert len(select_panel(NODES, 96, seed=1)) == 96


def test_small_populations_are_taken_whole():
    """Vertiv has 25 devices, Schneider 2 panels, Weather 1 series."""
    devices = [f"cdz{i}" for i in range(25)]
    assert select_panel(devices, 96, seed=1) == set(devices)


def test_panel_is_deterministic_across_calls():
    assert select_panel(NODES, 96, seed=1) == select_panel(NODES, 96, seed=1)


def test_panel_is_independent_of_input_order():
    """File and row order must never influence membership."""
    forward = select_panel(NODES, 96, seed=1)
    backward = select_panel(list(reversed(NODES)), 96, seed=1)
    assert forward == backward


def test_panel_is_stable_when_other_entities_come_and_go():
    """The key property for cross-metric comparison.

    Coverage varies by metric and month — some metrics report on fewer nodes.
    A node that is present must land in the panel regardless of which OTHER
    nodes happen to be present, otherwise each metric would get a different
    slice of the machine and between-metric differences would be confounded.
    """
    full = select_panel(NODES, 96, seed=1)
    # A metric that only reported on the first 500 nodes.
    partial_input = NODES[:500]
    partial = select_panel(partial_input, 96, seed=1)

    expected = {n for n in full if n in set(partial_input)}
    # Every node chosen from the full population is still chosen here, provided
    # it exists in the reduced population.
    assert expected <= partial


def test_different_seeds_give_different_panels():
    assert select_panel(NODES, 96, seed=1) != select_panel(NODES, 96, seed=2)


def test_panel_survives_a_process_boundary():
    """blake2b, not Python's randomised hash().

    Workers are separate processes. Python's built-in hash() is salted per
    process, so using it would silently give each worker a different panel.
    """
    import subprocess
    import sys

    code = (
        "import sys; sys.path.insert(0, 'src');"
        "from hsf.io.panel import select_panel;"
        "print(sorted(select_panel([str(i) for i in range(980)], 8, seed=1)))"
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        ).stdout.strip()
        for _ in range(2)
    }
    assert len(runs) == 1
    assert runs.pop() == str(sorted(select_panel(NODES, 8, seed=1)))
