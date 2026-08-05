"""The disk guard is the only thing standing between a 420 GB dataset and a full
filesystem, so it gets tested first."""

from __future__ import annotations

import pytest

from hsf.io import InsufficientDiskSpace, free_gb, require_free_gb


def test_free_gb_reports_a_positive_number(tmp_path):
    assert free_gb(tmp_path) > 0


def test_free_gb_works_for_a_path_that_does_not_exist_yet(tmp_path):
    """Callers check space before creating the output directory."""
    missing = tmp_path / "not" / "created" / "yet"
    assert free_gb(missing) > 0


def test_require_free_gb_passes_when_space_is_available(tmp_path):
    assert require_free_gb(tmp_path, 0.0) > 0


def test_require_free_gb_raises_when_margin_is_not_met(tmp_path):
    with pytest.raises(InsufficientDiskSpace) as excinfo:
        require_free_gb(tmp_path, 10**9, context="extracting 21-08")
    message = str(excinfo.value)
    assert "extracting 21-08" in message
    assert "safety margin" in message
