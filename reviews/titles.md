# Title candidates

Scored 1--5 on accuracy (does it match what the paper found), specificity (could it describe
another paper), searchability (terms a reader would query), appeal (would a reviewer open it).

## Incumbent
**Why Are HPC Monitoring Signals Hard to Forecast? Intrinsic Predictability Across Eight Telemetry
Families of a Tier-0 Supercomputer**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 2 | 4 | 4 | 4 | **14** |

*Accuracy is the weak axis and it is the one that matters.* The paper does not answer "why"; it
finds that difficulty is ordinally portable and cardinally not. The title promises an explanation
the paper deliberately declines to give.

## Round 01 candidates

**T1 — Forecast Difficulty Transfers in Rank, Not in Level: Model-Free Predictability Across Eight
HPC Telemetry Families**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 3 | 4 | **17** |
States the actual finding. Searchability suffers slightly — "transfers in rank" is not yet a term
people query — but every other axis is strong.

**T2 — Ranking Is Portable, Accuracy Is Not: What Model-Free Measures Can and Cannot Predict About
HPC Telemetry Forecasting**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 4 | 3 | 5 | **17** |
Most readable and the "can and cannot" framing is honest about a mixed result. Slightly long.

**T3 — Persistence Is Hard to Beat: A Predictability Audit of Eight Telemetry Families on a Tier-0
Supercomputer**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 4 | 4 | 5 | 5 | **18** |
Leads with the capacity result, which is the most immediately useful finding and the most
searchable phrasing. Loses a point on accuracy because it foregrounds the secondary result and
says nothing about the transfer finding.

## Running leader after round 01
**T3** (18) on total, but **T1** (17) is the better scientific title because it names the primary
contribution. Deferring the decision to a later round, per the loop's final-round rule.

## Round 02 candidates

The round-02 findings shift what the title should foreground: a gzip compression ratio beats every
hand-designed entropy measure, and removing the entropy family *improves* transfer.

**T4 — What Transfers and What Does Not: Model-Free Predictability of HPC Telemetry Across Eight
Signal Families**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 4 | 4 | 4 | **17** |
Clean statement of the ordering/level split without jargon. Slightly generic opening clause.

**T5 — gzip Beats Entropy: Model-Free Forecastability Measures on a Tier-0 Supercomputer**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 3 | 5 | 4 | 5 | **17** |
Memorable and true, but it promotes a secondary finding to the headline and undersells the
transfer result. Accuracy suffers for that reason.

**T6 — Forecast Difficulty Is Ordinally Portable: Predictability Measures Across Eight HPC
Telemetry Families**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 3 | 4 | **17** |
The most precise title on offer. "Ordinally portable" is exact but is not a phrase anyone searches,
which costs it on searchability.

## Running leader after round 02
Still **T3** (18) on raw total. But T1/T6 state the primary contribution and T3 does not, and the
scoring weights searchability and appeal equally with accuracy, which flatters T3. Leaning T1 or a
T1/T6 hybrid for the final round; decision deferred per the loop rules.

## Round 03 candidates

The protocol control changes what the paper's strongest claim is. It is no longer only "difficulty
does not transfer" — it is "the ordering transfers, the level does not, and we have a positive
control proving the method could have found either."

**T7 — Ordering Without Magnitude: What Model-Free Measures Predict About HPC Telemetry
Forecastability**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 3 | 5 | **18** |
"Ordering without magnitude" is exact, short, and memorable. Searchability is the weak axis —
nobody queries that phrase — but the subtitle carries the searchable terms.

**T8 — A Positive Control for Predictability Transfer: Eight HPC Telemetry Families and Three
Synthetic Worlds**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 4 | 5 | 3 | 4 | **16** |
Foregrounds the methodological contribution, which is arguably the most reusable part. But it
promises a methods paper and this is an empirical one.

