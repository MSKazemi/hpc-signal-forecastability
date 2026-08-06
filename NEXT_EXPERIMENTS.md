# Next experiments

Ten improvements that are **not** already registered in `OPEN_ISSUES.md` and **not** in the
revision plan of `review_hpc-signal-forecastability_2026-08-06.md`. Each is grounded in a number
from `results/tables/` or a line of the code, states what it would change about the paper's claim,
and gives its cost honestly.

`data/derived/features.parquet` (1,402 rows) and `data/derived/skill.parquet` are on disk, so
items **1–6 and 8 need no re-extraction and no archive access**.

---

## 1. Split the transfer failure into a *level* error and a *rank* error

**Evidence.** In `link_cv.csv`, `train_skill_mean` is essentially constant across all 13 folds
(0.419–0.508, spread 0.09), while `test_skill_mean` ranges from **−0.220** (humidity) to **+0.988**
(alarm_state) — a spread of 1.21, thirteen times larger. The model is being asked to locate the
level of an unseen family from a training set whose level never moves. R² punishes exactly that,
and the two worst folds (`error_counter` −10.93, `alarm_state` −0.64) are the two with the most
extreme test means.

**Do.** Report, per held-out family, the Spearman ρ between predicted and observed skill *within*
that family, alongside R². Bootstrap a CI on each.

**What it would change.** If ρ is consistently positive, the honest claim becomes: *the measures
rank series inside a family they have never seen, but cannot predict where that family sits.* That
is a real, usable, and much more interesting result than "no portable law", and it is the natural
formal statement of what reviewer finding C1 noticed informally.

**Cost.** Under an hour. `src/hsf/link/analysis.py::leave_one_family_out` already holds both
vectors; it just discards them after computing R².

---

## 2. A random-group permutation null for the leave-one-family-out R²

**Evidence.** The whole negative claim is that grouping by *family* breaks transfer. That is
asserted, never tested — there is no null distribution for the R² spread anywhere in the results.
With 331 series, 19 features, and 13 folds, a mean of −0.82 with one fold at −10.9 may be what
*any* 13-way split of this data produces.

**Do.** Re-run the identical CV with 13 random groups of matched sizes, B ≈ 500. Report where the
observed family-grouped R² distribution falls in the null.

**What it would change.** Either the family axis is shown to be the genuine barrier (the paper's
claim becomes *tested*, not merely *reported*), or the failure is generic small-sample instability
and the headline must be rewritten. Both outcomes are publishable; not knowing which is not.

**Cost.** A few minutes of compute. Combines naturally with item 1.

---

## 3. Few-shot calibration: how many labelled series does a new family cost?

**Evidence.** R² = 0 means "no better than knowing the held-out family's own mean skill". The study
tests only the k = 0 case. Nobody deploying this would refuse to label a handful of series.

**Do.** Sweep k ∈ {0, 1, 2, 5, 10, 20} labelled series drawn at random from the held-out family
into the training set; plot held-out R² against k, averaged over draws.

**What it would change.** It converts a flat negative into an operational protocol: *model-free
measures alone do not transfer; with k ≈ 5 labelled series from the new family they reach R² = X.*
This also answers reviewer question 1 directly, and it is the single item most likely to give the
paper a positive deliverable without weakening the negative one.

**Cost.** Half a day. Same machinery as item 1, with a fold-construction loop around it.

---

## 4. Stop regressing on `best_skill` — it is a biased statistic, and the wrong question

**Evidence.** `analysis.py:86–88` sets the target to the **maximum** over 12 models of a per-series
median skill. The max of 12 noisy estimates is upward-biased, and the size of that bias depends on
how many models returned a valid skill for the series — which varies systematically by family
(constant-heavy families lose models to undefined MASE). Part of the between-family level shift in
item 1 may be this artefact rather than signal physics.

**Do.** Two changes, both cheap.
(a) Re-run the linking analysis against *fixed* targets — `persistence` skill, and the per-tier
median — so no result rests on an order statistic.
(b) Reframe the target as **which tier wins**, a 4-way classification. Report accuracy against the
majority-class baseline.

**What it would change.** (b) is baseline-invariant: it is immune to the MASE-denominator
reversal that OI-5 shows determines the paper's headline, because changing the denominator rescales
every model's skill without necessarily changing the argmax. It is also the operational question —
an operator picks a model, they do not predict an R². "Measures cannot predict skill level but do
predict model choice at N% vs a 40% baseline" would be a strong, defensible headline.

**Cost.** One day. No new forecasting.

---

## 5. Predict the *forecast horizon*, not the skill at one horizon

**Evidence.** `scripts/08_link.py:62` fixes the linking horizon to `horizons[1]` = 4 steps (1 h),
one point on a curve that collapses from +0.477 to −3.241 across the four horizons in
`skill_by_tier.csv`. The collapse *rate* is the physically meaningful quantity: thermal diffusion
should decay slowly, scheduler queues fast.

**Do.** Fit skill(h) per series over h ∈ {1, 4, 12, 96} and derive a scale-free target — the
crossover horizon at which skill first goes negative (interpolated), i.e. *how far ahead this
signal is worth forecasting at all*. Regress that on the measures under the same LOFO protocol.

**What it would change.** It gives the study a target that is stated in operational units
(minutes of usable lead time), largely immune to the denominator problem, and far more likely to
be predictable from measures like DFA exponent and seasonal strength than a skill level is. If
*this* transfers where skill level does not, the paper's story changes from a null result to a
mechanism: predictability measures capture the decay of memory, not the level of noise.

