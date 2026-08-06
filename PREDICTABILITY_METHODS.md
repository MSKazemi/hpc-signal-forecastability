# Why are HPC monitoring signals hard to forecast — and what can tell you *before* you fit a model?

A methods survey for this study: the statistical, information-theoretic and dynamical tools that
answer "is this series predictable at all", organised into ten families, each with the mathematics,
a Python route, what it would settle for M100, and what it costs.

This complements `NEXT_EXPERIMENTS.md` (which is about *experimental design*). This document is
about *measurement instruments*.

> **Citation status.** Every reference here is marked `[verified]` (checked this session against the
> source or its abstract), `[cited-standard]` (canonical, definition-only, not yet read), or
> `[to-audit]`. Nothing enters `paper/refs.bib` until it passes the repo's reference-audit
> convention (OI-10).

---

## 0. Audit: what this study currently measures, declares, and lacks

`src/hsf/features/measures.py` implements **13** measures. `scripts/06_features.py` assembles them
into 19 columns with metadata. That is the whole instrument.

| implemented (13) | what it is |
|---|---|
| `permutation_entropy`, `spectral_entropy`, `lempel_ziv` | complexity |
| `dominant_period_strength`, `seasonal_strength`, `autocorrelation` | periodicity |
| `dfa_alpha` | long memory |
| `drift_ratio`, `variance_ratio` | non-stationarity proxies |
| `jump_fraction`, `excess_kurtosis` | tails |
| `flat_run_fraction`, `longest_flat_run` | stasis |

**Declared in the pre-registered config but never implemented.** `conf/experiment.yaml` lists
under `features:` a `sample_entropy` block (`m: 2, r_times_sd: 0.2`), a `changepoints` block
(`model: rbf, penalty: bic`), and an `stl` block (`robust: true`). None of the three appears in
`measures.py` or `06_features.py`. Since that file's header states its choices were made before
results existed precisely so they could not be tuned, the gap should be closed by either
implementing them or striking them with a note — leaving a pre-registration that overstates what
ran is the kind of thing a referee checks.

**Structurally absent from the instrument.** No entropy-rate estimator, no predictability *bound*
of any kind, no stationarity or unit-root test, no changepoint detection, no discrete/Markov
machinery, no multivariate or causal measure, no volatility measure, no tail-index estimate, and
no measure that survives irregular sampling. Ten families follow, roughly in order of what they
would buy this study.

---

## 1. Mechanism map — the candidate answers to "why are they hard"

The study currently has one composite answer ("intrinsic difficulty"). These are the separable
mechanisms, each with a diagnostic that can confirm or eliminate it. This table is the argument
structure the paper is missing.

| # | Mechanism | Signature in the data | Diagnostic | Family |
|---|---|---|---|---|
| M1 | **Sensor quantisation** — the signal is finer than its representation | few distinct values, constant ties | Π_max with alphabet = sensor resolution; `n_unique` | 2, 8 |
| M2 | **Genuine stochasticity** — the process really is noisy | high entropy rate, λ₁ > 0 | Fano bound, entropy-power floor, Lyapunov | 2, 3, 4 |
| M3 | **Missing covariates** — predictable, but not from its own past | univariate hard, multivariate easy | Granger / transfer entropy / exogenous-model skill gap | 9 |
| M4 | **Exogenous regime switching** — jobs start and stop | breaks at job boundaries | changepoints, Markov-switching, TE from job table | 5, 9 |
| M5 | **Control-loop actuation** — deadbands, hysteresis, bang-bang | square waves, long dwells | RQA laminarity, dwell-time hazard, cepstrum | 4, 7, 8 |
| M6 | **Monotone counters with resets** | DFA α > 1.5, entropy 0, drift wins | unit-root tests, monotone fraction, reset count | 5, 8 |
| M7 | **Rare-event step functions** (alarms) | 0/1, long dwells, class imbalance | hazard analysis, Markov mixing time, Fano with N = 2 | 8 |
| M8 | **1/f aggregation noise** — many jobs superposed | PSD slope β ≈ 1 | Welch/multitaper slope, MFDFA | 6, 7 |
| M9 | **Heavy-tailed failure events** | kurtosis, isolated extremes | Hill estimator, EVT peaks-over-threshold | 10 |
| M10 | **Instrument non-stationarity** | coverage changes across months | already reported (OI-2) | 5 |
| M11 | **Outages and irregular sampling** | gaps, jitter | Lomb–Scargle, gap-aware entropy | 7 |
| M12 | **Volatility without level structure** | bursty variance, flat mean | ARCH-LM, GARCH, Allan factor | 10 |

