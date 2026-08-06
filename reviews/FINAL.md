# FINAL — consolidated review history

**Paper:** `paper/paper.tex` → `paper/paper.pdf`, 19 pp.
**Loop:** 10 rounds of review → revise → re-review. The stop condition was recorded as met at
round 07 and then invalidated by evidence arriving afterwards; it was met again, and properly, at
round 10.
**Repository:** https://github.com/MSKazemi/hpc-signal-forecastability (public)

> **Conflict of interest, stated once and meant.** Every review in this loop was written by the
> paper's author. That is structurally biased toward leniency, and no amount of adversarial intent
> removes it. What compensates: every Critical and Major finding is tied to a recomputation from a
> committed CSV that a third party can repeat. What does not compensate: framing choices, where an
> author is least able to see their own blind spots. **This loop is not a substitute for
> independent review.**

## What the loop changed

The paper began the loop stating a conclusion its own data did not support, and ended stating a
five-link causal argument. It went 10 → 19 pages and Major revision → Accept with minor revision.

| round | the finding that mattered |
|---|---|
| 01 | The central claim was wrong: the measures transfer in **ordering** (Spearman +0.50) but not in **level**. The text said "transfer weakly" because it predated the level/ordering decomposition. Also added the random-group null, which was in the tables and not the paper. |
| 02 | **Every linking number was stale** after the profile grew to 21 measures. Removing the entropy family *improves* transfer (−0.079 vs −0.189), and a gzip compression ratio outranks every hand-designed entropy measure (r = −0.42). |
| 03 | Added the **synthetic positive control**: where a portable law exists the protocol recovers it (R² +0.25, 13/15). Without it, "no portable law" was indistinguishable from "our method cannot find one". The control also **refuted the mechanism its own docstring proposed**. |
| 04 | The mechanism is **extrapolation distance** — r = +0.78 with level bias, only −0.22 with ordering. This reversed round 03's "mechanism is open". On a scale-free metric the model wins 13/15 families, not 9/15. |
| 05 | **Few-shot calibration**: 20 labelled series flip the mean R² positive, and help most exactly where extrapolation is worst — the prediction round 04's mechanism makes, confirmed. |
| 06 | The **Fano ceiling is not a floor**: 77.5% of series exceed it. Reporting it as the "irreducible error" — which is what the open issue asked for — would have contradicted the paper's own data three times in four. It *is* the strongest ordinal predictor (Spearman +0.69). |
| 07 | Cited the Fano construction. Found a **published statement of the same caveat** in a source that was read. No other findings — stop condition recorded as met. |
| 08 | The stop was premature: OI-15 arrived and was correct — **R²'s comparator is an oracle** that knows the held-out family's mean, so "R² < 0" never meant "no better than nothing". Found the paper had **misattributed its own worst fold**: −2.56 is alarm states, the family it predicts *best* (95% error reduction), not the error counters that actually fail. The two criteria disagree about which family failed. |
| 09 | Stopped reading the numbers and **re-ran the scripts**. Found a Table row that **no committed artefact reproduced** (hand-entered, three values stale), a table **stale against its own generating code** since round 03 (OI-16), a **duplicate `\label`** the build check was structurally unable to see, and a "families > 0" column that counted draws — which had the paper contradicting itself about its own experiment in two different sections. |
| 10 | Applied round 09's method to the figures — the one artefact class it had not covered. All six regenerate identically and agree with their tables on visual inspection. **No new findings; stop condition met, this time for the right reason.** |

## The pattern worth recording

Four separate rounds found a claim that was *natural* to make and contradicted by the data:

1. the outlier-driven mean R² (round 01, and again at a different scale in a later re-run),
2. disjoint parameter bands as the mechanism (round 03),
3. entropy measures being merely redundant rather than harmful (round 02),
4. the Fano ceiling as an error floor (round 06).

Each was caught by recomputation, not by intuition. Three rounds also found the manuscript lagging
the analysis tables — the characteristic failure of a project where the code moves faster than the
prose.

## Title

**Chosen: "Rank for Free, Calibrate with Twenty: Transferring Forecast-Difficulty Estimates Across
Eight HPC Telemetry Families"** (T13, score 19/20).

*Rationale.* The original title — "Why Are HPC Monitoring Signals Hard to Forecast?" — promises an
explanation the paper deliberately declines to give, and scored 2/5 on accuracy for that reason.
Eighteen candidates were scored across seven rounds on accuracy, specificity, searchability and
appeal. T13 states both the finding and the procedure a reader can act on, and "calibrate with
twenty" is the paper's most transferable sentence. Runner-up **T15** ("Which Signals Are Hard to
Forecast? Ranking Transfers Across HPC Telemetry Families, Calibration Does Not", also 19) is the
fallback if a question-form title is preferred for continuity.

