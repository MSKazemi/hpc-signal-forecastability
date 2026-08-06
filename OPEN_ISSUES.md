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



**Why it matters.** The central claim is that predictability differs by *signal physics*. Ganglia
is the plugin with the most diverse physics (CPU, memory, network, GPU/DCGM), and it is also the
one whose own documentation warns: *"the sampling period of the metrics has high variability,
patterns are different across nodes. The reported values are an approximation."* If Ganglia scores
as unpredictable, we cannot yet distinguish "this signal is intrinsically hard" from "this signal
was sampled badly".

**A trap found while measuring this.** The first attempt used the coefficient of variation of the
inter-sample interval, `dt_cv`, computed over every interval. That measure reported **IPMI** as
the least regular plugin — the opposite of what the documentation says. The cause is that one
multi-day outage in a month of 20-second samples dominates the statistic: `dt_cv` is an outage
detector wearing a jitter label. Had it gone unnoticed, the paper would have contradicted the
dataset's own documentation on the strength of an artefact.

The census now records three distinct quantities, because they are three distinct problems for a
forecaster: `dt_jitter`, the interquartile spread of the interval relative to its median, which is
insensitive to a handful of long gaps; `gap_frac`, the share of intervals exceeding ten times the
median; and `coverage`, the share of expected samples present. A signal can be finely jittered,
coarsely interrupted, or both.

**To settle.** Include all three as *first-class covariates* in the linking regression, then test
whether Ganglia's family effect survives conditioning on them. Additionally, resample a matched
IPMI signal onto Ganglia's observed Δt pattern and measure how much predictability is destroyed —
this gives a direct, quantitative instrumentation penalty.

**Fallback.** Report Ganglia results conditioned on sampling regularity, and state the
instrumentation penalty as a separate measured quantity rather than folding it into "signal
physics".

---

## OI-2 — The monitoring infrastructure is itself non-stationary `BLOCKING`

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

## OI-4 — Aggregated and native-cadence arms measure different objects `IMPORTANT`

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

## OI-7 — The irreducible-error floor is an estimate, not a bound `IMPORTANT`

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

## OI-10 — Related-work claims are not yet verified against source PDFs `OPEN`

No literature has been harvested yet. Every claim about prior work must be checked against the
actual paper before it enters the manuscript; none has been. This item stays open until the
reference audit has run over the final bibliography.
