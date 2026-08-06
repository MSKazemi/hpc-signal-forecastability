# FINAL — consolidated review history

**Paper:** `paper/paper.tex` → `paper/paper.pdf`, 18 pp.
**Loop:** 7 rounds of review → revise → re-review, stopped early on the no-new-findings condition.
**Repository:** https://github.com/MSKazemi/hpc-signal-forecastability (public)

> **Conflict of interest, stated once and meant.** Every review in this loop was written by the
> paper's author. That is structurally biased toward leniency, and no amount of adversarial intent
> removes it. What compensates: every Critical and Major finding is tied to a recomputation from a
> committed CSV that a third party can repeat. What does not compensate: framing choices, where an
> author is least able to see their own blind spots. **This loop is not a substitute for
> independent review.**

## What the loop changed

The paper began the loop stating a conclusion its own data did not support, and ended stating a
five-link causal argument. It went 10 → 18 pages and Major revision → Accept with minor revision.

| round | the finding that mattered |
|---|---|
| 01 | The central claim was wrong: the measures transfer in **ordering** (Spearman +0.50) but not in **level**. The text said "transfer weakly" because it predated the level/ordering decomposition. Also added the random-group null, which was in the tables and not the paper. |
| 02 | **Every linking number was stale** after the profile grew to 21 measures. Removing the entropy family *improves* transfer (−0.079 vs −0.189), and a gzip compression ratio outranks every hand-designed entropy measure (r = −0.42). |
| 03 | Added the **synthetic positive control**: where a portable law exists the protocol recovers it (R² +0.25, 13/15). Without it, "no portable law" was indistinguishable from "our method cannot find one". The control also **refuted the mechanism its own docstring proposed**. |
| 04 | The mechanism is **extrapolation distance** — r = +0.78 with level bias, only −0.22 with ordering. This reversed round 03's "mechanism is open". On a scale-free metric the model wins 13/15 families, not 9/15. |
| 05 | **Few-shot calibration**: 20 labelled series flip the mean R² positive, and help most exactly where extrapolation is worst — the prediction round 04's mechanism makes, confirmed. |
| 06 | The **Fano ceiling is not a floor**: 77.5% of series exceed it. Reporting it as the "irreducible error" — which is what the open issue asked for — would have contradicted the paper's own data three times in four. It *is* the strongest ordinal predictor (Spearman +0.69). |
| 07 | Cited the Fano construction. Found a **published statement of the same caveat** in a source that was read. No other findings — stop condition met. |

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
