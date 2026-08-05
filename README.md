# Why Are HPC Monitoring Signals Hard to Forecast?

A predictability study of the monitoring telemetry of CINECA's **Marconi100** (M100) Tier-0
supercomputer, using the public
[M100 ExaData](https://doi.org/10.1038/s41597-023-02174-3) release.

> **Status: study in progress — no results yet.** The scaffold, method, and pre-registered
> analysis plan are in place; the empirical phases are being executed. Nothing in this repository
> should be cited as a finding until this notice is removed.
>
> Read [`OPEN_ISSUES.md`](OPEN_ISSUES.md) before relying on anything here.

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
                  │ naive → ARIMA/ETS/Theta →   │
                  │ LightGBM → TCN/N-BEATS/     │
                  │ PatchTST                    │
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
data/derived/  small committed artefacts: manifest, taxonomy, features, skill
results/       committed tables and figures
paper/         paper.tex (arXiv format), refs.bib, figures
literature/    committed screening table and bibliography
tests/         known-answer tests for the measures; leakage tests for the harness
```

`data/raw/` and `data/interim/` are gitignored, as is `private/`.

## Reproducing

The committed artefacts in `data/derived/` are sufficient to reproduce every table and figure
**without downloading any raw data**:

```bash
uv sync
make reproduce
```

To regenerate those artefacts from scratch you need the M100 ExaData monthly archives from
Zenodo (one tar per month; see the DOIs in the
[ExaData repository](https://gitlab.com/ecs-lab/exadata)). Then:

```bash
make reproduce-from-raw RAW_DIR=/path/to/exadata/raw
```

Extraction is **selective and disk-guarded**: only the required `plugin=/metric=` partitions are
pulled from each tar, one month at a time, and the pipeline aborts rather than filling the disk.

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