## What the paper now claims

1. The monitoring system is itself non-stationary — 104 of 573 (plugin, metric) pairs present in
   all 31 months, all IPMI.
2. Much of what is monitored never changes — 64.8% of Nagios series constant, against 8.4% of IPMI.
3. Model capacity does not help; a persistence forecast beats every heavier tier at every horizon
   (paired Wilcoxon, p < 10⁻²⁰), and this is **not** an artefact of recursive forecasting — a direct
   multi-horizon control still loses to persistence.
4. Predictability measures **rank** signals in an unseen family correctly (Spearman +0.50, positive
   14/15) but **cannot calibrate** the absolute skill (mean R² −0.19). Extrapolation distance
   explains the asymmetry, and ~20 local labels repair it.

## What remains open

- **OI-6** — no true sequence model (TCN, PatchTST, pretrained forecaster). Narrowed by the direct
  multi-horizon control, not closed.
- **A bound in MASE units.** The Fano ceiling is not one. Would need a k-nearest-neighbour analog
  estimator on the continuous series.
- **The mechanism behind the level offset** is *identified* (extrapolation) but not *explained* —
  why families sit where they do in feature space is not addressed.
- **Three references cite a version of record while a preprint was read**; the AAAI PDF for
  Borghesi et al. 2019 is unobtainable after three attempts. Needs institutional access.
- **Eight of fourteen references are unread** — all paywalled, all definition-only, none credited
  with a finding.
- **Independent review.** See the conflict statement above.

---

## Addendum after rounds 08–10

### The stop condition was wrong once, and the reason generalises
Round 07 recorded the loop as finished. Rounds 08 and 09 then found, between them, the single
worst defect in the study (a table row no artefact reproduced) and a self-contradiction spanning
two sections. The stop rule tests whether *a round* found nothing — which is not the same as the
work being finished, and says nothing about the classes of defect no round has yet looked for.

### What actually found things, ranked
1. **Re-running the generating scripts and diffing** (round 09) — found two Critical defects in one
   pass, neither visible in the text. Eight rounds of careful reading had missed both.
2. **Recomputing every numeric claim from the committed tables** — found stale numbers in rounds
   02, 04, 08 and 09. Reliable, but one at a time.
3. **Reading for argument** — found the round-01 and round-06 reversals, where the data supported a
   *different* conclusion rather than a wrong number. Nothing mechanical would have caught these.

The order is worth stating because the cheapest check was the most productive one and it was
introduced ninth.

### Four rounds found the same shape of error
A claim that was natural to make and contradicted by the study's own data: the outlier-driven mean
(round 04), disjoint bands as the mechanism (round 03), entropy as merely redundant (round 02), and
the Fano ceiling as an error floor (round 06). Round 08 adds a fifth — reading "R² < 0" as "no
better than nothing" — and round 09 a sixth, where a mislabelled column had the paper asserting in
§5.3 what it correctly denied in §5.5. In every case the correction made the paper's claim
narrower and its evidence stronger.

### Title
**T13 — "Rank for Free, Calibrate with Twenty: Transferring Forecast-Difficulty Estimates Across
Eight HPC Telemetry Families"** (19/20), set in the paper. It led from round 06 and survived four
further rounds against 21 candidates. Round 09 strengthened it: the "rank for free" half is
untouched, and the "calibrate with twenty" half improved from −0.21 → +0.06 to −0.26 → +0.06 once
the k-sweep was restated on a family set that is constant across its own rows.

### What remains open
- **OI-6** — no true sequence model (TCN, PatchTST) has been run; the capacity claim rests on
  gradient-boosted trees and a small MLP.
- **No bound in MASE units.** The Fano ceiling is next-symbol accuracy on a discretised alphabet;
  the forecast results are MASE. The two are not on one axis and the paper does not pretend they are.
- **OI-14** — DFA-1 fit quality is unreported and DFA-2 was not run.
- **OI-16** — nothing re-runs `make reproduce` automatically. This round's finding was found by
  hand, and the next one of its kind will be too until a gate does it.
- **References** — 8 of 14 unread (paywalled, definition-only, no finding attributed); 3 cite a
  version of record while a preprint was read.
- **Independent review.** Still the largest gap, and unchanged by ten rounds of self-review.
