# Open Issues

Everything in this study that is **not yet settled**, with what would settle it. Each item has an
ID cited from `paper/paper.tex` so the paper and this register stay in sync.

Status: `BLOCKING` = must be resolved before submission · `IMPORTANT` = weakens a claim if
unresolved · `OPEN` = worth doing, not load-bearing.

This register is written **before** the results, deliberately. Every threat listed here was
identified from the dataset documentation and a structural inspection of the archives, not
discovered after seeing an inconvenient number.

---

## OI-1 — Ganglia's irregular sampling confounds predictability with instrumentation `RESOLVED`

> **Both halves now settled.** The measurement problem was resolved by separating jitter from
> interruption (below). The conditioning test has now run: removing the sampling and quantisation
> covariates *improves* the linking model slightly (\(-0.79\) against \(-0.82\)), and using them
> alone collapses it (\(-8.03\)). Whatever the predictability measures capture, it is not how the
> data was sampled. The between-family differences are not an instrumentation artefact.

**Resolved: "irregular sampling" was two different things.** Measured across all 159,506 series:

| plugin | series with jitter > 0.01 | series with a gap > 100× median |
|---|---:|---:|
| IPMI | **0.0%** | **100%** |
| Ganglia | **81.0%** | 74.9% |
| Logics | 40.8% | 30.5% |
| SLURM | 10.5% | 91.5% |
| Schneider | 0.0% | 52.6% |
| Vertiv | 0.0% | 61.1% |
| Nagios | 0.0% | 18.1% |
| Weather | 0.0% | 11.1% |

The two are almost orthogonal. IPMI samples with a *perfectly* regular typical interval and is
*universally* interrupted — every single IPMI series contains a gap more than a hundred times its
median interval. Ganglia is the only plugin with substantial jitter in the interval itself, which
is precisely what the ExaData documentation warns about and what the combined measure denied.

This is why the original `dt_cv` ranked IPMI as the least regular plugin: its rare enormous gaps
(gap fraction 0.001, but each gap thousands of times the median) dominated the coefficient of
variation entirely, giving `dt_cv` = 12.7 for a signal whose sampling is otherwise exact.



**Historical note — the trap that produced this entry.** The first attempt measured irregularity
as the coefficient of variation of the inter-sample interval, `dt_cv`, over every interval. That
reported IPMI as the *least* regular plugin, contradicting the dataset documentation, because a
single multi-day outage in a month of 20-second samples dominates the statistic. `dt_cv` was an
outage detector wearing a jitter label. Left unnoticed it would have put a claim in the paper that
contradicted the dataset's own documentation on the strength of an artefact.

**Still worth doing.** Resample a matched IPMI signal onto Ganglia's observed interval pattern and
measure how much predictability is destroyed. That would give a direct instrumentation penalty
rather than the indirect ablation evidence used here.

---

## OI-2 — The monitoring infrastructure is itself non-stationary `IMPORTANT`

> **Downgraded from BLOCKING.** It was blocking for *cross-month* claims. The study as reported
> makes none: every result pools months and is stated per signal family, and the coverage
> instability is reported as a finding in its own right rather than used as a covariate. It
> returns to blocking the moment a claim of the form "metric X became less predictable in 2022"
> is made.

**Why it matters.** Structural inspection of the monthly archives shows plugin coverage changing
over the campaign:

| Month | Plugins present | Ganglia metric partitions |
|---|---|---|
| 20-04 | ipmi only | — |
| 20-11 | ipmi, ganglia, slurm, nagios, job_table | 67 |
| 21-08 | all 9 | 99 |
| 22-06 | all 9 | 355 |

Any cross-month comparison therefore confounds *signal behaviour* with *changes to the monitoring
system*. A metric that "becomes less predictable in 2022" may simply have started being collected
differently, or at a different cadence, or from more nodes.

**To settle.** Restrict all cross-month claims to metrics present with comparable cadence and
entity coverage in every compared month (an explicit intersection set, committed as a table).
Report the size of that intersection honestly. Treat coverage growth as a *result about
operational monitoring*, reported separately, not as a nuisance to be smoothed over.

---

## OI-3 — Four sampled months may not represent 31 `IMPORTANT`

**Why it matters.** Disk capacity (146 GB free against 420 GB of archives) forces month sampling.
Months 20-04, 20-11, 21-08, and 22-06 were chosen to span the observed instrumentation eras, but
seasonal effects (summer cooling stress vs winter), workload campaigns, and one-off incidents are
not evenly represented.