M2 is the paper's implicit thesis. M1, M3, M5, M6, M7 and M12 are alternative explanations that the
current instrument **cannot distinguish from it**. Most of what follows is about building that
discrimination.

---

## 2. Information-theoretic ceilings — the single largest gap

The one class of tool that literally answers "is this dataset predictable" *before* any model is
fitted, and the study has none of it. It also closes **OI-7**, which records that the irreducible
error floor was never computed.

### The Fano bound on maximum predictability

For a symbolised series with entropy rate `S` and `N` distinct states, the maximum probability
`Π_max` that *any* predictor correctly calls the next symbol solves a limiting case of Fano's
inequality:

```
S  =  −[ Π·log₂Π + (1−Π)·log₂(1−Π) ]  +  (1−Π)·log₂(N−1)
```

Solve numerically for `Π ∈ [1/N, 1]`. This is the Song–Qu–Blumm–Barabási construction
(*Science* 327:1018, 2010) `[verified]`, which found ~93% potential predictability in human
mobility; the formula is restated in many follow-ups `[verified]`.

### Estimating the entropy rate

| estimator | formula / note | when to use |
|---|---|---|
| **Lempel–Ziv (Kontoyiannis et al. 1998)** | `S ≈ (n·log₂n) / Σᵢ Λᵢ`, where `Λᵢ` = length of the shortest substring starting at `i` not appearing in `x₁…x_{i−1}` | default; consistent, needs no alphabet model `[cited-standard]` |
| **Plug-in block entropy** with Miller–Madow / Grassberger / NSB / Chao–Shen bias correction | `Ŝ_k = H(x_{t}|x_{t−1..t−k})` | small alphabets (alarms, N = 2–5) |
| **Context-tree weighting (CTW)** | code length per symbol | best small-alphabet estimator; also gives a *compressor* baseline |
| Shannon of the marginal `S_rand = −Σ pᵢ log₂ pᵢ` | ignores order | reference point |
| Uniform `S_unc = log₂ N` | ignores everything | reference point |

The triple `(S_unc, S_rand, S_real)` is itself informative: `S_rand − S_real` is exactly *how much
temporal structure there is to exploit*, and reporting it per family would be a result in its own
right.

### Applying it here

Symbolisation is *not* an obstacle for this dataset — it is natural. IPMI temperatures are already
integers; Schneider/Vertiv registers are fixed-point; Nagios states are categorical; alarm and
setpoint families are discrete by construction. For genuinely continuous series, bin at the
**sensor's own quantisation step** (already computed as `log_quantisation_step`), or use SAX with a
fixed alphabet and report sensitivity to alphabet size.

**What it settles.** Compute `Π_max` per series, then compare it against *achieved* accuracy from
the existing forecast sweep (discretised to the same alphabet). Three outcomes, all publishable:

- `Π_max` low, achieved ≈ `Π_max` → **the signal is the limit.** The paper's thesis, proven, not asserted.
- `Π_max` high, achieved ≪ `Π_max` → **the models are the limit.** The thesis fails for a nameable reason and the paper becomes about the gap.
- `Π_max` varies by family and achieved tracks it → **a portable law exists after all**, just not in the feature space tried. This is the outcome the current LOFO analysis is structurally unable to detect.

**Caveats to state up front.** `Π_max` is alphabet-dependent (report a sensitivity sweep); it bounds
next-symbol accuracy, not multi-step MASE (state the mapping, or evaluate accuracy at h = 1 only);
and the LZ estimator is biased on short series (n ≥ 2,000 here, which is adequate — but validate on
synthetic sources with known entropy rate, exactly as OI-7 asks).

