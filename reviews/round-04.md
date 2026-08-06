# Round 04 — review of `paper/paper.pdf` (13 pp. at review, 14 after)

**Conflict:** reviewer is the author. **Access:** extracted text; figures re-rendered from source.

## Recommendation: Minor revision

Round 04 found one stale value and one substantive result that **partially reverses round 03's
conclusion**. The loop does not stop here.

## Critical

**C6 — Round 03 declared the mechanism open; it is not. Extrapolation distance explains the level
failure.**
*Location:* §5.5, conclusion. *Confidence:* High.

`link_cv.csv` now carries `extrapolation_distance` — how far a held-out family's feature
distribution sits outside the training families' support. Across the 15 families:

| correlates with | r |
|---|---:|
| absolute level bias | **+0.780** |
| raw R² | −0.657 |
| within-family Spearman | **−0.223** |

Extrapolation distance strongly predicts the *level* error and barely touches the *ordering*. That
is precisely the asymmetry the paper reports, and it now has a measured mechanism rather than an
open question. Error counters sit furthest outside the training support (3.73, next highest 2.45)
and are the worst case on every metric.

This does **not** restore the naive disjoint-band story that round 03 correctly rejected. The
synthetic `disjoint` arm destroyed the ordering because forcing non-overlapping bands removes the
shared structure the ranking depends on — a stronger intervention than the real data applies. Real
families overlap enough to share a ranking while still requiring extrapolation for the level. Both
findings stand; round 03 was right to reject the synthetic arm as a model of M100 and wrong to
conclude no mechanism was available.

*Fix:* applied. The paper now reports extrapolation as the mechanism, with the distinction from the
synthetic arm stated explicitly.

## Major

**M9 — On a scale-free metric the model beats baseline for 13 of 15 families, not 9.**
`mae_skill` (mean absolute error against the same train-mean baseline) is positive for **13/15**
families with mean **+0.20**, against 9/15 on R². Since the paper's own argument is that R² is
dominated by level error, reporting only R² understates the result on exactly the axis the paper
says is misleading. Added as a complementary metric with the caveat that the two answer different
questions.

**M10 — Stale null value.** The random-group null was re-run; median R² is +0.349, not the +0.33 the
paper carried in four places. Fixed. **Third consecutive round in which the manuscript lagged the
tables** — see the convergence note.

## Moderate

- **Mo8** `skill_sd_test` and `mae_baseline` are computed and unused in the text. Not obviously
  needed; noted so a later round does not rediscover them as missing.
- **Mo9** `scripts/11_protocol_control.py` was renamed to `12_protocol_control.py`; the paper does
  not reference script numbers, so no text change needed, but the pipeline table in §4.7 lists 11
  stages and there are now 12. Fixed in passing.

## Reference audit

No change. Bibliography 12 entries: 5 read in full, 7 definition-only and paywalled. No wrong
papers, no wrong author names, no unsupported claims. The `extrapolation_distance` measure is
computed from the study's own features and introduces no external method, so no new citation
obligation.

**Unchanged and unfixable here:** three entries cite a version of record while a preprint was read;
the AAAI PDF for Borghesi et al. 2019 remains unobtainable (OJS 404).