**To settle.** The 31-month `time_aggregated` IPMI arm requires no extraction and *is* complete —
use it to check whether the predictability profile of IPMI signals in the four sampled months is
representative of all 31. If IPMI is representative, that is evidence (not proof) that the
sampling is not adversarial for the other plugins.

---

## OI-4 — The study analyses the aggregated representation, not the raw sensor stream `IMPORTANT`

> **Escalated from a two-arm comparison to a single stated scope.** The plan was to run both a
> native-cadence and an aggregated arm and report them separately. The native arm is not runnable:
> at native cadence the gaps fragment every family beyond use. A Ganglia month has 43,199 grid
> slots and a longest gap-free run of **149** samples; Logics manages **59** of 37,099. Nothing can
> be forecast at a 96-step horizon on runs that short, and imputing across the gaps would invent
> the structure being measured.
>
> Everything therefore runs on a common 15-minute grid, where empty slots fall from ~12% to under
> 1% and gap-free runs reach 500–3,000 points across every plugin. This is also the aggregation the
> ExaData authors chose for their own published anomaly-detection dataset.
>
> **What it costs, and it is not small.** Aggregation is a low-pass filter and raises apparent
> predictability. Every skill number here describes 15-minute aggregates. The paper says so in the
> abstract rather than in a limitations paragraph, because a reader who assumes these are
> 20-second-sensor results would draw the wrong operational conclusion.

---

## OI-4b — Original wording: the two arms measure different objects `SUPERSEDED`

**Why it matters.** The ready-made `time_aggregated` dataset is 15-minute resampled with
`_avg/_std/_min/_max` per metric. Aggregation is a low-pass filter: it *raises* apparent
predictability by discarding high-frequency variation, and the `_std/_min/_max` channels are
derived statistics, not measurements. Predictability measured on 15-minute aggregates is not the
predictability of the 20-second sensor stream.

**To settle.** Run both arms and report them separately, never pooled. Quantify the aggregation
effect directly by aggregating native-cadence IPMI to 15 minutes ourselves and comparing the
predictability profile against the native one on the same series.

---

## OI-5 — The MASE denominator changes which models appear to win `IMPORTANT`

> **Measured, and larger than anticipated.** This was filed as a routine "pick a defensible
> seasonal period" concern. It turned out to determine the paper's headline.

Against a **daily-seasonal** denominator (m=96 on a 15-minute grid) median skill at a one-hour
horizon is \(+0.769\); against a **same-step** denominator it is \(-0.235\). The daily
denominator compares a one-hour-ahead forecast against a one-day-lag baseline, which is not
like-for-like and flatters every model at short horizons. At a 24-hour horizon the two give
\(+0.233\) and \(-4.154\).

It also reverses the ranking the paper reports. Same-step: naive leads at every horizon
(0.477 / 0.127 / −0.513 / −3.241). Daily-seasonal: the statistical tier leads
(0.892 / 0.838 / 0.755 / 0.303) and boosted trees overtake naive at the shortest horizon. A first
draft of the results reported a median best skill of 0.949 on the daily denominator alone, which
would have claimed near-perfect forecasting.

**Resolved by:** running both denominators on all 331 series and reporting the conservative one as
primary, with the other shown alongside. The figure code filters to one denominator explicitly,
because an earlier version pooled them and the pooled table inverted the tier ordering.

**Still open:** the seasonal period is fixed at one day from the cadence rather than estimated per
family. A family with no daily cycle is scaled by a baseline that means little for it.

---

## OI-5b — Original wording: a defensible seasonal period `RESOLVED`

**Why it matters.** Skill is reported as `1 − MASE` against a seasonal naive baseline. MASE's
scaling term depends on the assumed seasonal period *m*. A daily period is defensible for
thermal, power, and utilisation signals driven by human working patterns; it is not obviously
correct for scheduler queue dynamics, alarm states, or weather. Choosing *m* per family after
seeing the results would be circular.

**To settle.** Fix *m* per family **a priori** from the dominant-period estimate computed in the
predictability phase (which uses no forecaster and no test data), record the choice in
`conf/`, and additionally report results for *m* = 1 (non-seasonal MASE) as a robustness check.

---

## OI-6 — No sequence model has been run `IMPORTANT`

**Why it matters.** A load-bearing part of the argument is "even strong models cannot beat the
intrinsic floor". The machine has 24 CPU threads and no GPU, and the sweep covers thousands of
series, so every model in the suite is small by necessity. A reviewer can reasonably object that a
larger or better-suited model would have done better, and the claim would collapse to "the models
we could afford did poorly".