**Python.** `antropy`, `EntropyHub`, a ~30-line LZ-`Λ` loop, `scipy.optimize.brentq` for the Fano
solve. **Cost:** two to three days including validation. **Highest value item in this document.**

Further reading: *On Predictability of Time Series*, arXiv:1806.03876 `[to-audit]` — a survey of
exactly this construction applied outside mobility.

---

## 3. Continuous-valued noise floors — the analogue for real-valued signals

`Π_max` needs symbols. For continuous series the equivalent is a lower bound on achievable MSE.

- **Entropy-power lower bound.** For any predictor of `X_{t+h}` from the past,
  `MSE ≥ (1 / 2πe) · 2^{2·h(X_{t+h} | X_t^{(m)})}`, where `h(·|·)` is conditional differential
  entropy. Estimate it with **Kozachenko–Leonenko** or **Kraskov–Stögbauer–Grassberger (KSG)**
  nearest-neighbour estimators `[cited-standard]`. This is a genuine bound, not a proxy — which is
  precisely the distinction OI-7b says the study must respect.
- **Gamma test / Delta test** (Stefánsson, Končar & Jones 1997; Evans & Jones 2002) `[to-audit]`.
  Regress `γ(k) = ½·mean|y_{N(k,i)} − y_i|²` against `δ(k) = mean‖x_{N(k,i)} − x_i‖²` over `k`
  nearest neighbours in the embedding; the **intercept Γ estimates the noise variance** directly.
  Fast, well-established in the nonlinear-modelling literature, and gives an irreducible-MSE number
  per series in seconds.
- **k-NN analog residual variance** — the estimator OI-7 originally planned. Keep it, but report it
  as an *upper* bound on the floor (it is itself a model) alongside the two above, which bound from
  below. Bracketing the floor from both sides is far stronger than either alone.
- **Local linear / local projection prediction error** as a function of embedding dimension
  (Kantz & Schreiber). The curve's plateau is the floor; where it plateaus is the useful
  embedding dimension.
- **Cross-validated kernel regression (Nadaraya–Watson) residual** as a nonparametric ceiling on
  achievable skill.

**What it settles.** Convert the floor into the study's own units — `MASE_floor` using the same
denominator — and plot achieved-vs-floor per family. A family where models sit at the floor is
*intrinsically* hard; a family where they sit far above it is *badly modelled*. This is the single
figure that would most directly support or destroy the paper's central claim.

**Python.** `sklearn.neighbors` for the k-NN machinery, `npeet`/`scikit-feature` or a direct KSG
implementation. **Cost:** three to four days.

---

## 4. Nonlinear dynamics and state-space geometry

Gives a *physically interpretable forecast horizon*, which the study currently lacks entirely.

| tool | what it gives | note for this data |
|---|---|---|
| **Average mutual information** (Fraser & Swinney) | embedding delay τ from first minimum | also a **nonlinear ACF** — works where Pearson `acf1` fails on discrete signals |
| **False nearest neighbours** (Kennel et al. 1992) / **Cao's method** | embedding dimension m | m is itself a complexity feature |
| **Correlation dimension D₂** (Grassberger–Procaccia) | attractor dimension | needs long, clean series — use with care at n ≈ 2,000 |
| **Largest Lyapunov exponent λ₁** (Rosenstein 1993; Kantz 1994) | **`t_pred ≈ (1/λ₁)·ln(Δ/δ₀)`** | a horizon in *minutes*, per series, model-free |
| **Recurrence quantification analysis** | RR, **DET**, **LAM**, trapping time, `L_max ∝ 1/λ₁`, diagonal-line entropy | **robust to quantisation**, unlike permutation entropy (OI-11); LAM directly detects control-loop deadbands (M5) |
| **0-1 test for chaos** (Gottwald & Melbourne) | scalar K ∈ [0,1] | cheap, no embedding, good screening statistic |
| **Surrogate data tests** (Theiler et al. 1992; IAAFT, Schreiber & Schmitz) | is the nonlinearity real? | **mandatory here** — quantised, heavy-tailed, gap-filled signals generate spurious nonlinearity statistics; surrogates are the control |

