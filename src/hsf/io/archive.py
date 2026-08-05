"""Reading the M100 ExaData monthly archives.

Each monthly archive is a tar laid out as a Hive-partitioned parquet tree::

    year_month=YY-MM/plugin=<plugin>_pub/metric=<metric>/a_0.parquet

Two operations are supported, and both are cheap because a tar stored in a
regular file is seekable: listing walks headers only, and extraction seeks
directly to the members it wants. Neither reads the bulk of a 30 GB archive.

This matters — the full release is roughly 420 GB against far less free space,
so nothing here ever extracts a whole archive.
"""

from __future__ import annotations

import re
import tarfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from hsf.io.disk import require_free_gb

# year_month=21-08/plugin=ipmi_pub/metric=ambient/a_0.parquet
_MEMBER_RE = re.compile(
    r"^year_month=(?P<year_month>[^/]+)/"
    r"plugin=(?P<plugin>[^/]+)/"
    r"metric=(?P<metric>[^/]+)/"
    r"(?P<filename>[^/]+)$"
)


@dataclass(frozen=True)
class Partition:
    """One ``metric=`` partition file inside a monthly archive."""

    year_month: str
    plugin: str
    metric: str
    member: str
    size_bytes: int

    @property
    def plugin_family(self) -> str:
        """Plugin name with the ExaMon ``_pub`` suffix removed."""
        return self.plugin[:-4] if self.plugin.endswith("_pub") else self.plugin


def iter_partitions(tar_path: Path) -> Iterator[Partition]:
    """Yield every parquet partition in ``tar_path``.

    Headers only — the archive's data blocks are seeked over, so this costs
    milliseconds even for a 30 GB archive.
    """
    with tarfile.open(tar_path, "r:") as tf:
        for member in tf:
            if not member.isfile():
                continue
            match = _MEMBER_RE.match(member.name)
            if match is None:
                continue
            yield Partition(
                year_month=match["year_month"],
                plugin=match["plugin"],
                metric=match["metric"],
                member=member.name,
                size_bytes=member.size,
            )


def extract_partitions(
    tar_path: Path,
    dest: Path,
    *,
    predicate=None,
    min_free_gb: float = 30.0,
    check_every: int = 5,
) -> list[Path]:
    """Extract the partitions of ``tar_path`` accepted by ``predicate``.

    ``predicate`` takes a :class:`Partition` and returns whether to extract it;
    ``None`` means extract everything, which is almost never what you want.

    Free space is re-checked every ``check_every`` members so that a large
    selection aborts partway rather than filling the filesystem.
    """
    dest.mkdir(parents=True, exist_ok=True)
    require_free_gb(dest, min_free_gb, context=f"extracting from {tar_path.name}")

    written: list[Path] = []
    with tarfile.open(tar_path, "r:") as tf:
        for member in tf:
            if not member.isfile():
                continue
            match = _MEMBER_RE.match(member.name)
            if match is None:
                continue
            partition = Partition(
                year_month=match["year_month"],
                plugin=match["plugin"],
                metric=match["metric"],
                member=member.name,
                size_bytes=member.size,
            )
            if predicate is not None and not predicate(partition):
                continue

            if len(written) % check_every == 0:
                require_free_gb(dest, min_free_gb, context=f"extracting {member.name}")

            target = dest / member.name
            if target.exists() and target.stat().st_size == member.size:
                written.append(target)  # already extracted; idempotent re-runs
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            source = tf.extractfile(member)
            if source is None:  # pragma: no cover - defensive
                continue
            with source, open(target, "wb") as out:
                while chunk := source.read(1 << 20):
                    out.write(chunk)
            written.append(target)

    return written


def month_from_archive_name(tar_path: Path) -> str:
    """``/path/to/21-08.tar`` -> ``21-08``."""
    return tar_path.stem


def find_archives(raw_dir: Path, months: Iterable[str] | None = None) -> list[Path]:
    """Monthly archives in ``raw_dir``, optionally restricted to ``months``."""
    archives = sorted(raw_dir.glob("*.tar"))
    if months is None:
        return archives
    wanted = set(months)
    return [p for p in archives if month_from_archive_name(p) in wanted]