**T9 — Forecast Difficulty in HPC Telemetry Transfers in Rank but Not in Level**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 4 | 4 | **18** |
Declarative, complete, and every content word is searchable ("forecast difficulty", "HPC
telemetry", "transfer"). Slightly flat as prose, which is the only mark against it.

## Running leader after round 03
**T9 (18)** — ties T3 and T7 on total but wins on the axis that matters: it states the paper's
actual finding in terms a reader would search for. T3 foregrounds a secondary result; T7 is more
elegant but less findable. **T9 is the presumptive winner for the final round** unless a later
round changes the headline again.

## Round 04 candidates

Round 04 supplies the mechanism: extrapolation distance predicts the level error (r=+0.78) but not
the ordering (r=−0.22). A title can now name *why*, not just *what*.

**T10 — Extrapolation Breaks the Level, Not the Ranking: Predictability Transfer Across HPC
Telemetry Families**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 3 | 5 | **18** |
Names the finding and its cause. "Extrapolation" is searchable; the rest of the phrase is not.

**T11 — Which HPC Signals Are Hard to Forecast? Rank-Transferable, Level-Specific Predictability**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 4 | 4 | 5 | 4 | **17** |
Question form is highly searchable and echoes the original title's framing. The subtitle's jargon
is precise but dense.

**T12 — Model-Free Predictability Measures Rank HPC Telemetry Correctly but Cannot Calibrate It**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 4 | 4 | **18** |
"Rank correctly but cannot calibrate" is the finding in six words, and "calibrate" is the term the
forecasting literature would actually use for the level failure. Strong on every axis.

## Running leader after round 04
**T12 (18)** overtakes T9. Both state the finding; T12 uses *calibrate*, which is the established
term for exactly this failure and therefore more searchable and more precise than "level". T9
remains the fallback if a plainer title is wanted.

## Round 05 candidates

The few-shot result completes the arc: rank for free, calibrate with ~20 labels. A title can now
promise a procedure rather than only a finding.

**T13 — Rank for Free, Calibrate with Twenty: Transferring Forecast-Difficulty Estimates Across HPC
Telemetry Families**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 4 | 5 | **19** |
States the finding *and* the actionable procedure. "Twenty" is concrete and memorable; the subtitle
carries the searchable terms.

**T14 — Model-Free Forecast-Difficulty Estimates Transfer Ordinally and Calibrate with Few Labels**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 4 | 3 | **17** |
Most precise, least readable. "Transfer ordinally" is exact but stiff.

**T15 — Which Signals Are Hard to Forecast? Ranking Transfers Across HPC Telemetry Families,
Calibration Does Not**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 5 | 4 | **19** |
Question opening is the most searchable form and echoes the original title. Names both halves of
the finding. Slightly long.

## Running leader after round 05
**T13 and T15 tie at 19.** T13 leads on appeal and gives the reader the procedure; T15 leads on
searchability and preserves continuity with the original question framing. **T13 is the
presumptive winner** — the procedure is what a reader will remember and cite, and "calibrate with
twenty" is the paper's most transferable sentence.

## Round 06 candidates

The ceiling result reinforces the same axis: information-theoretic quantities rank difficulty well
and bound it badly. No new dimension, so these are refinements rather than departures.

**T16 — Ranking Difficulty Without Bounding It: Model-Free Predictability of HPC Telemetry**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 3 | 4 | **17** |
Captures both the transfer and the ceiling result in one clause. Less concrete than T13.

**T17 — Twenty Labels Beat an Entropy Bound: Calibrating Forecast Difficulty Across HPC Telemetry
Families**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 4 | 5 | 4 | 5 | **18** |
Provocative and true, but sets up a comparison the paper does not literally run — the ceiling and
the few-shot result answer different questions. Accuracy drops for that.

**T18 — What Model-Free Measures Know About HPC Telemetry: Rank Yes, Magnitude No**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 4 | 4 | 4 | **17** |
Plain and accurate. "Rank yes, magnitude no" is memorable; the opening clause is a little soft.

## Running leader after round 06
**T13 holds at 19.** Nothing this round beats it, and the ceiling finding strengthens rather than
redirects the argument T13 states. T13 remains the winner for the final round.

## Round 09 candidates

**T19 — Rank Without Calibration: Model-Free Forecast-Difficulty Estimates Transfer Across Eight
HPC Telemetry Families**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 4 | 3 | **17** |
Accurate and specific, but "rank without calibration" reads as a limitation where T13's "rank for
free" reads as a result. Same content, weaker framing.

**T20 — The Criterion Decides the Answer: Grouped Cross-Validation on HPC Telemetry**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 4 | 3 | 3 | 4 | **14** |
Round 08's finding is real and general, but it is a methodological note inside the paper, not the
paper. A title promising it would misdescribe the contribution.

**T21 — Twenty Series per Family: Transferring Forecast-Difficulty Estimates Across HPC Telemetry**
| accuracy | specificity | searchability | appeal | total |
|---:|---:|---:|---:|---:|
| 5 | 5 | 4 | 4 | **18** |
The closest challenger yet — concrete and it survives round 09's correction (the calibration
result strengthened to −0.26 → +0.06). But it drops the ordering half of the finding, which is the
part that works with no local data at all.

## Running leader after round 09
**T13 holds at 19.** Nine rounds have not displaced it, and round 09 strengthened rather than
qualified the claim it makes: the "rank for free" half is unchanged and the "calibrate with twenty"
half improved once the k-sweep was restated on a matched family set.
