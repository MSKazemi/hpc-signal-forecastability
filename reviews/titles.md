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