**What is now run.** A capacity ladder rather than a single comparison, since saturation is a
claim about a curve: gradient-boosted trees at three capacities (8/15, 24/60, 48/200 lags and
iterations) and feed-forward networks at two (64-32 and 128-64-32 hidden units over 24- and
48-step lag windows).

**What is still missing.** `mlp` is a multilayer perceptron over a lag window — **not** a sequence
model. No TCN, N-BEATS, PatchTST, or pretrained forecaster has been run. The paper may therefore
say that skill saturates across the capacity ladder actually tested, and may not say that deep
models cannot help.

**One alternative explanation is now closed rather than caveated.** Every learned model forecasts
recursively, so error compounds over multi-step horizons, and that — rather than the signals —
could have produced the collapse of the learned tiers. `scripts/11_direct_control.py` fits the
same gradient-boosted learner directly for each horizon on matched windows. Recursion does cost a
great deal (at one hour, skill goes from −0.223 recursive to +0.114 direct), but the direct model
still loses to persistence at every horizon, so the capacity conclusion does not rest on the
recursion. Results in `results/tables/direct_vs_recursive.csv`.

**To settle.** Run one genuine sequence model, and ideally one zero-shot pretrained forecaster as
an upper reference point that costs no training. If skill saturates well before the largest model
tried, capacity is not the binding constraint and the argument survives.

**Fallback.** State the claim strictly as "skill saturates across the capacity ladder tested,
which spans four architecture families and roughly two orders of magnitude of parameter count".

---

## OI-7 — The irreducible-error floor was never computed `ADDRESSED`

> **A ceiling now exists, by a different and stronger route than the one planned.** The original
> plan — a k-nearest-neighbour analog bound plus the quantisation step — was never implemented, and
> would in any case have produced an *estimate* rather than a bound, which OI-7b correctly
> objected to. What is implemented instead is a genuine information-theoretic bound.

**What was added.** Each series is symbolised at its own resolution (its distinct values where
there are at most 16, equal-frequency quantiles otherwise), its entropy rate is estimated with the
Lempel–Ziv estimator `S = n log₂ n / Σ Λᵢ`, and the maximum predictability `Π_max` is obtained by
solving the limiting case of Fano's inequality

```
S = −[Π log₂ Π + (1−Π) log₂(1−Π)] + (1−Π) log₂(N−1)
```

for `Π`, following the construction of Song et al. (*Science* 327:1018, 2010). This is the only
quantity in the study that no forecaster can beat, which is what makes it able to answer the
question the whole paper is about: **is a family hard because the signal is at its information
limit, or because the models are weak?**

`symbolic_persistence_accuracy` supplies the matching achieved number — the accuracy of "repeat the
last symbol" on the *same* alphabet — because a ceiling is uninterpretable without a comparable
achievement. Persistence is the fair comparator rather than a straw man: this study finds it is the
strongest forecaster on this data at every horizon tested.

**Behaviour on known cases**, all pinned by tests:

| series | entropy rate (bits) | ceiling |
|---|---:|---:|
| constant | 0.000 | 1.000 |
| alarm state (1% switching) | 0.111 | 0.985 |
| monotone counter | 0.340 | 0.967 |
| smoothed thermal | 1.961 | 0.718 |
| white noise | 3.545 | 0.326 |

A fair coin recovers 1.0 bit to within 0.15, and for a first-order Markov chain — where Fano is
*tight* and the analytic optimum is `p + (1−p)/N` — the estimated ceiling matches that optimum to
within 0.05.

**Two honest limitations.** First, `Π_max` bounds *next-symbol* accuracy on a chosen alphabet, not
multi-step MASE, so it is not directly comparable to the study's skill numbers; the alphabet size
is carried alongside every ceiling for exactly this reason, and cross-family comparison requires
holding it fixed. Second, the match-length cap in the LZ estimator biases the ceiling *downward*,
which is the wrong direction for an upper bound; it is set high enough (512, against a typical
match length near 16) that it should not bind, but a series predictable enough to reach it would
have its ceiling under-reported rather than over-reported.

**The estimator is biased, and the direction is now measured rather than assumed.** Against Markov
chains whose entropy rate is known in closed form, at the n ≈ 2,000 this data provides:

| p(stay) | true rate | estimated | true ceiling | estimated ceiling |
|---:|---:|---:|---:|---:|
| 0.99 | 0.076 | 0.127 | 0.992 | 0.986 |
| 0.95 | 0.290 | 0.348 | 0.962 | 0.953 |
| 0.85 | 0.686 | 0.712 | 0.887 | 0.882 |

The Lempel–Ziv estimator converges from *above*, closing only near n = 16,000, so the derived
ceiling is an **under-estimate** and is not a bound. On M100, 248 of 1,402 series (18%) exceed it,
concentrated exactly among the near-deterministic ones. This is what OI-7b demanded: the quantity
is reported as an estimator with a validated bias direction, never as "the" irreducible error.

The bias direction is what makes it usable anyway. Because the ceiling is under-reported, any
headroom it shows is a **lower bound** on the true headroom — so "these models leave predictability
unclaimed" is the conservative reading. The converse claim, that a family sits *at* its limit,
cannot be established from a small positive gap and is asserted only where the gap is zero or
negative by more than the measured bias (≈0.01).

---

**RETRACTED: the two-regime reading, and what replaced it.** Comparing achieved next-symbol
accuracy against the estimated ceiling appeared to split the families into four at their limit and
nine leaving 12–31 points unclaimed. That reading required the ceiling to be approximately correct
for the signals it was applied to, and `scripts/13_ceiling_calibration.py` shows it is not.

For a Gaussian AR(1) binned into quantiles — the study's own symbolisation, on the smooth
continuous signals the physical families contain — the Bayes-optimal next-symbol accuracy is
computable in closed form and cannot be beaten by anything. The estimated ceiling exceeds it by
**0.24–0.30** across the whole persistence range, which brackets the 0.12–0.31 gaps observed. No
part of those gaps can be attributed to model weakness.

Two independent attempts to claim the supposed headroom agree it is absent: `symbolic_markov_accuracy`
(first-order Markov on the same symbols, fitted causally) scores below persistence in 13 of 17
families, and an AR(8) on the continuous values, binned identically, in 16 of 17.

**What the calibration establishes instead is more valuable than the claim it withdraws.**
Persistence comes within **0.008** of the Bayes optimum at every φ tested. For smooth continuous
signals observed at fixed resolution, repeating the last value is near-optimal — so the study's
capacity finding (§5.4: no heavier tier beats persistence) is *explained* rather than merely
observed. That is the answer to "why are HPC monitoring signals hard to forecast" for this class of
signal: they are not badly modelled, they are close to the limit of what one-step extrapolation at
this resolution can do.

**Unaffected by the retraction.** The four low-entropy families achieve 0.99+ in absolute terms and
no estimator error creates room above 1.0, so they are genuinely exhausted by persistence. The
withdrawal concerns only the nine continuous families.

**The general lesson for the measure.** The Fano ceiling is usable for *ordering* series by
difficulty — it remains the strongest single ordinal predictor in the study — and is not usable as
a *level*. Any use of it as an error floor, on this class of signal, will over-state achievable
predictability by an amount comparable to the quantity being measured.

---

## OI-15 — The headline used R², whose comparator is an oracle the model cannot have `BLOCKING`

> **This is the reason the study reads as a null result, and it is a reporting defect rather than
> a finding.** It supersedes the framing of the abstract, §5.4, and the conclusion.

**The mechanism.** R² is `1 − SSE/SST`, and `SST` is the sum of squares about the mean of the
**held-out** family. The implicit comparator is therefore a predictor that already knows what the
unseen family's average skill is — which is precisely the quantity a model predicting a family it
has never seen cannot know. "R² < 0" means *worse than that oracle*. It does **not** mean *no
better than nothing*, and the paper has been reading it as the latter.

**Consequence 1 — the denominator collapses on homogeneous families.** A family whose series nearly
all have the same skill has almost no `SST`, so R² divides by something near zero. The `alarm_state`
fold is the clearest case:

| | |
|---|---:|
| within-family standard deviation of skill | 0.036 |
| model mean absolute error | **0.036** |
| family-blind baseline mean absolute error | **0.600** |
| error reduction | **94%** |
| **reported R²** | **−2.05** |

The model predicts every held-out alarm series to within a thirtieth of the baseline's error, and
R² records a catastrophe.

**Consequence 2 — the honest baseline was already in the output and was never used as the
criterion.** `link_cv.csv` has always carried `r2_baseline`, the score of the train-mean predictor
on the same held-out series. It averages **−18.35** against the forest's **−0.19**. The model beats
the best family-blind predictor by two orders of magnitude in exactly the folds the headline counts
as failures.

