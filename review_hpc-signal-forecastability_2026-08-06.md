# Review — "Why Are HPC Monitoring Signals Hard to Forecast?"

**Manuscript:** `paper/paper.pdf`, 8 pp., working draft, 2026-08-06
**Depth:** deep audit · **Reviewer:** senior referee
**Recommendation:** **Weak Reject (provisional)** — the central negative claim is not supported at
the strength stated, but the defect is a reporting choice and is repairable without new experiments.

## Conflict of interest — read this first

**The reviewer is the manuscript's author.** This review is therefore structurally biased toward
leniency. It was conducted adversarially to compensate, and every Critical/Major finding is tied
to a locator and a recomputation a third party can repeat from the committed tables. It is not a
substitute for independent review.

## Access and verification coverage

- Manuscript text: **complete** (8/8 pp., via extracted text — see limitation below)
- Figures/tables: **complete** — all 5 generated figures inspected as rendered images; both
  in-paper figures and Table 1 checked
- References: **9/9** audited separately (`private/reference-audit-workspace/reference-audit.md`);
  4 read in full, 5 paywalled and definition-only
- Numbers ledger: **21 decision-relevant values** recomputed from `results/tables/*.csv`

**Limitation:** `pdftoppm` is absent, so the Read tool could not render PDF pages. Manuscript text
was extracted with pypdf and figures were re-rendered to PNG from the same code and data that
produced the embedded PDFs. Layout defects visible only in the compiled PDF (overfull boxes,
figure placement, page breaks) were **not** assessed. Confidence on presentation findings is
lowered accordingly; confidence on content findings is unaffected.

## Executive assessment

The paper does something genuinely uncommon: it states a hypothesis, builds an apparatus capable
of refuting it, and reports the refutation. The engineering is unusually well controlled — a
pre-registered config, an a-priori taxonomy, leave-one-family-out validation, ablations designed
to attack the headline, and a threat register with twelve entries. The numbers in the text
reconcile against the committed tables almost perfectly (19 of 21 exact).

But the headline conclusion is **overstated in the negative direction**, which is an unusual and
easily-missed failure mode. "We find no portable law of forecast difficulty," supported by a mean
held-out R² of −0.82, is driven almost entirely by a single outlier family. The median is
**+0.066**, seven of thirteen families are positive, and dropping the one worst family moves the
mean to **+0.028**. The evidence supports "the relation transfers weakly and inconsistently," not
"no portable law." Fixing this requires no new computation — only reporting the distribution
instead of its mean.

## Strengths

1. **Falsifiability is built in, not claimed.** The model suite spans four tiers precisely so
   that a monotone capacity–skill curve would refute the thesis; §5.3 reports that it does not.
2. **The MASE-denominator analysis is a real methodological contribution.** Showing that the
   same data ranks *statistical* first under a daily-seasonal denominator and *naive* first under
   a same-step denominator is a finding about how this literature reports results, not a footnote.
3. **The jitter/interruption dissociation (§5.2)** correctly overturns a standard summary
   statistic, with a clean mechanism: IPMI has 0% jittery series and 100% interrupted.
4. **Claim traceability.** Every reported number has a committed CSV behind it.
5. **Honest scoping.** OI-4, OI-6, OI-12 state limitations in the abstract and body rather than
   burying them.

## Findings

### Critical

**C1 — The headline negative claim is outlier-driven and overstated.**
*Location:* abstract ¶4; §5.4; conclusion ¶2. *Confidence:* High.
The paper reports "a mean R² of −0.82" and concludes "We find no portable law of forecast
difficulty." Recomputing from `results/tables/link_cv.csv` (13 held-out families):

| statistic | value |
|---|---:|
| mean R² (reported) | −0.815 |
| **median R²** | **+0.066** |
| range | [−10.932, +0.570] |
| families with R² > 0 | **7 of 13** |
| mean excluding worst family | **+0.028** |

`error_counter` alone contributes −10.93; the mean is not a summary of this distribution. The
strongest defensible claim is that transfer is **weak, inconsistent, and fails badly for monotone
counters** — which is a more interesting result than the one stated, because it localises the
failure. *Fix:* report median and range alongside the mean, state the 7/13 split, and rewrite the
conclusion to "transfers weakly and inconsistently, and fails outright for monotone counters."
The `error_counter` case deserves its own paragraph: drift forecasts counters near-perfectly and
no predictability feature anticipates that, which is a concrete, explicable failure.

### Major

**M1 — Title and abstract claim nine telemetry families; eight are characterised.**
*Location:* title; abstract ¶2; Table 1. *Confidence:* High.
`manifest.parquet` contains 8 plugins. The ninth, `job_table`, is excluded as not a time series
(OI-8, and Table 1 says so). The title "Across Nine Telemetry Families" and "we characterise
telemetry from nine heterogeneous plugin families" both overstate scope. The abstract's own
enumeration lists only seven categories. *Fix:* "eight" throughout, or "nine collected families,
eight of which are time series."

