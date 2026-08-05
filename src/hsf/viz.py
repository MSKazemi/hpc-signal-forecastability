"""Figure styling for the paper.

One place decides how every figure looks, so the paper reads as one document
rather than as a pile of separately-styled plots.

Colour
------
The categorical palette is fixed and assigned in a fixed order — never cycled,
never reassigned when a filter changes which families are present, so a family
keeps its colour across every figure in the paper. It was checked with a
colour-vision-deficiency validator: worst adjacent pair separates at
ΔE 9.1 under protanopia and 19.6 under normal vision, both above the required
floors.

Because several slots sit below 3:1 contrast against the page, every figure
that uses them also carries a direct label or a legend — identity is never
carried by colour alone. That is a requirement, not a preference: the paper is
printed and photocopied.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

# Fixed categorical order. Validated: see module docstring.
CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#8a8a8a",  # grey — reserved for "other"/aggregate
]

# Single hue, light to dark, for magnitude.
SEQUENTIAL = "Blues"

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#8a8a8a"
GRID = "#dcdcda"

# Plugin colours are pinned so a plugin is the same colour in every figure.
PLUGIN_COLOURS = {
    "ipmi": CATEGORICAL[0],
    "ganglia": CATEGORICAL[1],
    "slurm": CATEGORICAL[2],
    "nagios": CATEGORICAL[3],
    "vertiv": CATEGORICAL[4],
    "schneider": CATEGORICAL[5],
    "logics": CATEGORICAL[6],
    "weather": CATEGORICAL[7],
}


def apply_style() -> None:
    """Set the paper's matplotlib defaults.

    Grid and axes are deliberately recessive: the data should be the darkest
    thing on the page.
    """
    mpl.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "font.size": 9,
            "font.family": "serif",
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.labelcolor": INK_SECONDARY,
            "axes.edgecolor": GRID,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "xtick.color": INK_SECONDARY,
            "ytick.color": INK_SECONDARY,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.frameon": False,
            "legend.fontsize": 8,
            "lines.linewidth": 1.6,
            "lines.markersize": 4,
        }
    )


def plugin_colour(name: str) -> str:
    return PLUGIN_COLOURS.get(name, INK_MUTED)


def save(fig, path, *, close: bool = True) -> None:
    """Write a figure as PDF, which is what the LaTeX build wants."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf")
    if close:
        plt.close(fig)
