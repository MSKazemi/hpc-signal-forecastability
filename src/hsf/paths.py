"""Canonical paths for the project.

Every script resolves paths through this module so that a clone with a different
checkout location, or a run with data mounted elsewhere, needs no code edits.

Environment overrides:
    HSF_ROOT      repository root (default: inferred from this file's location)
    HSF_RAW_DIR   directory holding the M100 ExaData monthly ``*.tar`` archives
    HSF_AGG_DIR   directory holding the pre-aggregated per-node parquet files
"""

from __future__ import annotations

import os
from pathlib import Path

# src/hsf/paths.py -> src/hsf -> src -> repo root
ROOT = Path(os.environ.get("HSF_ROOT", Path(__file__).resolve().parents[2]))

# --- committed outputs -----------------------------------------------------
DERIVED = ROOT / "data" / "derived"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"
PAPER = ROOT / "paper"
LITERATURE = ROOT / "literature"
CONF = ROOT / "conf"

# --- gitignored working space ----------------------------------------------
INTERIM = ROOT / "data" / "interim"
PRIVATE = ROOT / "private"

# --- external, read-only source data ---------------------------------------
# Never written to. The ExaData tree is treated as immutable input.
RAW_DIR = Path(os.environ.get("HSF_RAW_DIR", Path.home() / "exadata" / "raw"))
AGG_DIR = Path(os.environ.get("HSF_AGG_DIR", Path.home() / "exadata" / "time_aggregated"))

# --- named artefacts -------------------------------------------------------
MANIFEST = DERIVED / "manifest.parquet"
TAXONOMY = DERIVED / "taxonomy.csv"
FEATURES = DERIVED / "features.parquet"
SKILL = DERIVED / "skill.parquet"


def ensure_output_dirs() -> None:
    """Create the writable output directories if they do not exist."""
    for d in (DERIVED, TABLES, FIGURES, INTERIM):
        d.mkdir(parents=True, exist_ok=True)
