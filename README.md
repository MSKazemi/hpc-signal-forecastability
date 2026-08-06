# Why Are HPC Monitoring Signals Hard to Forecast?

A predictability study of the monitoring telemetry of CINECA's **Marconi100** (M100) Tier-0
supercomputer, using the public
[M100 ExaData](https://doi.org/10.1038/s41597-023-02174-3) release.

> **Status: the central hypothesis was tested and is NOT supported.**
>
> The study set out to show that forecast difficulty is predictable from model-free properties of
> a signal. It is not — at least not across signal families. The suite was built so that this
> outcome was reachable, and it was reached; see [What the study found](#what-the-study-found).
>
> Read [`OPEN_ISSUES.md`](OPEN_ISSUES.md) before relying on anything. Twelve threats to validity
> are registered there, most written before the results existed; no cited work has yet been
> checked against its source paper.
>
> All series are analysed on a common **15-minute grid**. At native cadence the gaps fragment every
> family beyond use — a Ganglia month has 43,199 slots but a longest gap-free run of 149 — so this
> study characterises the aggregated representation, not the raw 20-second stream (OI-4).

## What the study found

**1. Predictability measures do not transfer across signal families.** Holding out an entire
family and predicting its forecast skill from the other families' measures gives a mean
out-of-sample R² of **−0.82** (random forest; ridge −2.36). It beats predicting the global mean
(−6.00), but a negative R² means it is worse than knowing only the held-out family's own average.
There is no universal difficulty law here that generalises to signal physics it has not seen.

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
| naive | **0.477** | **0.127** | **−0.513** | **−3.241** |
| statistical | 0.259 | −0.030 | −0.556 | −3.561 |
| boosted trees | 0.078 | −0.500 | −1.422 | −4.022 |
| neural (MLP) | 0.251 | −0.259 | −1.122 | −5.204 |

The naive tier is best at every horizon, and the single best model throughout is `persistence` —
repeat the last value (0.778, 0.508, 0.155, −2.523). Beyond three hours *every* tier is worse than
a same-step naive forecast.

**Two caveats, both load-bearing:**
- The ML and neural models forecast **recursively**, so error compounds over multi-step horizons.
  Part of this gap is that modelling choice, not the signals; a direct multi-horizon model would
  likely close some of it.
- The ordering is specific to this baseline. Against the daily-seasonal denominator the same data
  puts *statistical* on top (0.892 / 0.838 / 0.755 / 0.303) and boosted trees above naive at h=1.
  Which baseline you scale by changes which family of models looks best — which is itself a
  finding about how this literature reports results.

**4. This is not an instrumentation artefact.** Dropping the sampling and quantisation covariates
*improves* the linking model slightly (−0.79 vs −0.82), and using them alone collapses it (−8.03).
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

The first half survives and the second does not. Difficulty is not a modelling deficiency —
bigger models do worse here, not better. But it is also not a portable property: measures that
correlate with skill inside one family do not predict skill in a family they have never seen.

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
```

The relation was tested by holding out whole families, so it had to generalise to unseen signal
physics to count. It did not (mean out-of-sample R² = -0.82). "HPC signals are hard to forecast"
remains, for now, a statement about particular signals rather than a measurable law.

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