**Cost.** One to two days. Uses the existing `skill.parquet` — the four horizons are already there.

---

## 6. Add the structural features the feature set is missing, and drop the dead one

**Evidence.** `error_counter` alone (R² = −10.93) drives the headline mean; excluding it moves the
mean from −0.82 to +0.03. `src/hsf/features/measures.py` implements 15 measures and **none of them
measures monotonicity** — `drift_ratio` is the nearest, and it has r = −0.019 and importance
0.0009, i.e. it does not detect counters. Meanwhile `log_step_s` has r = −6.1e-17 and importance
exactly −1.2e-16: it is *constant* in the linking sample, because regridding to 15 minutes
destroyed the cadence variation it was meant to capture. The feature set is carrying a dead column
and missing the one property that explains its worst fold.

**Do.** Add `monotone_fraction` (share of non-negative differences), `n_resets` (counter wraps),
`sign_run_entropy`, and `unique_value_growth_rate`. Replace `log_step_s` with the **native**
cadence from `manifest.parquet`, which survives regridding as metadata.

**What it would change.** Either the error_counter fold recovers — in which case the headline moves
to roughly zero and the paper's story becomes "transfer fails for a *nameable, detectable* reason,
and here is the detector" — or it does not, and the negative result is substantially stronger for
having survived a targeted attack. This is the highest information-per-hour item on the list.

**Cost.** One to two days, including known-answer tests in `tests/test_measures.py`.

---

## 7. Run catch22 as an independent, externally-selected feature canon

**Evidence.** catch22 is already cited and verified in `OPEN_ISSUES.md` OI-10 (arXiv:1901.10200,
4,791 → 22 features, ~7% mean accuracy loss over 93 datasets). The current claim is that *these 19
hand-picked measures* do not transfer — which invites the obvious objection that better features
exist.

**Do.** Compute pycatch22 over all 1,402 series and re-run the full LOFO protocol on (a) catch22
alone, (b) the study's 19, (c) the union.

**What it would change.** It upgrades "our measures fail" to "a canon *selected by an independent
group for cross-domain performance over 93 datasets* also fails on HPC telemetry", which is
materially harder to dismiss. If catch22 transfers where the hand-picked set does not, that is a
finding too — and a better paper.

**Cost.** One day. One dependency; catch22 is milliseconds per series.

---

## 8. Test whether the taxonomy, not the physics, produces the result

**Evidence.** "Transfer" is defined entirely relative to the 13 semantic families assigned a priori
by `src/hsf/taxonomy.py`. The grouping is a modelling choice, and the headline is a property of it.

**Do.** Re-run LOFO under three alternative groupings: leave-one-**plugin**-out (8 groups, defined
by the instrument rather than by semantics), leave-one-**value_kind**-out (categorical / quantised /
continuous), and groups obtained by unsupervised clustering of the feature space.

**What it would change.** If transfer fails under every grouping, "no portable law" becomes robust
rather than taxonomy-contingent. If it holds under plugin grouping and fails under semantic
grouping, the finding is about how signals were *labelled*, not about signal physics — which would
be a serious threat to the current conclusion and is currently untested. Pairs with item 2.

**Cost.** One day. All three grouping keys are already columns in the derived tables.

---

## 9. External validation on a second machine

**Evidence.** Every number in the paper comes from M100. A claim about the *portability* of
predictability measures that is tested only within one supercomputer is testing the weaker half of
its own question.

**Do.** Take 2–3 families with cross-system analogues — `cpu_utilisation`, `memory`, `scheduler` —
from a second public source (other CINECA releases; Google/Alibaba cluster traces, which have no
facility side but do have utilisation and scheduler signals) and test whether the *within-family*
relation from item 1 survives a change of machine.

**What it would change.** Cross-machine transfer of the within-family relation would be the
strongest positive result available to this study and would justify the paper's framing far better
than either the current negative or a repaired positive. Cross-machine *failure* would show the
relation is machine-specific, which is also a clean, quotable result.

**Cost.** The highest here — a week or more, and it needs a second dataset ingested through
`src/hsf/io/`. Scope it to three families and one month; do not generalise the pipeline.

---

## 10. Ship the negative result as a benchmark others can attack

**Evidence.** The repo already commits everything the task needs: `features.parquet` (1,402 × 19),
`skill.parquet` (per series × model × horizon × denominator), `taxonomy.csv` (the grouping), and
`results/tables/*.csv` (the baselines). The one objection a negative result cannot answer from the
inside is "better features would have worked".

**Do.** Add `benchmark/` with a frozen split, `scripts/11_benchmark.py` implementing the LOFO
protocol and the scoring (R², within-family ρ from item 1, tier-choice accuracy from item 4), and
this paper's numbers as the reference baselines.

**What it would change.** It hands the "maybe better features exist" objection to the community
instead of absorbing it as a limitation, and it makes the artefact citable independently of whether
the paper's conclusion survives. A negative result that others can run against is worth
considerably more than one they can only read.

**Cost.** Two to three days, mostly packaging and documentation. No new science.

---

## Suggested order

**Run first (local data, hours to a day each, may change the headline):** 6 → 1 → 2 → 4.
Item 6 attacks the outlier that drives the result; items 1, 2 and 4 establish what the result
actually is once it is measured properly.

**Then (strengthens whichever conclusion survives):** 8 → 7 → 5.

**Then (new deliverables):** 3 → 10.

**Only with a real time budget:** 9.