**M2 — The series count is wrong: 1,419 stated, 1,402 analysed.**
*Location:* abstract ¶2 / §4.3 (`\num{1419}`). *Confidence:* High.
`features.parquet` holds 1,402 rows. 1,419 is the pre-regrid sample size; 17 series fell below
the minimum length when resampled to the 15-minute grid. *Fix:* cite 1,402 and state the 17
dropped and why.

**M3 — The abstract states as a position the thesis the paper refutes.**
*Location:* abstract ¶1 vs ¶4. *Confidence:* High.
¶1: "We argue instead that the difficulty is largely intrinsic to the signals, differs
systematically between signal families, and can be quantified without fitting any forecaster."
¶4 then reports that it does not transfer across families. A reader who stops after ¶1 takes away
the opposite of the paper's finding. *Fix:* "We test whether…" and state the outcome in ¶1.

**M4 — "A tiered suite ranging from naive baselines to gradient-boosted trees" omits the neural
tier whose numbers the same abstract reports.**
*Location:* abstract ¶2 vs ¶3. *Confidence:* High. *Fix:* "…to gradient-boosted trees and
feed-forward neural networks."

**M5 — "A fixed panel of 96 entities" is imprecise where a secondary key exists.**
*Location:* §4.2. *Confidence:* High.
96 caps the *primary* entity (node/device/panel) and is correctly enforced. But Nagios keys a
series by node **and** check description, reaching **1,484** distinct series keys per
metric-month. *Fix:* "96 primary entities; families with a secondary key (e.g. Nagios check
description) yield proportionally more series."

### Moderate

**Mo1 — Three of five generated figures are unused, and one included figure is never referenced.**
`constant_share.pdf`, `sampling_irregularity.pdf`, `landscape.pdf` are generated but not included,
though §5.1 and §5.2 discuss exactly their content in prose. `fig:coverage` is included but never
`\ref`'d. *Fix:* include the sampling figure in §5.2 (it is the OI-1 evidence) and the constant-share
figure in §5.1; reference `fig:coverage` from §5.

**Mo2 — The skill figure's x-axis asserts an unestablished ordering.**
The axis reads "model tier (increasing capacity)" with ml → neural, implying the MLPs have greater
capacity than the boosted trees. No parameter counts or FLOPs are given, and the two are not
obviously ordered. *Fix:* drop "(increasing capacity)" or report the capacity measure.

**Mo3 — Ambiguous rounding.** "permutation entropy at −0.35"; the value is −0.345, which rounds to
−0.34 under round-half-even. *Fix:* print −0.345.

**Mo4 — No uncertainty on the tier medians.** §5.3's table gives medians over 331 series with no
spread or test. The naive-vs-statistical gap at h=4 (0.127 vs −0.030) carries the "capacity does
not help" claim and may not be significant. *Fix:* add IQR or a paired test across series.

**Mo5 — The recursive-forecasting confound is disclosed but not bounded.** §5.3 correctly notes
that ML/neural models forecast recursively and that this compounds error. Since this is the main
alternative explanation for the capacity result, it deserves a direct multi-horizon model on a
subsample rather than only a caveat.

### Minor

- **Mi1** `rostaghi2016dispersion` is cited but dispersion entropy is never implemented — remove.
- **Mi2** The ExaData self-citation is undisclosed; an anonymity risk at a double-blind venue.
- **Mi3** Three references cite a version of record while a preprint was read (see reference audit).
- **Mi4** §5.2's claim that 15-minute aggregation is justified by the ExaData authors' choice is
  correct but should note theirs covers IPMI only, where this study applies it to all eight families.

## Questions for the author

1. What is `error_counter`'s R² driven by — is it the monotone-counter drift effect alone? If so,
   does excluding monotone counters as a documented class restore transfer?
2. Are the tier differences at h=1 and h=4 statistically distinguishable across the 331 series?
3. Why is the 15-minute grid the right *scientific* choice rather than only the tractable one —
   would a 5-minute grid retain enough gap-free run length?

## Ordered revision plan

1. **C1** — report the R² distribution, not its mean; rewrite the conclusion; add the
   `error_counter` paragraph. *(no new computation)*
2. **M1–M5** — fix scope, counts, abstract framing, suite description, panel wording. *(text only)*
3. **Mo4** — add dispersion/significance to the tier table. *(small computation)*
4. **Mo1, Mo2** — include the unused figures; fix the axis label. *(small)*
5. **Mo5** — run a direct multi-horizon model on a subsample to bound the recursive confound.
6. **Mi1–Mi4** — bibliography and disclosure hygiene.

Items 1–2 and 4 would move this to **Weak Accept**. Item 5 would make the capacity claim solid.

## What would change the recommendation

The recommendation rests on **C1** alone. The apparatus, controls, and traceability are already at
an acceptable standard; the defect is that the paper's own data supports a more nuanced and more
interesting conclusion than the one it states. Correcting the statistic and the conclusion — which
requires no new experiments — removes the basis for rejection.