**Why this matters for the argument.** `λ₁` gives a per-series predictability horizon derived from
dynamics rather than from a fitted model. That is a direct, independent instrument for the target
proposed as idea 5 in `NEXT_EXPERIMENTS.md` — and if a model-free `t_pred` correlates with the
empirical crossover horizon, that is a portable law, exactly the thing the paper concluded does not
exist.

**Python.** `nolds` (DFA, Lyapunov, correlation dimension), `pyunicorn` or `PyRQA` (RQA),
`ordpy` (ordinal/permutation with proper tie handling), `nolitsa` (surrogates, FNN, AMI).
**Cost:** four to five days; RQA and Lyapunov are O(n²) in the worst case, so subsample.

---

## 5. Stationarity, unit roots, and structural breaks

The most-cited informal explanation for HPC forecast difficulty, and the study contains **no
hypothesis test of it at all**.

- **Unit-root pair: ADF (null = unit root) with KPSS (null = stationary).** Run both and classify
  into four cells — *stationary*, *unit root*, *both rejected* (→ fractionally integrated or
  break-driven), *neither rejected* (→ underpowered). The four-cell classification is far more
  informative than either test alone and is a natural categorical feature.
- **DF-GLS / Phillips–Perron** for power and heteroscedasticity robustness.
- **Zivot–Andrews** — unit root allowing one endogenous break. Essential here: a job-driven level
  shift makes a stationary series look integrated to plain ADF (M4).
- **Lo–MacKinlay variance-ratio *test***. `variance_ratio_8` is already computed as a raw ratio with
  no standard error; it correlates at r = −0.20 with skill. Its heteroscedasticity-robust test
  statistic costs nothing extra and makes it interpretable.
- **Structural breaks:** Bai–Perron multiple breakpoints, CUSUM / MOSUM, Chow.
- **Changepoints:** PELT, binary segmentation, kernel/RBF cost, and **Bayesian online changepoint
  detection** (Adams & MacKay 2007) `[cited-standard]`. This is the family `conf/experiment.yaml`
  already declares (`model: rbf, penalty: bic`) and that was never implemented — the changepoint
  *rate* per series is an obvious and directly interpretable difficulty feature.
- **Regime models:** Markov-switching AR (Hamilton), HMM with state count by BIC, TICC. The number
  of regimes and the expected dwell time in each are strong candidate features for M4/M5.
- **Time-varying stationarity:** sliding-window ADF; locally stationary wavelet test (Nason).

**What it settles.** Whether a series is trend-stationary or difference-stationary determines
whether *drift* or *persistence* is the right naive model. That is exactly the `error_counter` fold
(R² = −10.93) where drift forecasts near-perfectly and nothing in the feature set anticipates it.
A unit-root test would have flagged it.

**Python.** `statsmodels.tsa.stattools` (adfuller, kpss, zivot_andrews, range_unit_root_test),
`arch.unitroot`, `ruptures` (already implied by the config), `bayesian-changepoint-detection`,
`statsmodels.tsa.regime_switching`. **Cost:** two days. Cheapest high-value item here.

---

## 6. Long memory, scaling, and multifractality

`dfa_alpha` is implemented and is *useless* in the linking model (r = 0.004, importance −0.0005).
That is a suspicious result for a measure that should matter, and it points at the estimator rather
than the concept.

- **DFA order matters.** DFA-1 removes only a linear trend; on a monotone counter or a series with a
  job-driven ramp, α is dominated by the trend and means nothing. Report **DFA-2 and DFA-3**
  alongside, and report the *goodness of the log-log fit* — a bad fit means the scaling law does not
  hold and α should not be used at all. This alone may explain the null result.
- **Alternative Hurst estimators:** R/S, detrended moving average (DMA), wavelet-based Abry–Veitch,
  Higuchi fractal dimension. Disagreement between estimators is itself diagnostic.
- **ARFIMA `d` estimation:** GPH (Geweke–Porter-Hudak) and **local Whittle** — these come with
  standard errors, which DFA does not, so they can support a *test* of long memory rather than a
  point estimate.
