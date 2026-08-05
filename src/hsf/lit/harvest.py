"""Reproducible literature harvest.

A narrative related-work section cannot be checked: a reader has no way to tell
whether a paper is missing because it does not exist or because nobody looked.
This module turns the search into an artefact — a versioned query set in
``conf/literature_queries.yaml`` produces a screening table that anyone can
re-run and diff.

Sources are OpenAlex (metadata, citation counts, open-access status) and arXiv
(preprints, which HPC systems work often reaches first).

On copyright: only the open-access location that a record itself advertises is
ever downloaded, and PDFs land in gitignored ``private/`` — never in the public
repository. Nothing here attempts to reach a paywalled article by any route.
"""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

OPENALEX = "https://api.openalex.org/works"
ARXIV = "https://export.arxiv.org/api/query"
CROSSREF = "https://api.crossref.org/works"

_USER_AGENT = "hpc-signal-forecastability/0.1 (research; +https://github.com/MSKazemi)"


@dataclass
class Record:
    """One candidate paper."""

    source: str
    external_id: str
    title: str
    year: int | None = None
    authors: str = ""
    venue: str = ""
    doi: str = ""
    cited_by: int | None = None
    relevance: float | None = None
    is_oa: bool = False
    oa_url: str = ""
    abstract: str = ""
    query_id: str = ""
    terms: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        """Deduplication key: DOI when present, else a normalised title."""
        if self.doi:
            return self.doi.lower()
        return re.sub(r"[^a-z0-9]+", "", self.title.lower())[:80]


def _get(url: str, *, timeout: int = 45, retries: int = 3) -> bytes:
    """HTTP GET with polite retries."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - network flakiness is expected
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} attempts: {url}") from last


def _invert_abstract(index: dict | None) -> str:
    """Rebuild an abstract from OpenAlex's inverted index."""
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, spots in index.items():
        positions.extend((spot, word) for spot in spots)
    positions.sort()
    return " ".join(word for _, word in positions)


def search_openalex(term: str, *, mailto: str, per_page: int, from_year: int) -> list[Record]:
    import json

    # `title_and_abstract.search`, NOT the bare `search` parameter.
    #
    # The bare parameter searches full text, which on these queries returned
    # mostly high-citation noise from unrelated fields — deep-learning reviews,
    # heart-rate-variability surveys, a paper on psychedelics — because the query
    # words appear somewhere in their bodies. Restricting the match to title and
    # abstract trades recall for precision, which is the right trade for a
    # screening table a reader is expected to audit.
    filters = [
        f"title_and_abstract.search:{term}",
        f"from_publication_date:{from_year}-01-01",
    ]
    params = {
        "filter": ",".join(filters),
        "per-page": str(min(per_page, 200)),
        "sort": "relevance_score:desc",
        "mailto": mailto,
    }
    payload = json.loads(_get(f"{OPENALEX}?{urllib.parse.urlencode(params)}"))

    out = []
    for work in payload.get("results", []):
        location = work.get("best_oa_location") or {}
        authorships = work.get("authorships", [])
        out.append(
            Record(
                source="openalex",
                external_id=work.get("id", ""),
                title=(work.get("title") or "").strip(),
                year=work.get("publication_year"),
                authors="; ".join(
                    (a.get("author") or {}).get("display_name", "") for a in authorships[:8]
                ),
                venue=((work.get("primary_location") or {}).get("source") or {}).get(
                    "display_name", ""
                )
                or "",
                doi=(work.get("doi") or "").replace("https://doi.org/", ""),
                cited_by=work.get("cited_by_count"),
                is_oa=bool((work.get("open_access") or {}).get("is_oa")),
                oa_url=location.get("pdf_url") or location.get("landing_page_url") or "",
                relevance=work.get("relevance_score"),
                abstract=_invert_abstract(work.get("abstract_inverted_index"))[:1200],
            )
        )
    return out


def search_arxiv(term: str, *, per_page: int) -> list[Record]:
    params = {
        "search_query": f'all:"{term}"',
        "max_results": str(min(per_page, 100)),
        "sortBy": "relevance",
    }
    root = ET.fromstring(_get(f"{ARXIV}?{urllib.parse.urlencode(params)}"))
    ns = {"a": "http://www.w3.org/2005/Atom"}

    out = []
    for entry in root.findall("a:entry", ns):
        arxiv_id = (entry.findtext("a:id", "", ns) or "").rsplit("/", 1)[-1]
        published = entry.findtext("a:published", "", ns) or ""
        pdf = ""
        for link in entry.findall("a:link", ns):
            if link.get("title") == "pdf":
                pdf = link.get("href", "")
        out.append(
            Record(
                source="arxiv",
                external_id=arxiv_id,
                title=" ".join((entry.findtext("a:title", "", ns) or "").split()),
                year=int(published[:4]) if published[:4].isdigit() else None,
                authors="; ".join(
                    a.findtext("a:name", "", ns) or "" for a in entry.findall("a:author", ns)
                ),
                venue="arXiv",
                doi=(entry.findtext("arxiv:doi", "", {"arxiv": "http://arxiv.org/schemas/atom"})
                     or ""),
                is_oa=True,  # arXiv is open access by definition
                oa_url=pdf,
                abstract=" ".join((entry.findtext("a:summary", "", ns) or "").split())[:1200],
            )
        )
    return out


def fetch_doi(doi: str, *, mailto: str) -> Record | None:
    """Fetch one record by DOI from Crossref, for the named classics."""
    import json

    url = f"{CROSSREF}/{urllib.parse.quote(doi)}?mailto={urllib.parse.quote(mailto)}"
    try:
        message = json.loads(_get(url)).get("message", {})
    except Exception:  # noqa: BLE001
        return None

    title = (message.get("title") or [""])[0]
    issued = (message.get("issued") or {}).get("date-parts") or [[None]]
    return Record(
        source="crossref",
        external_id=doi,
        title=title.strip(),
        year=issued[0][0] if issued and issued[0] else None,
        authors="; ".join(
            f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
            for a in (message.get("author") or [])[:8]
        ),
        venue=(message.get("container-title") or [""])[0],
        doi=doi,
        cited_by=message.get("is-referenced-by-count"),
        query_id="classics",
    )


def _merge_provenance(*values: str) -> str:
    """Union of semicolon-separated provenance strings, deduplicated and sorted."""
    parts: set[str] = set()
    for value in values:
        parts.update(p.strip() for p in value.split(";") if p.strip())
    return "; ".join(sorted(parts))


def deduplicate(records: list[Record]) -> list[Record]:
    """Collapse duplicates, preferring the record that carries a DOI.

    The same paper routinely appears as an arXiv preprint and a published
    version; keeping both would inflate every count in the screening table.
    """
    best: dict[str, Record] = {}
    for record in records:
        existing = best.get(record.key)
        if existing is None:
            best[record.key] = record
            continue
        # Merge provenance, then keep whichever has richer metadata.
        #
        # Provenance fields are already semicolon-joined from earlier merges, so
        # they must be split before re-uniquing. Treating them as opaque strings
        # produced entries like "competitions; competitions; competitions" once a
        # work matched several terms.
        merged_terms = _merge_provenance(existing.terms, record.terms)
        merged_queries = _merge_provenance(existing.query_id, record.query_id)
        winner = existing if (existing.doi and not record.doi) else record
        loser = record if winner is existing else existing
        winner.terms = merged_terms
        winner.query_id = merged_queries
        if not winner.abstract:
            winner.abstract = loser.abstract
        if not winner.oa_url:
            winner.oa_url, winner.is_oa = loser.oa_url, loser.is_oa
        best[record.key] = winner
    return list(best.values())
