# Why Are HPC Monitoring Signals Hard to Forecast?

A predictability study of the monitoring telemetry of CINECA's **Marconi100** (M100) Tier-0
supercomputer, using the public
[M100 ExaData](https://doi.org/10.1038/s41597-023-02174-3) release.

> **Status: the central hypothesis holds ordinally, and fails on level.**
>
> The study set out to show that forecast difficulty is predictable from model-free properties of a
> signal. Measured against a baseline a model could actually have, it transfers: **13 of 15 signal
> families beat the family-blind predictor, by a median 19% reduction in error.** What does not
> transfer is the *level* — the measures rank series inside a family they have never seen
> (Spearman ρ = 0.50, positive in 14 of 15 families) but cannot say where that family sits.
>
> Earlier drafts of this README reported no transfer at all. That was a defect in the statistic,
> not a finding: R²'s comparator is an oracle that already knows the held-out family's mean skill
> (OI-15). See [What the study found](#what-the-study-found).
>
> Read [`OPEN_ISSUES.md`](OPEN_ISSUES.md) before relying on anything. Fifteen threats to validity
> are registered there, most written before the results existed.
>
> All series are analysed on a common **15-minute grid**. At native cadence the gaps fragment every
> family beyond use — a Ganglia month has 43,199 slots but a longest gap-free run of 149 — so this
> study characterises the aggregated representation, not the raw 20-second stream (OI-4).

## What the study found

**1. Predictability measures do transfer across signal families — ordinally, not cardinally.**
Holding out each of 15 families in turn (1,082 series), against the best predictor that has never
seen the held-out family (predict the training mean):

| | |
|---|---:|
| families beating the family-blind baseline | **13 of 15** |
| median reduction in prediction error | **19%** |
| within-family rank correlation (Spearman ρ), median | **+0.50** |
| families with ρ > 0 | **14 of 15** |
| the one genuine failure | `error_counter`, 85% *worse* than baseline |

The measures reliably say *which* series inside an unseen family are the hard ones — ρ = +0.82 for
memory, +0.83 for scheduler, +0.74 for CPU utilisation. What they cannot do is say where a new
family sits: mean R² given the family's true level is −0.01, against −0.19 without it, so nearly
the whole R² deficit is the unknown offset.

**Why earlier drafts reported the opposite.** They used R², whose denominator is the variance of
the held-out family about *its own* mean — so its implicit comparator is an oracle that already
knows the answer a model is trying to predict. On a family whose series all have similar skill the
denominator collapses. `alarm_state` is the clearest case: the model predicts every held-out
series to within **MAE 0.036** against a baseline error of **0.600** — a 94% improvement — and R²
records **−2.05**. The honest baseline was in the output all along, as `r2_baseline`, averaging
**−18.35** against the model's −0.19. Registered as OI-15.

**The protocol was then validated against known ground truth** (OI-13). Four synthetic arms run
through the identical pipeline:

| arm | mean R² | MAE-skill | within-family ρ |
|---|---:|---:|---:|
| a genuine portable law | +0.248 | +0.201 | +0.584 |
| same, with the true generating parameter supplied | +0.233 | +0.195 | +0.576 |
| same law, non-overlapping per-family bands | −0.096 | +0.165 | −0.050 |
| skill permuted — no relation at all | −0.070 | **+0.002** | +0.100 |
| **M100 (real)** | **−0.189** | **+0.192** | **+0.495** |

The measures recover **103% of the oracle ceiling**, and the no-relation arm correctly scores zero,
so the pipeline can find a law when one exists. On the two statistics that survive a degenerate
denominator M100 resembles the *genuine law* arm; only raw R² resembles the failures. Note that the
no-relation arm scores −0.070 while M100 scores −0.189: on the headline statistic alone the real
data transfers worse than data containing no relation, which is as sharp a demonstration as the
question admits that R² is the wrong summary here.

**One family genuinely fails.** Monotone counters are forecast almost exactly by a drift model, and
`error_counter` is 85% worse than baseline with ρ = −0.02. Adding direction measures
(`monotone_fraction` = 1.00 for that family, 68% classified as unit-root) makes it *detectable*
without making it *predictable* — it is the one place the relation does not hold.

**And the mechanism for the level failure is open.** The obvious explanation — that held-out
families occupy feature regions no training family covers — was tested and refuted twice: across
the real folds Spearman(extrapolation distance, R²) is only −0.111, and in the synthetic control,
genuine band-disjointness collapses within-family ordering to ρ = −0.05 where M100 holds at +0.50.

**2. Individual measures do correlate with skill — but the strongest one is nearly tautological.**
Cluster-robust over 156 metric clusters:

| measure | r | 95% CI |
|---|---:|---|
| fraction of steps that repeat | **+0.40** | [0.25, 0.53] |
| permutation entropy | −0.35 | [−0.49, −0.18] |
| daily seasonal strength | −0.24 | [−0.43, −0.02] |
| excess kurtosis of differences | +0.23 | [0.12, 0.31] |

The best predictor of "is this forecastable" is "does it hold still" — which is closer to a
restatement than an explanation.

**3. More model capacity makes things worse, and skill goes negative fast.** Median skill
(1 − MASE) against a **same-step** naive baseline, 331 series:

| tier | h=1 (15 min) | h=4 (1 h) | h=12 (3 h) | h=96 (24 h) |
|---|---:|---:|---:|---:|
| naive | **0.461** | **0.115** | **−0.494** | **−3.550** |
| statistical | 0.230 | −0.064 | −0.546 | −3.921 |
| boosted trees | 0.022 | −0.613 | −1.492 | −4.308 |
| neural (MLP) | 0.227 | −0.327 | −1.257 | −5.746 |

The naive tier is best at every horizon and the single best model throughout is `persistence`.
Comparing each tier's *best* model per series — fairer, since pooling penalises a tier for holding
a weak member — a paired Wilcoxon rejects equality of naive against every other tier at every
horizon by a wide margin (p < 10⁻²⁰ at one hour; p < 10⁻⁹⁰ against the neural tier). At 24 hours
even the best naive model is negative (−0.284).

**Two caveats, both load-bearing:**
- The ML and neural models forecast **recursively**, so error compounds. This was tested, not
  assumed: `scripts/11_direct_control.py` fits the same learner directly per horizon. Recursion
  costs a lot (at 1 h, −0.223 → **+0.114**), but the direct model still loses to persistence at
  every horizon, so the conclusion does not rest on it. See `results/tables/direct_vs_recursive.csv`.
- The ordering is specific to this baseline. Against the daily-seasonal denominator the same data
  puts *statistical* on top (0.892 / 0.838 / 0.755 / 0.303) and boosted trees above naive at h=1.
  Which baseline you scale by changes which family of models looks best — which is itself a
  finding about how this literature reports results.

**4. This is not an instrumentation artefact.** Dropping the sampling and quantisation covariates
*improves* the linking model slightly (−0.14 vs −0.16), and using them alone collapses it (−15.0).
Whatever the measures capture, it is not how the data was sampled — which is the conditioning test
OI-1 called for.

Every number above is in [`results/tables/`](results/tables).

## Descriptive findings

**The monitoring system is itself non-stationary.** Across the 31-month campaign there are 573
distinct (plugin, metric) pairs, and only **104 are present in every month** — all of them IPMI.
Ganglia's metric count runs 0 → 33 → 73 → 49 → 157 → 177 and is not even monotonic; SLURM's runs
20 → 2 → 0 → 2 → 36; Schneider appears in 21-03 and Vertiv and Weather in 21-04. Any comparison
across months confounds signal behaviour with changes to the instrument.

**A large share of what is monitored never changes.** Fraction of series constant over a month:

| Nagios | Schneider | Logics | Ganglia | Vertiv | SLURM | IPMI | Weather |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 64.8% | 47.0% | 42.9% | 42.9% | 33.1% | 10.5% | 8.4% | 0.0% |

A benchmark that averages over such series reports the share of constants in its sample as much as
the skill of its models.

Both are reproduced in `results/tables/coverage.csv` and `results/tables/constant_share.csv`,
which are committed.

## The question

Forecasting a supercomputer's monitoring signals — node temperatures, power draw, fan speeds,
GPU utilisation, scheduler queue depth, facility cooling — is markedly harder than the
time-series literature would lead you to expect. Models that perform well on standard benchmarks
degrade sharply on this data.

The usual response is to reach for a bigger model. **This study set out to test the opposite
position:**

> The difficulty is largely *intrinsic to the signals themselves*. It differs systematically
> between signal families, and it can be measured **without fitting any forecaster at all**.

**Both halves survive, with one qualification that took a validated control to establish.**
Difficulty is not a modelling deficiency — bigger models do worse here, not better, significantly
so at every horizon. And it *can* be measured without fitting a forecaster: the measures transfer
to families they have never seen, beating a family-blind baseline in 13 of 15 and ranking series
inside an unseen family at ρ = 0.50.

The qualification is that what transfers is the **ordering**, not the **level**. The measures say
which signals in a new family are the hard ones; they do not say how hard that family is overall.
Why the level fails to transfer is not yet explained — the obvious answer, extrapolation to unseen
feature regions, has been tested and refuted.

## Method in one diagram

```
                  ┌─────────────────────────────┐
   each series ──▶│ model-free predictability   │──▶ predicted difficulty
                  │ entropy · periodicity ·     │            │
                  │ long memory · stationarity ·│            │
                  │ quantisation · missingness ·│            │ compare
                  │ exogeneity                  │            │
                  └─────────────────────────────┘            │
                  ┌─────────────────────────────┐            ▼
   each series ──▶│ tiered forecast suite       │──▶ observed skill (MASE)
                  │ naive → Theta/Holt/ridge-AR │
                  │ → boosted trees ×3 capacity │
                  │ → lag-window MLP ×2 capacity│
                  └─────────────────────────────┘

  Central claim:  observed skill ≈ f(intrinsic predictability measures)
                  tested with cross-validation grouped by signal family,
                  so the relation must generalise to families it never saw.

  Validated by:   the same pipeline run on synthetic data with a KNOWN law,
                  which it recovers at 103% of an oracle's ceiling, and on
                  synthetic data with NO law, where it correctly finds none.
```

The relation was tested by holding out whole families, so it had to generalise to unseen signal
physics to count. It does: 13 of 15 families beat a family-blind baseline, by a median 19% error
reduction, with within-family ordering transferring at ρ = +0.50. Because that conclusion rests on
choosing the right statistic, the protocol itself was put through a positive and a negative control
before the conclusion was drawn (OI-13) — the study's earlier null result came from R², whose
comparator is an oracle no model can have (OI-15).

## Why M100 ExaData is the right substrate

ExaData is unusually well suited to this question because it collects **nine heterogeneous
plugin families** from the same machine over the same 31 months, so signal type varies while the
system, workload, and period are held fixed:

| Plugin | What it measures | Nominal cadence | Character |
|---|---|---|---|
| IPMI | BMC sensors: core/DIMM/GPU temps, socket & PSU power, fans | 20 s | quantised integers, thermally inertial |
| Ganglia | OS & GPU counters: CPU, memory, network, NVIDIA DCGM | 20 s – 5 min, **irregular** | mixed; documented variable sampling |
| SLURM | cluster-wide scheduler aggregates, per-partition/QoS | 5–10 s | queue dynamics, bursty |
| Nagios | service/hardware alarm states | 15 min | discrete, categorical |
| Job table | per-job submission records | event-driven | not a time series at all |
| Schneider | electrical distribution measurements | — | facility-side |
| Logics | room power, PUE, chillers, CRACs, pumps | — | facility-side, control-loop coupled |
| Vertiv | air-conditioning units: temps, humidity, fan, valves | 10 s | closed-loop controlled |
| Weather | outdoor conditions at Casalecchio di Reno | 10 min | exogenous driver |

A signal produced by a *control loop* (Vertiv), by *thermal diffusion* (IPMI), by *user
behaviour* (SLURM queues), and by *the weather* have fundamentally different predictability —
and this study measures how different.

## Repository layout

```
src/hsf/
  io/          selective tar→parquet extraction, series loading, disk guards
  features/    model-free predictability measures
  forecast/    tiered model suite + leakage-free rolling-origin harness
  link/        skill ~ features analysis, family separability, error floor
  lit/         reproducible literature harvest (OpenAlex / arXiv / S2)
scripts/       one entry point per pipeline stage
conf/          YAML experiment configs — seeds, horizons, model grid
data/derived/  taxonomy.csv and sample.csv are committed; parquet is regenerable
results/       committed tables and figures
paper/         paper.tex (arXiv format), refs.bib, figures
literature/    committed screening table and bibliography
tests/         known-answer tests for the measures; leakage tests for the harness
```

`data/raw/` and `data/interim/` are gitignored, as is `private/`.

## Reproducing

**What is committed.** Derived `.parquet` is deliberately not tracked — it is bulky and fully
regenerable from `scripts/`. What *is* committed is small and human-readable:

| path | what it is |
|---|---|
| `results/tables/*.csv` | the numbers behind every figure, one CSV per figure |
| `data/derived/taxonomy.csv` | the a-priori label for every (plugin, metric) pair, with the rule that produced it |
| `data/derived/sample.csv` | exactly which series were analysed |
| `literature/screening.csv` | every candidate paper the search returned, with provenance |

So a reader without the archives cannot re-run the pipeline, but **can check every number the
paper prints** against the table that produced the corresponding figure. That is what claim
traceability is actually for.

**Full regeneration** needs the M100 ExaData monthly archives from Zenodo (one tar per month; see
the DOIs in the [ExaData repository](https://gitlab.com/ecs-lab/exadata)):

```bash
uv sync
make reproduce-from-raw RAW_DIR=/path/to/exadata/raw
```

Extraction is selective and disk-guarded: only the required `plugin=/metric=` partitions are
pulled from each tar, one month at a time, and the pipeline aborts rather than filling the disk.
Concurrency is derived from a memory budget rather than the core count, because the reference
machine is shared.

**Once derived data exists locally**, `make reproduce` rebuilds all tables and figures from it
without touching the archives again.


## Data source

Borghesi, A., Di Santi, C., Molan, M., Seyedkazemi Ardebili, M., Mauri, A., Guarrasi, M.,
Galetti, D., Cestari, M., Barchi, F., Benini, L., Beneventi, F., Bartolini, A.
"M100 ExaData: a data collection campaign on the CINECA's Marconi100 Tier-0 supercomputer."
*Scientific Data* **10**, 288 (2023). https://doi.org/10.1038/s41597-023-02174-3

## Licence

Code is MIT (see [`LICENSE`](LICENSE)). The paper text, figures, and derived data tables are
CC BY 4.0 (see [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)).

## Author

Mohsen Seyedkazemi Ardebili — <mohsen.seyedkazemi@gmail.com>