- **MFDFA** (Kantelhardt et al. 2002) `[cited-standard]`: generalised Hurst `h(q)`, singularity
  spectrum `f(α)`, and the **multifractal width Δα**. Δα separates a signal with one scaling law
  (thermal diffusion) from one whose bursts and calm periods scale differently (scheduler queues) —
  a distinction the current feature set cannot express.
- **DCCA / ρ_DCCA** for scale-dependent coupling between two non-stationary series (inlet air ↔ core
  temperature), which is more appropriate than Pearson correlation on non-stationary telemetry.

**Python.** `nolds`, `MFDFA`, `fathon` (DFA/DCCA/MFDFA in one package), `arch` for local Whittle.
**Cost:** two to three days.

---

## 7. Spectral, time–frequency, and irregular-sampling methods

Contains the one published, off-the-shelf **forecastability index** the study should be benchmarking
against, and the one method that makes native-cadence analysis possible again.

### ForeCA's Ω — a named forecastability measure

Goerg, *Forecastable Component Analysis*, JMLR W&CP 28(2):64–72, 2013 `[verified]` defines

```
Ω(x) = 1 − H_s(f_x) / log(2π)      ∈ [0, 1]
```

where `H_s` is the entropy of the normalised spectral density: **flat spectrum → Ω = 0 → white noise
→ unforecastable; peaked spectrum → Ω → 1 → forecastable.** This is precisely the tool the goal asks
for, it has a paper and an R implementation behind it, and it is a direct comparator for
`spectral_entropy` (currently r = 0.08, importance 0.0009 — near-useless as implemented, which is
worth investigating given that Ω is essentially a normalised version of it).

ForeCA is also *multivariate*: it finds the linear combination of a multivariate series that is
**most forecastable**. Applied to the 96-entity panel of a single metric, "how forecastable is the
most forecastable combination of nodes?" is a genuinely new question for this dataset.

### Lomb–Scargle — the answer to OI-4

The **Lomb–Scargle periodogram** estimates spectral content from *irregularly sampled* data without
interpolation. OI-4 states the study was forced onto a 15-minute grid because native-cadence gaps
fragment every family, and that this is the study's largest scoping compromise. Lomb–Scargle
sidesteps it for the frequency-domain measures entirely: periodicity, spectral entropy, Ω and the
1/f slope can all be computed **at native cadence, on the raw irregular samples, with no imputation
and no low-pass filtering.** That converts the biggest stated limitation into a partial result.

### The rest of the family

- **Welch / multitaper PSD**, fit `S(f) ∝ f^{−β}`. β is a compact predictability index: β ≈ 0 white
  (nothing to forecast); β ≈ 1 flicker/aggregation noise (M8); β ≈ 2 random walk (persistence is
  optimal — which is exactly what the paper observes).
- **Spectral flatness / Wiener entropy** — geometric over arithmetic mean of the PSD.
- **Wavelet power spectrum and wavelet coherence** (Torrence & Compo) for periodicity that comes and
  goes — the normal case under changing workload.
- **SSA (singular spectrum analysis):** the variance share of the leading k components is a clean
  signal-to-noise proxy, and the decomposition itself separates trend / oscillation / noise without
  assuming a model.
- **EMD / EEMD and Hilbert–Huang** for nonlinear non-stationary decomposition.
- **Cepstrum and harmonic-set detection** for control-loop duty cycles (Vertiv, CRAC units) — a
  square wave has a harmonic signature that a single dominant-period statistic misses entirely.

**Python.** `astropy.timeseries.LombScargle`, `scipy.signal` (welch, periodogram), `spectrum`
(multitaper), `PyWavelets` + `pycwt`, `PyEMD`, `pyts`/`pyactigraphy` for SSA. Ω is ~20 lines from a
PSD. **Cost:** three days, and Lomb–Scargle alone would justify it.

---

## 8. Symbolic, discrete, and event-based methods

Where the study's worst fold lives. OI-11 records that `alarm_state` and `error_counter` both score
permutation entropy 0.000 for *opposite structural reasons* — the instrument cannot tell a monotone
counter from a step function. The reason is that every implemented measure assumes a continuous
signal. Three of the thirteen families (`alarm_state`, `error_counter`, `setpoint_config`) are not.

