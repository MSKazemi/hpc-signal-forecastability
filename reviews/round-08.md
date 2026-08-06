# Round 08 — review of `paper/paper.pdf` (19 pp.)

**Conflict:** reviewer is the author. **Access:** extracted text; figures re-rendered from source.

## The loop's round-07 stop was premature

Round 07 declared the stop condition met. Two new open issues then appeared — **OI-15 (BLOCKING)**
and **OI-14** — and OI-15 attacks the paper's headline directly. Recording this rather than
quietly reopening: the stop rule tests whether *a round* found nothing, which is not the same as
the work being finished, and a stop can be invalidated by evidence arriving afterwards.

## Critical — already applied to the paper, verified here

**OI-15 is correct and the paper now implements it.** R² is `1 − SSE/SST` with `SST` about the
mean of the **held-out** family, so its comparator is an oracle that already knows the quantity the
model cannot know. `R² < 0` means *worse than that oracle*, not *no better than nothing* — and the
paper had been reading it as the latter throughout.

Verified against `link_cv.csv`: mean R² −0.167 against the family-blind baseline's **−18.35**. On
fractional error reduction against that baseline, **13 of 15** families transfer successfully at a
median **21%** reduction.

## Critical — found this round

**C9 — The paper misattributed its own worst fold.**
*Confidence:* High. It read "ranging from +0.42 to −2.56 (monotone error counters)". The −2.56 fold
is **alarm states**, not error counters, which score −1.83.

This inverts the paper's own argument. Alarm states are the family the model predicts *best* — mean
absolute error 0.033 against a baseline of 0.600, a 95% reduction — and they carry the worst R² in
the study. Error counters are the one genuine failure (68% worse than baseline) and score *better*
on R². Attributing the worst R² to the family that actually fails would let a reader conclude the
two criteria merely differ in scale. They do not: **they disagree about which family failed.** Now
stated explicitly.

**C10 — Two stale values in the alarm-state example, in both §5.4 and the conclusion.**
Mean absolute error given as 0.036 (the standard deviation, not the error); actual 0.033. R² given
as −2.05; actual −2.56. Both corrected in both locations.

## Reference audit

No change. 14 entries, 6 read in full, 8 definition-only and paywalled. No wrong papers, no wrong
author names, no unsupported claims. OI-14's estimator concerns (periodogram → Welch, DFA-1 fit
quality) are internal method choices and introduce no citation obligation.

**Unchanged:** three entries cite a version of record while a preprint was read; the AAAI PDF for
Borghesi et al. 2019 unobtainable after three attempts.
