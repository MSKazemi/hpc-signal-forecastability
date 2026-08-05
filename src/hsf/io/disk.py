"""Disk-space guards.

The M100 ExaData archives total roughly 420 GB and the working machine has far
less free space than that, so extraction must be selective and must fail loudly
rather than filling the filesystem. Every routine that writes bulk data to
``data/interim`` calls :func:`require_free_gb` first and again between units of
work.
"""

from __future__ import annotations

import shutil
from pathlib import Path


class InsufficientDiskSpace(RuntimeError):
    """Raised when a bulk write would take free space below the safety margin."""


def free_gb(path: Path) -> float:
    """Free space in gibibytes on the filesystem containing ``path``.

    The nearest existing ancestor is used, so the check works for a directory
    that has not been created yet.
    """
    probe = path
    while not probe.exists():
        parent = probe.parent
        if parent == probe:  # reached the filesystem root
            break
        probe = parent
    return shutil.disk_usage(probe).free / (1024**3)


def require_free_gb(path: Path, minimum_gb: float, *, context: str = "") -> float:
    """Assert that at least ``minimum_gb`` GiB are free, else raise.

    Returns the measured free space so callers can log it.
    """
    available = free_gb(path)
    if available < minimum_gb:
        where = f" before {context}" if context else ""
        raise InsufficientDiskSpace(
            f"Only {available:.1f} GiB free on the filesystem holding {path}{where}; "
            f"the configured safety margin is {minimum_gb:.1f} GiB. "
            f"Free space or lower --min-free-gb deliberately, but note that filling "
            f"this filesystem will affect the whole machine."
        )
    return available


def dir_size_gb(path: Path) -> float:
    """Total size of ``path`` in gibibytes, following no symlinks."""
    if not path.exists():
        return 0.0
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
    return total / (1024**3)