- **Markov chain order selection** by AIC/BIC/χ² over order k. Then: the estimated transition matrix
  `P`, its stationary distribution, and its **spectral gap** — because the **mixing time
  `≈ 1/(1−|λ₂|)` is a predictability horizon for discrete signals**, the direct analogue of `1/λ₁`.
- **Variable-length Markov chains / context-tree weighting / PPM.** The achieved code length per
  symbol *is* a predictability measure, and CTW is close to optimal for small alphabets.
- **Compression-based complexity:** gzip / bzip2 / xz compression ratio; **normalised compression
  distance** (Cilibrasi & Vitányi) `[cited-standard]`. Crude, extremely cheap, alphabet-agnostic, and
  robust to the quantisation bias that OI-11 shows contaminates permutation entropy. A good
  sanity check against `lempel_ziv`.
- **Run-length and dwell-time analysis:** survival curves and hazard functions for state
  persistence; fit exponential vs Weibull. A memoryless alarm (constant hazard) is unpredictable
  beyond its base rate; an ageing one is not. This is the right instrument for M7, and
  `longest_flat_run` is its crudest possible summary.
- **Point processes for event-driven data (OI-8):** the job table is not a time series and should not
  be forced into one. Fit a **Hawkes process** and report the **branching ratio η** — η → 1 means
  self-exciting bursts, which are predictable in *intensity* but not in *timing*, a distinction that
  matters operationally. Test Poisson-ness with the **Fano factor** of counts and the **Allan
  factor** across bin scales.
- **Symbolic dynamics:** SAX, symbolic transfer entropy, and ordinal patterns **with an explicit
  tie-handling rule** — OI-11's fallback (a) asks for exactly this, and randomised tie-breaking is a
  three-line fix to `permutation_entropy`.
- **Mutual information at lag k** as a nonlinear, categorical-safe ACF. `acf1` is meaningless for
  alarm states; `I(X_t; X_{t−k})` is not.
- **For counters specifically:** difference first, detect resets explicitly, and test for a unit
  root — see family 5.

**Python.** `hmmlearn`, `pomegranate`, `statsmodels` (Markov), `zlib`/`bz2`/`lzma` for compression
ratios, `lifelines` for hazards, `tick` or `hawkeslib` for Hawkes, `ordpy` for symbolic dynamics.
**Cost:** four to five days for the full set; the tie-fix and compression ratios are an afternoon.

---

## 9. Multivariate structure, causality, and exogeneity

The study is univariate throughout. But a supercomputer is a **coupled physical system**:
outdoor weather → chillers → CRAC units → inlet air → node inlet → core temperature; and
scheduler → job placement → power → temperature. Treating each series as an isolated stochastic
process discards the causal structure that makes the machine predictable at all.

- **Granger causality** (VAR-based) and nonparametric variants — the standard first pass.
- **Transfer entropy** (Schreiber 2000) `[cited-standard]` and **conditional transfer entropy** to
  remove common drivers. Model-free, nonlinear, and directional — the right tool when the coupling
  is a thermostat rather than a regression.
- **Convergent cross mapping** (Sugihara et al. 2012) `[to-audit]` — designed for *deterministic
  coupled dynamical systems*, which is exactly what a cooling control loop is, and where Granger
  causality is known to give the wrong answer.
- **PCMCI / tigramite** for causal discovery with time lags across many series at once, with
  multiple-testing control.
- **Dynamic factor models / PCA over the 96-entity panel.** How many latent factors explain the
  machine? This is simultaneously (a) a predictability measure — few factors means high redundancy
  means high predictability — and (b) the quantitative version of **OI-9**, since the effective
  sample size for significance testing is the number of factors, not the number of nodes.
- **Partial directed coherence / directed transfer function** for frequency-resolved causality.

**The decisive experiment.** Forecast a target family (node temperature) twice: once univariate,
once with exogenous covariates (weather, aggregate facility power, job arrivals from the job table
in its intended role per OI-8). **The skill gap is a direct measure of how much of the observed
difficulty is missing information rather than intrinsic randomness.** If the gap is large, the
paper's framing is wrong in an interesting way: HPC signals are not intrinsically unpredictable,
they are *incompletely observed* — and that is a far more useful conclusion for the operators who
would read this.

