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

**To settle.** Run one genuine sequence model, and ideally one zero-shot pretrained forecaster as
an upper reference point that costs no training. If skill saturates well before the largest model
tried, capacity is not the binding constraint and the argument survives.

**Fallback.** State the claim strictly as "skill saturates across the capacity ladder tested,
which spans four architecture families and roughly two orders of magnitude of parameter count".

---

## OI-7 — The irreducible-error floor was never computed `OPEN`

> **Not attempted.** The planned error-floor decomposition — a k-nearest-neighbour analog bound
> plus the quantisation step — was not implemented, so the paper makes no claim about how much of
> the observed error is irreducible. Nothing in the results depends on it. Recorded here so the
> gap is visible rather than inferred from its absence.

---

## OI-7b — Original wording: the floor is an estimate, not a bound `DEFERRED`

**Why it matters.** The error-floor argument uses a quantisation step plus a k-nearest-neighbour
analog predictor as a proxy for the achievable minimum. Neither is a true information-theoretic
lower bound: a k-NN analog estimate is itself a model and can be beaten, and quantisation bounds
only the resolution component of error.

**To settle.** Present it explicitly as a *lower-bound estimator with known bias direction*,
validate it on synthetic series whose true noise floor is known by construction, and report the
estimator's error on those. Never call it "the" irreducible error in the paper.

---

## OI-8 — The job table is not a time series `OPEN`

**Why it matters.** `job_table` records per-job submission metadata, event-driven, one row per
job. Including it as a "signal family" requires converting it into a regularly sampled series
(e.g. arrival rate, requested-node count per bin). That conversion imposes structure — the bin
width alone determines how bursty the result looks.

**To settle.** Either exclude it from the per-signal predictability comparison and use it only as
an *exogenous covariate* (its intended role in the exogeneity measure), or include it with the
bin width swept and the sensitivity reported. Current plan: use it as a covariate only.

---

## OI-9 — Node-level results are not independent samples `OPEN`

**Why it matters.** With 980 nodes each contributing the same metric, per-series statistics are
strongly correlated — nodes share racks, inlet air, cooling zones, and workload. Treating 980
node-series as 980 independent observations would inflate every significance test.

**To settle.** Cluster-robust standard errors (cluster by rack and by metric), and report the
effective sample size. The family-grouped cross-validation in the linking analysis already guards
the headline R², but per-measure significance claims need this too.

---

## OI-11 — Permutation entropy is biased downward by quantisation `IMPORTANT`

**Why it matters.** Permutation entropy ranks the samples inside each embedding
window. When samples are *tied* — and they constantly are, because IPMI temperatures are integers,
Schneider registers are fixed-point, and roughly a third of Vertiv/Schneider series are outright
constant — the ranking convention (stable argsort, ties resolved by index order) invents an
ordering that is not in the data. The result scores as *more ordered* than it is.

The consequence is directly adversarial to the study's thesis: a coarsely quantised sensor would
look intrinsically predictable when what we actually measured is its resolution. Since
quantisation varies systematically by plugin, this could manufacture the very between-family
difference the paper claims to find.

**Evidence it is real — now measured, not predicted.** Across the 1,419 sampled series, Spearman
correlation between permutation entropy and the log number of distinct values is **+0.534**. A
signal's entropy score is substantially a function of its resolution. By `value_kind`:

| value_kind | n | median entropy | median distinct values |
|---|---:|---:|---:|
| categorical | 196 | 0.001 | 2 |
| quantised | 445 | 0.202 | 45 |
| continuous | 698 | 0.604 | 270 |

`tests/test_measures.py::test_permutation_entropy_reports_tie_dominated_series_as_ordered` shows
the mechanism on a synthetic 8-level staircase, which scores below 0.2 — the same range as a
clean sine.

**How much independent information entropy carries.** Plotting entropy against the fraction of
steps that simply repeat the previous value shows the two are largely redundant: Pearson
*r* = −0.84, and a degree-5 polynomial in repetition fraction explains **77.6%** of entropy
variance. Roughly a fifth of the variance is genuinely something else, and it is concentrated
among signals that rarely repeat (standard deviation 0.345 in the lowest repetition decile against
0.048 in the highest). Entropy is therefore not redundant, but on this data it is mostly a
restatement of how often a signal holds still — which is a far cheaper measure with no tie bias.

**A second, larger problem the same data exposed.** Entropy is not a measure of forecastability at
all, in either direction. Monotone counters score entropy 0.000 while having ~17,850 distinct
values and no quantisation whatsoever: a monotone series has exactly one ordering pattern, so it
is maximally "ordered" — and it is also genuinely easy to forecast, by drift. Alarm states also
score 0.000, for the opposite structural reason: they are step functions that almost never change,
and persistence forecasts them nearly perfectly. Two signal classes with nothing in common land on
the same entropy value.

The consequence is not that the measure is broken but that no single measure can carry this study.
The paper must report a predictability *profile* — entropy alongside flat-run fraction, DFA
exponent, distinct-value count, and quantisation step — and must never rank families by entropy
alone. That is now an argument for the multi-measure design rather than an incidental caveat.

**To settle.** (a) Always carry `quantisation_step` and `n_unique` from the census alongside the
entropy in the linking regression, so the model can separate resolution from predictability.
(b) Report the correlation between quantisation step and permutation entropy across families; if
it is strong, the entropy term cannot be interpreted on its own. (c) As a robustness check,
recompute entropies on rank-transformed series with ties broken at random rather than by index,
and confirm the family ordering survives.

**Fallback.** Report permutation entropy only *conditioned on* quantisation, never as a raw
between-family comparison.

---

## OI-12 — Skill is measured on a subset of the series predictability is measured on `IMPORTANT`

**Why it matters.** The linking analysis regresses forecast skill on predictability measures.
Predictability is computed for all 1,419 sampled series, but skill for only **437** of them, so the
regression's sample size is set by a compute budget rather than by the science.

**Why it is bounded that way.** Profiling the full suite gave 7.9 s per series for four rolling
origins across twelve models and four horizons, dominated by the two largest models. Over 1,419
series with six origins that is roughly 50 hours on this machine, which the study cannot afford —
an earlier attempt was producing two partitions per 44 minutes and would have taken about 300
hours. Cost was cut in three independent places rather than one, so no single choice carries the
whole reduction: origins 6→4, training window 4,000→1,500 most-recent points, and a cap of 12
series per stratum.

**Why the subset is defensible.** Membership is a blake2b hash of the series identity, so it is
reproducible, independent of anything the data does, and specifically not "the first N" or "the
ones that finished quickly" — either of which would correlate with series length and therefore
with cadence and family. Every stratum is still represented.

**What it costs.** Roughly 26 series per signal family for the leave-one-family-out
cross-validation. That is enough to fit, but confidence intervals on the held-out R² will be wide,
and the study must report them rather than a point estimate.

**To settle.** Re-run the sweep at a higher cap on a machine with more cores, or restrict the
expensive tiers to the subset while running the cheap tiers on all 1,419 series — the latter costs
almost nothing and would let the linking analysis use the full sample for every model except the
two largest.

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