**What the corrected criterion shows.** Scoring the same folds by fractional reduction in mean
absolute error against that train-mean predictor:

| | |
|---|---:|
| families that beat the family-blind baseline | **13 of 15** |
| median error reduction | **19%** |
| the one genuine failure | `error_counter`, 85% *worse* than baseline |

So predictability measures **do** transfer across signal families. They fail on exactly one
nameable class — monotone counters, where a drift forecast is near-perfect and no measure
anticipates it — and that localised failure is a more useful result than the global null the paper
currently reports.

**What must change.** The abstract, §5.4 and the conclusion currently assert that no portable
relation exists. They must instead report: the relation transfers, quantified against a baseline a
model could actually have; R² is reported alongside with its denominator problem stated; and the
counter family is given its own paragraph as the one place transfer genuinely fails. `mae_skill`,
`mae_baseline` and `skill_sd_test` are now first-class columns of `link_cv.csv`, and
`tests/test_link.py` pins the `alarm_state` case so the defect cannot silently return.

**The sharpest available demonstration that R² is the wrong summary here.** In the synthetic
control (OI-13), the `no_law` arm — where skill was *permuted across series*, so no relation exists
at all — scores mean R² **−0.070**. M100 scores **−0.189**. On the headline statistic the real data
transfers *worse than data with no relation in it*, while its within-family Spearman (+0.495) is
five times `no_law`'s (+0.100) and its MAE-skill (+0.192) is a hundredfold higher (+0.002). A
statistic that ranks genuine structure below noise is not measuring what the paper is asking.

**This is not metric-shopping, and the construction is the study's own.** Forecast skill in this
paper is already defined as `1 − MAE_model / MAE_baseline` — that is what MASE is, and what
`1 − MASE` means. `mae_skill` applies the identical construction one level up: the error of the
skill-*predictor* against the error of the best family-blind skill-predictor. Using a
relative-error criterion for the linking analysis makes it consistent with the criterion used for
forecasting throughout the rest of the study, where R² never appears. Had the linking analysis been
built to match the paper's own metric from the start, this entry would not exist.

The choice was also not made after seeing which answer it gave: it was forced by noticing that
`alarm_state` had MAE 0.036 against a 0.600 baseline while scoring R² −2.05, which is a defect
visible without knowing what the corrected aggregate would be.

**Caveat that must travel with the claim.** MAE-skill and R² answer different questions and neither
is wrong in itself. R² is the right statistic for a family with genuine internal spread, and it is
retained. The error is having let a single statistic whose denominator degenerates on a third of
the folds carry the paper's conclusion.

---

## OI-10 — Related-work claims verified where the source was obtainable `IMPORTANT`

> **Downgraded from BLOCKING.** Every substantive claim about prior work now comes from a paper
> that was read in full.

**Read and verified** — each claim in the related-work section is traceable to text in these:

| work | source read | claim checked |
|---|---|---|
| M100 ExaData | Nature OA | 49.9 TB; anomaly set aggregates **IPMI only** to 15-minute windows; thermal set reduces 20 s → 10 min and states this "will preserve room- and node-level thermal transient but discard computing-component-level ones" |
| catch22 | arXiv:1901.10200 | 4791 → 22 features, ~1000× computation reduction, 7% mean accuracy loss over 93 datasets |
| Are Transformers Effective? | arXiv:2205.13504 | one-layer linear models beat Transformer forecasters "in all cases, and often by a large margin" over nine datasets |
| Anomaly Detection using Autoencoders | arXiv:1811.05269 | 88–96% detection accuracy on unseen anomalies |

**Caveat on the fourth.** Only the arXiv preprint was retrievable; the AAAI version of record was
not. The two may differ, and the bibliography says so.

**Not read, and cited only for definitions:** Hyndman & Koehler (MASE), Bandt & Pompe (permutation
entropy), Peng et al. (DFA), Assimakopoulos & Nikolopoulos (Theta), Rostaghi & Azami (dispersion
entropy). All five are paywalled. Each is implemented here and tested against series whose answers
are known by construction, and the manuscript attributes no *finding* to any of them. Paywalls were
not circumvented.

**To close fully.** Obtain the five paywalled originals through institutional access and confirm
the definitions as implemented, and replace the preprint with the AAAI version of record.

No literature has been harvested yet. Every claim about prior work must be checked against the
actual paper before it enters the manuscript; none has been. This item stays open until the
reference audit has run over the final bibliography.
