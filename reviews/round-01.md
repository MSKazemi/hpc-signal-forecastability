# Round 01 — review of `paper/paper.pdf` (10 pp.)

**Reviewer conflict:** the reviewer is also the author. Findings are tied to recomputations from
`results/tables/*.csv` so a third party can repeat them.
**Access:** `pdftoppm` unavailable; manuscript read as extracted text, figures re-rendered to PNG
from the same code and data. Compiled-PDF layout defects not assessed.

## Recommendation: Major revision

The manuscript's central claim is now **weaker than the evidence supports**, because the analysis
has been extended since the text was written and the text has not caught up. Two additions change
the result materially.

## Critical

**C1 — The paper reports a raw R² and misses the actual finding: ordering transfers, level does not.**
*Location:* abstract ¶4, §5.5, conclusion. *Confidence:* High.

`link_cv.csv` now carries `spearman_within` and `r2_level_corrected`. The decomposition:

| quantity | mean | median | positive |
|---|---:|---:|---:|
| raw R² (what the paper reports) | −0.163 | +0.061 | 9/15 |
| **level-corrected R²** | **+0.009** | **+0.105** | **11/15** |
| **within-family Spearman** | — | **+0.397** | **10/15 at p<0.05** |

The model ranks series *within* an unseen family correctly — Spearman up to +0.80 (memory), +0.72
(CPU utilisation), +0.68 (setpoint) — but assigns the wrong absolute level, and R² punishes level
error while Spearman does not. "The measures transfer weakly" is the wrong summary. The correct one
is that **the ordering transfers and the level does not**, which is both more precise and more
useful: a practitioner can rank candidate signals by forecastability without being able to predict
the achievable skill outright.

*Fix:* rewrite the finding around the decomposition; report Spearman and level-corrected R²
alongside the raw value rather than instead of it.

**C2 — A null-group control now exists and the paper does not mention it.**
*Location:* §5.5. *Confidence:* High.

`link_null.csv`: running the identical protocol with *random* groups of matched size gives mean
R² **+0.329** (95% range [0.215, 0.381]) with 100% of groups positive, against **−0.163** and 60%
for the real families — **p = 0.000** over 100 draws.

This is the control the negative claim most needed. It rules out the alternative that the protocol
simply cannot transfer across any held-out grouping: arbitrary grouping transfers fine, so the
failure is specific to crossing *family* boundaries, and the family axis carries real structure.
Omitting it leaves the headline weaker than the evidence warrants.

*Fix:* report it in §5.5 as the primary control on the leave-one-family-out design.

## Major

**M1 — The measure profile grew from 14 to 21 signal measures; the Method section still describes the old set.**
`adf_pvalue`, `kpss_pvalue`, `changepoint_rate`, `sample_entropy`, `compression_ratio`,
`monotone_fraction` and `reset_rate` are now computed and used. §4.4 lists neither the stationarity
tests nor the two counter-specific measures. Notably `monotone_fraction` was added in direct
response to the previous round's diagnosis of the `error_counter` failure, and the paper should say
whether it helped (error_counter's level-corrected R² is −0.62 against −1.88 raw, so partially).

**M2 — No architecture/pipeline description.** The paper describes what was measured but not the
system that measured it: eleven pipeline stages, their data flow, where each artefact is written,
what is committed versus regenerable, or the cost of a full run. A reader cannot reproduce the
study's *shape* from the paper alone.

**M3 — No hyperparameter table.** Model capacities, lag windows, iteration counts, training-window
cap, origin count and horizon set are scattered through prose or absent. The capacity claim depends
on these being legible.

**M4 — No failure-mode or complexity discussion.** Nothing states what the pipeline does with a
constant series, a series shorter than the minimum, a non-numeric value column, or a partition
whose entity set is empty — all of which occur and are handled in code.

## Moderate

- **Mo1** Three committed result tables (`link_ablation`, `link_correlations`, `link_importance`)
  are cited only as prose numbers; the ablation especially deserves a table.
- **Mo2** `constant_share.pdf` and `sampling_irregularity.pdf` are now included, but
  `landscape.pdf` is still generated and unused.
- **Mo3** §5.3's tier table appears only as a figure; the numbers should be a table too, since the
  paper quotes four of them in the abstract.

## Reference audit

Re-run against `paper/refs.bib` (8 entries after the previous round removed the unused one).

- **No change in verdicts since the last audit.** 4 read in full (ExaData, catch22, Zeng et al.,
  Borghesi et al. 2019) — identity CORRECT, author names CORRECT, all claims SUPPORTED, two
  verbatim quotations confirmed.
- 4 remain definition-only and paywalled (Hyndman & Koehler, Bandt & Pompe, Peng et al.,
  Assimakopoulos & Nikolopoulos). No finding is attributed to them.
- **Outstanding, unchanged:** three entries cite a version of record while a preprint was read; the
  AAAI PDF for Borghesi et al. 2019 remains unobtainable (OJS 404).
- **New check this round:** the added measures (`sample_entropy`, `compression_ratio`,
  `changepoint_rate`, ADF, KPSS) introduce methods with standard citations that the bibliography
  does **not** carry. Sample entropy (Richman & Moorman), the ADF and KPSS tests, and any
  changepoint method used should be cited if the paper describes them. **This is a new gap created
  by the code extension.**