**Python.** `statsmodels` (VAR, Granger), `IDTxl` or `PyIF` (transfer entropy), `pyEDM`/`skccm`
(CCM), `tigramite` (PCMCI), `statsmodels.tsa.statespace.dynamic_factor`.
**Cost:** one to two weeks; the univariate-vs-exogenous comparison alone is about three days and is
the part worth doing first.

---

## 10. Distributional structure, volatility, extremes, and proper scoring

A signal can be unpredictable in *level* and highly predictable in *distribution*. The study
measures only the former, and for capacity planning and anomaly detection the latter is what
matters.

- **ARCH-LM test and GARCH fitting** — volatility clustering (M12). Bursty scheduler queues plausibly
  have a flat conditional mean and a strongly predictable conditional variance. The current
  instrument would score them as pure noise.
- **BDS test** (Brock–Dechert–Scheinkman) — a general test for iid-ness in residuals, and therefore
  a general nonlinearity detector. Apply to the residuals of the naive forecast: if they are iid,
  no model can do better, which is a *direct* per-series answer to "is more modelling worth it".
- **Ljung–Box on residuals and on squared residuals** — the second is what catches remaining
  volatility structure and is routinely omitted.
- **Tail index estimation:** Hill estimator, peaks-over-threshold / GPD fits, block maxima.
  `excess_kurtosis` is the *second strongest* correlate with skill in `link_correlations.csv`
  (r = +0.226) and the study instruments it with a single fourth-moment statistic that is itself
  notoriously unstable under heavy tails. A tail index would be both more robust and more
  interpretable.
- **Time-reversibility tests** (Ramsey–Rothman) — asymmetry under time reversal implies nonlinear
  dynamics, and is cheap.
- **Proper scoring rules instead of point-forecast MASE:** CRPS, pinball/quantile loss, log score,
  Winkler interval score. **This sidesteps OI-5 entirely** — OI-5 records that the choice of MASE
  denominator reverses which model family wins and therefore determines the paper's headline. CRPS
  against a *climatological* reference distribution is well-defined, needs no seasonal period, and
  does not admit that failure mode.
- **Conformal prediction interval width** as a distribution-free, model-agnostic per-series
  difficulty measure with finite-sample coverage guarantees. Arguably the most defensible single
  "how hard is this series" number available, because it makes no distributional assumption at all.

**Python.** `arch` (ARCH-LM, GARCH), `statsmodels` (Ljung-Box, BDS), `scipy.stats.genpareto` /
`pyextremes`, `properscoring` or `scoringrules` (CRPS), `MAPIE` or `crepes` (conformal).
**Cost:** three to four days. The CRPS re-scoring is the highest-value part and reuses the existing
forecast outputs.

---

## 11. Feature libraries, forecastability indices, and meta-learning

Where this study sits in a literature that has been asking its question for a decade, plus the
missing control.

### Feature libraries — comparators for the hand-picked 19

| library | size | note |
|---|---|---|
| **catch22 / `pycatch22`** | 22 | already cited and verified in OI-10; selected for cross-domain performance over 93 datasets, ~1000× cheaper than the parent set |
| **hctsa** | ~7,700 | the parent set; MATLAB, but `pyhctsa` subsets exist |
| **tsfresh** | ~800 | with built-in relevance filtering |
| **TSFEL**, **Kats**, **tsfeatures**, **aeon/sktime** transformers | 50–400 | `tsfeatures` is the Hyndman set used by FFORMA |

Running catch22 and tsfresh through the identical LOFO protocol converts "our 19 measures do not
transfer" into "**three independently constructed feature sets, including one selected by another
group for exactly this purpose, do not transfer**". That is a categorically stronger negative
result and it costs almost nothing.

### Named forecastability indices to benchmark against

- **ForeCA Ω** (family 7) — spectral-entropy-based, `[verified]`.
- **Approximate / sample / multiscale entropy** (Pincus; Richman & Moorman; Costa et al. 2002) —
  `sample_entropy` is *declared in the config and not implemented*; multiscale entropy is the
  natural extension and is well suited to signals with structure at several timescales, which is
  every signal here.
