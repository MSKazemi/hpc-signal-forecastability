#!/usr/bin/env python3
"""Stage 10 — harvest the literature against a versioned query set.

Runs every query in ``conf/literature_queries.yaml`` against OpenAlex and
arXiv, deduplicates, and writes a screening table. The table is committed, so
the related-work section can be audited: a reader can see exactly what was
searched for, what came back, and what was kept.

Open-access PDFs are downloaded only with ``--download``, and only to
gitignored ``private/literature/pdfs/``. Paywalled articles are recorded as
metadata and never fetched.

Outputs:
    literature/screening.csv   (committed) every candidate, with provenance
    literature/queries_run.csv (committed) what was asked and how much came back
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hsf import paths  # noqa: E402
from hsf.lit.harvest import (  # noqa: E402
    Record,
    deduplicate,
    fetch_doi,
    search_arxiv,
    search_openalex,
)

PDF_DIR = paths.PRIVATE / "literature" / "pdfs"


def safe_name(record: Record) -> str:
    stem = record.doi or record.external_id or record.title
    return re.sub(r"[^A-Za-z0-9._-]+", "_", stem)[:120] + ".pdf"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conf", type=Path, default=paths.CONF / "literature_queries.yaml")
    ap.add_argument("--out-dir", type=Path, default=paths.LITERATURE)
    ap.add_argument(
        "--download",
        action="store_true",
        help="fetch open-access PDFs into private/literature/pdfs (never committed)",
    )
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between API calls")
    args = ap.parse_args()

    with open(args.conf) as fh:
        conf = yaml.safe_load(fh)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    mailto = conf["mailto"]
    per_query = conf["per_query"]
    from_year = conf["from_year"]

    records: list[Record] = []
    query_log: list[dict] = []

    for query in conf["queries"]:
        for term in query["terms"]:
            for source, fn in (
                ("openalex", lambda t: search_openalex(
                    t, mailto=mailto, per_page=per_query, from_year=from_year)),
                ("arxiv", lambda t: search_arxiv(t, per_page=per_query)),
            ):
                try:
                    found = fn(term)
                except Exception as exc:  # noqa: BLE001
                    print(f"  !! {source} '{term}': {type(exc).__name__}: {exc}", flush=True)
                    query_log.append(
                        {"query_id": query["id"], "term": term, "source": source,
                         "n_results": 0, "status": f"error: {type(exc).__name__}"}
                    )
                    continue

                for record in found:
                    record.query_id = query["id"]
                    record.terms = term
                records.extend(found)
                query_log.append(
                    {"query_id": query["id"], "term": term, "source": source,
                     "n_results": len(found), "status": "ok"}
                )
                print(f"  {source:9s} {len(found):3d}  {term}", flush=True)
                time.sleep(args.sleep)

    print("\nfetching named classics by DOI")
    for classic in conf.get("classics", []):
        record = fetch_doi(classic["doi"], mailto=mailto)
        if record is None:
            print(f"  !! could not fetch {classic['doi']}")
            continue
        record.notes.append(classic["why"])
        records.append(record)
        print(f"  {record.year}  {record.title[:70]}")
        time.sleep(args.sleep)

    unique = deduplicate(records)
    print(f"\n{len(records):,} raw hits -> {len(unique):,} unique works")

    table = pd.DataFrame(
        [
            {
                "key": r.key,
                "title": r.title,
                "year": r.year,
                "authors": r.authors,
                "venue": r.venue,
                "doi": r.doi,
                "cited_by": r.cited_by,
                "relevance": r.relevance,
                "is_oa": r.is_oa,
                "oa_url": r.oa_url,
                "source": r.source,
                "query_id": r.query_id,
                "terms": r.terms,
                "why_classic": "; ".join(r.notes),
                # Filled in by reading, not by the script. Screening is a human
                # judgement and the column is left honest until it is made.
                "decision": "",
                "decision_reason": "",
                "abstract": r.abstract,
            }
            for r in unique
        ]
    ).sort_values(["query_id", "relevance"], ascending=[True, False])

    screening = args.out_dir / "screening.csv"
    table.to_csv(screening, index=False)
    pd.DataFrame(query_log).to_csv(args.out_dir / "queries_run.csv", index=False)

    print(f"\nWrote {screening} ({len(table):,} rows)")
    print(f"open access: {int(table.is_oa.sum()):,} / {len(table):,}")
    print("\n=== hits per query ===")
    print(table.query_id.value_counts().head(10).to_string())
    print("\n=== most relevant hit per query ===")
    top = table.sort_values("relevance", ascending=False).groupby("query_id").head(1)
    for row in top.itertuples():
        print(f"  {str(row.query_id)[:34]:34s} {row.year}  {str(row.title)[:64]}")

    if not args.download:
        print("\n(--download not set; no PDFs fetched)")
        return

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    downloadable = table[table.is_oa & table.oa_url.astype(bool)]
    print(f"\ndownloading {len(downloadable):,} open-access PDFs into {PDF_DIR}")
    ok = failed = 0
    for row in downloadable.itertuples():
        target = PDF_DIR / re.sub(r"[^A-Za-z0-9._-]+", "_", str(row.key))[:120]
        target = target.with_suffix(".pdf")
        if target.exists():
            continue
        try:
            request = urllib.request.Request(
                row.oa_url, headers={"User-Agent": "hpc-signal-forecastability/0.1 (research)"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
            if body[:4] != b"%PDF":
                failed += 1
                continue
            target.write_bytes(body)
            ok += 1
        except Exception:  # noqa: BLE001 - a missing PDF is not a failure of the study
            failed += 1
        time.sleep(args.sleep)
    print(f"downloaded {ok}, unavailable {failed}")


if __name__ == "__main__":
    main()
