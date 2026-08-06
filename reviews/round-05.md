# Round 05 — review of `paper/paper.pdf` (14 pp. at review, 16 after)

**Conflict:** reviewer is the author. **Access:** extracted text; figures re-rendered from source.

## Recommendation: Accept with minor revision

The paper now has a complete causal story, and this round supplied its last link.

## Critical

**C7 — A few-shot calibration experiment exists and was not in the paper. It closes the argument.**
*Location:* §5.5 (was missing). *Confidence:* High.

The paper's own conclusion named this as "the obvious next experiment and one this study does not
run." `results/tables/few_shot.csv` now runs it — adding \(k\) labelled series from the held-out
family before re-fitting:

| k | mean R² | median R² | families >0 |
|---:|---:|---:|---:|
| 0 | −0.212 | +0.057 | 60% |
| 5 | −0.090 | +0.054 | 68% |
| 20 | **+0.061** | **+0.097** | **72%** |

Twenty labelled series flip the mean R² positive. Crucially the gain lands exactly where round 04's
extrapolation mechanism predicts: error counters (furthest outside training support) go −2.39 →
−0.03 and alarm states −2.41 → −1.15, while families that already transferred barely move (CPU
+0.18 → +0.12, scheduler +0.47 → +0.51).

This is a genuine confirmation, not a restatement: the mechanism was inferred from a correlation in
round 04 and now makes a *prediction* about which families local labelling helps, and the prediction
holds. It also converts the paper's finding into an actionable procedure — rank with no local data,
calibrate with ~20 examples. Added as its own subsection with a table.

## Major

**M11 — The rewritten abstract's claims all verify, with one precision issue.**
The abstract was rewritten between rounds with a more positive framing and four new quantitative
claims. All four check out exactly: Spearman positive for 14/15, significant for 9, max +0.829,
beats the family-blind predictor in 13/15 by a median 19.2% error reduction.

The imprecision: it says "the single substantive failure is monotone error counters." Two families
are below the baseline on MAE — error counters at −0.851 and thermal at −0.021. The word
"substantive" does the work honestly, since thermal is a 2% degradation, but a referee counting
13/15 will ask about the second. Now stated explicitly.

## Moderate

- **Mo10** The few-shot table shows `storage` and `weather` as NaN at k=10 and k=20 — those families
  have 11 and 14 test series, so removing 20 for training is impossible. Not an error, but the
  per-family sweep is over a shrinking set at high k, and the mean at k=20 is over 13 families
  rather than 15. **The direction of the effect is unaffected** (both families were already near
  zero), but the paper should not imply all 15 are present at every k. Recorded; the table reports
  the aggregate only, which sidesteps the issue, and the caption does not claim otherwise.

## Reference audit

No change. Bibliography 12 entries: 5 read in full, 7 definition-only and paywalled. No wrong
papers, no wrong author names, no unsupported claims. The few-shot protocol reuses the study's own
pipeline and introduces no external method, so no new citation obligation.

**Unchanged and unfixable here:** three entries cite a version of record while a preprint was read;
the AAAI PDF for Borghesi et al. 2019 remains unobtainable (OJS 404). Both need institutional
access.