- **Syntetos–Boylan / Croston classification** (CV² of nonzero demand × average inter-demand
  interval) from the intermittent-demand literature `[to-audit]`. Designed for exactly the
  intermittent, lumpy, mostly-zero pattern that alarm and error-counter signals exhibit — an
  established taxonomy for the family this study handles worst.

### Meta-learning — the direct precedent

- **Kang, Hyndman & Smith-Miles**, *Visualising forecasting algorithm performance using time series
  instance spaces*, IJF 2017 `[verified]`: project the series into a 2-D feature space by PCA and
  colour by which method wins. **This produces exactly the figure this paper needs** — a map of
  where forecasting fails, instead of a single R² that collapses thirteen families into one number.
- **FFORMS** (Talagala, Hyndman & Athanasopoulos, *J. Forecasting*, 2023) `[verified]` and
  **FFORMA** (Montero-Manso et al., *IJF* 2020) `[verified]`: meta-learning that maps features →
  model *selection* / combination *weights*, and that placed second in the M4 competition. This is
  strong published precedent that **features → model choice works even where features → skill level
  does not**, which is precisely the reframing proposed as idea 4 in `NEXT_EXPERIMENTS.md`. It also
  means the paper's negative result must be positioned against a literature where the positive
  result is established — currently it is not.

### The missing control

**Run this study's exact LOFO protocol on M4 / M3 / the Monash TSF archive.** These are datasets
where features→skill is *known* to work, so they establish what R² this protocol *should* produce
when the relation genuinely exists.

Without a positive control, a negative result cannot be distinguished from a broken protocol —
and given that `log_step_s` is a constant column with r = −6·10⁻¹⁷ and importance exactly 0, and
that `dfa_alpha` has essentially zero correlation with skill where the literature says it should
have some, the possibility that the protocol is what failed is live and untested. This is cheap,
it is the standard referee objection to any negative result, and it should be done before
submission.

**Python.** `pycatch22`, `tsfresh`, `tsfel`, `tsfeatures`, `sktime`/`aeon`, `datasetsforecast` for
M4/Monash. **Cost:** three to four days, of which the positive control is one.

---

## 12. Suggested order

**Tier A — highest value, closes registered open issues, ≤ 1 week each**

1. **Fano / Π_max predictability ceiling** (§2) — closes OI-7; separates hard-signal from bad-model, which is the paper's actual question.
2. **Positive control on M4 / Monash** (§11) — cheap, and no referee will accept a negative result without it.
3. **Stationarity / unit-root / changepoint battery** (§5) — implements what the pre-registered config already declares; the unit-root test alone explains the `error_counter` fold.
4. **Discrete & symbolic suite** (§8) — the tie-handling fix, Markov mixing time, dwell-time hazards; repairs OI-11 and covers the three families the instrument currently mismeasures.
5. **Univariate vs exogenous skill gap** (§9) — tests whether the difficulty is intrinsic or informational, which is the strongest alternative explanation for everything reported.

**Tier B — strengthens the instrument**

6. **ForeCA Ω + Lomb–Scargle at native cadence** (§7) — a published forecastability index as comparator, and a partial escape from OI-4.
7. **Entropy-power / Gamma-test noise floors** (§3) — bounds the floor from both sides for continuous series.
8. **CRPS and conformal-width targets** (§10) — sidesteps OI-5's denominator problem entirely.
9. **catch22 + tsfresh through the same protocol** (§11) — makes the negative result feature-set-independent.

**Tier C — deepens the mechanism story**

10. **Nonlinear dynamics with surrogate controls** (§4) — λ₁ as a model-free forecast horizon.
11. **MFDFA and DFA order sensitivity** (§6) — probably explains why `dfa_alpha` came out inert.
12. **Instance-space map** (§11) — the figure that replaces a single R² with a picture of where forecasting fails.

**Cheapest first three hours:** randomised tie-breaking in `permutation_entropy`; gzip compression
ratio as a complexity measure; ADF+KPSS on all 1,402 series. All three run on
`data/derived/features.parquet` and the existing series loader, and all three attack a documented
defect.
