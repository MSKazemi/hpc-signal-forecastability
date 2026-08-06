# Round 02 — review of `paper/paper.pdf` (12 pp. at review time, 13 after)

**Conflict:** reviewer is the author; all findings tied to recomputations from `results/tables/`.
**Access:** manuscript as extracted text (`pdftoppm` unavailable); figures re-rendered from source.

## Recommendation: Minor revision (up from Major)

Round 01's critical items are resolved. This round found one correctness class — **stale numbers**
— plus two findings the extended analysis produced that the text had not caught.

## Critical

**C3 — Every linking number in the paper was stale.**
*Location:* abstract ¶4, §5.5, Table 2. *Confidence:* High.
The linking analysis was re-run with the extended 21-measure profile after round 01's text was
written. Recomputed against `link_cv.csv`:

| quantity | paper said | actual |
|---|---:|---:|
| mean raw R² | −0.16 | **−0.19** |
| median Spearman | +0.40 | **+0.50** |
| Spearman significant | 10/15 | **9/15** |
| max Spearman | +0.80 | **+0.83** |
| level-corrected, positive | 11/15 | **10/15** |
| worst family (raw) | −1.88 | **−2.39** |

Direction of every conclusion is unchanged; the values were not. Fixed throughout and re-verified
(12/12 exact).

## Major

**M5 — The ablation now contradicts a claim the paper makes.**
The paper stated that dropping the instrument covariates *improves* the model. With the extended
profile it does not: `signal_only` is −0.206 against −0.189 for the full set. The honest reading is
that removing them costs almost nothing, while using them alone destroys the model (−15.0). The
conclusion — that this is not an instrumentation artefact — survives, but via a different argument.
Fixed, and the ablation is now a table (Table 3) rather than a parenthetical.

**M6 — Removing the entropy family *improves* transfer, and the paper does not say so.**
`no_entropy` scores −0.079 against −0.189 for the full profile — the best of the four ablations.
This is a substantive result: the entropy measures are not merely redundant with repetition
fraction (round 01's finding), they are actively harmful to transfer. It also vindicates OI-11's
concern about tie-driven entropy bias more strongly than the correlation evidence did.

**M7 — A gzip compression ratio is the strongest single correlate, ahead of every hand-designed
entropy measure.** r = −0.42 [−0.52, −0.31] over 261 clusters, and top of the permutation-importance
table at 0.202 — more than double the next feature. The paper listed it among the measures without
noting it wins. Added.

## Moderate

- **Mo4** `landscape.pdf` remains generated and unused. **Now resolved as a deliberate exclusion:**
  its claim (entropy ≈ repetition fraction) has been superseded by the stronger ablation evidence
  in M6, so including it would restate a weaker version of a result the paper now makes better.
  Recorded rather than silently dropped.
- **Mo5** The importance table is still prose-only. Deferred: with compression ratio at 0.202 and
  everything else below 0.10, a table of near-zero values would add length without information.

## Reference audit

**New citations added and wired this round**, closing the gap round 01 opened:

| work | for | status |
|---|---|---|
| Richman & Moorman 2000 | sample entropy | definition-only, paywalled, **not read** |
| Dickey & Fuller 1979 | ADF test | definition-only, paywalled, **not read** |
| Kwiatkowski et al. 1992 | KPSS test | definition-only, paywalled, **not read** |
| **Truong et al. 2020** | changepoint detection by binary segmentation | **READ** (arXiv:1801.00718) — title, authors and scope confirmed against the source |

Bandt & Pompe and Peng et al. are now cited at the point of use in §4.4 rather than only in the
"not verified" paragraph, which is where a reader looks for them.

- Bibliography is now 12 entries; 5 read in full, 7 definition-only and paywalled.
- **Unchanged:** three entries cite a version of record while a preprint was read; the AAAI PDF for
  Borghesi et al. 2019 is still unobtainable (OJS 404).
- **No wrong papers, no wrong author names, no unsupported claims** across all 12.
