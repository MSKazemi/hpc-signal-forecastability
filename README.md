# Why Are HPC Monitoring Signals Hard to Forecast?

A predictability study of the monitoring telemetry of CINECA's **Marconi100** (M100) Tier-0
supercomputer, using the public
[M100 ExaData](https://doi.org/10.1038/s41597-023-02174-3) release.

> **Status: descriptive results only. The central claim is not yet tested.**
>
> The two findings below are computed and reproducible. The question in the title is **not yet
> answered**: the forecast benchmark and the linking analysis that would answer it have not
> finished, so nothing here says whether predictability measures actually explain forecast skill.
>
> Read [`OPEN_ISSUES.md`](OPEN_ISSUES.md) before relying on anything. Twelve threats to validity
> are registered there, most written before the results existed; one is still marked blocking, and
> no cited work has yet been checked against its source paper.
>
> All series are analysed on a common **15-minute grid**. At native cadence the gaps fragment every
> family beyond use — a Ganglia month has 43,199 slots but a longest gap-free run of 149 — so this
> study characterises the aggregated representation, not the raw 20-second stream (OI-4).

## What is established so far

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

The usual response is to reach for a bigger model. **This study takes the opposite position:**

> The difficulty is largely *intrinsic to the signals themselves*. It differs systematically
> between signal families, and it can be measured **without fitting any forecaster at all**.

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

If that relation holds, "HPC signals are hard to forecast" stops being folklore and becomes a
measurable property with named causes.

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
