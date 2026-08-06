# Loop changelog

Target: `paper/paper.tex` → `paper/paper.pdf`.
Snapshots in `paper/versions/`, reviews in `reviews/round-NN.md`, titles in `reviews/titles.md`.

**Scope note.** The loop prompt referred to `paper/main.tex`; this repository's manuscript is
`paper/paper.tex` and its PDF is `paper/paper.pdf`, which is what `paper.pdf` in the prompt
matches. Paths adapted accordingly.

---

## Round 01 — 2026-08-06

**Snapshot:** `paper/versions/main-r01.tex` (10 pp. before edits, 12 pp. after)
**Review:** `reviews/round-01.md` · **Recommendation:** Major revision

### Why this round found so much
The analysis code had been extended since the manuscript text was last written — a random-group
null control, a level/ordering decomposition, and seven new measures — and the text had not caught
up. The paper was **understating its own result**.

### Applied

| ID | Change | Why |
|---|---|---|
| C1 | Rewrote the central finding as **ordering transfers, level does not** | `link_cv.csv` now carries `spearman_within` and `r2_level_corrected`. Median Spearman +0.40, significant for 10/15 families, up to +0.80; level-corrected R² median +0.11, positive 11/15. Raw R² penalises level error, Spearman does not. "Transfers weakly" was the wrong summary. |
| C2 | Added the **random-group null** to §5.5 and the abstract | Random groups transfer easily (median R² +0.33, all positive) against −0.16 for real families, p<0.001 over 100 draws. Rules out "the protocol cannot transfer at all" and shows the family axis carries real structure. This is the control the negative claim most needed and it was missing from the text. |
| M1 | Updated §4.4 to the **21-measure** profile | ADF, KPSS, changepoint rate, sample entropy, compression ratio, monotone fraction, reset rate are computed and used but were undescribed. Flagged that monotone fraction and reset rate were added *in response to* the error-counter failure rather than chosen a priori — and that they help but do not repair it (level-corrected −0.62 vs −1.88 raw). |
| M2 | Added §4.7 **pipeline** with an 11-stage table | The paper described what was measured, not the system that measured it. Includes the two engineering constraints that bounded the study: 55 billion rows against 62 GB shared memory, and thread pinning (unpinned, the sweep runs ~90× slower with no error shown). |
| M3 | Added **hyperparameter table** | Grid, panel, horizons, origins, training window, model capacities, seed. The capacity claim depends on these being legible. |
| M4 | Added §4.8 **failure modes** | Constant and near-periodic series (undefined MASE), too-short series, non-numeric columns, failed fits. Degenerate input is the common case here, not an edge case. |
| — | Corrected null statistic label | Wrote "mean +0.33" where +0.33 is the **median** across draws; mean is +0.32. Caught by the numbers ledger. |

### Deferred, with reasons
- **Mo1** ablation/importance/correlation tables not yet added as tables — the ablation deserves
  one; deferred to round 02 to keep this round's diff reviewable.
- **Mo2** `landscape.pdf` still generated and unused. Deferred: after the C1 rewrite, the figure's
  original claim (entropy ≈ repetition) is no longer a headline, so its place in the paper needs
  rethinking rather than mechanical insertion.
- **Reference audit, new gap:** the seven added measures introduce methods (sample entropy, ADF,
  KPSS, changepoint detection) with standard citations the bibliography does **not** carry. Round
  02 must add them — the paper now describes methods it does not cite.
- **Unchanged from previous audits:** three references cite a version of record while a preprint
  was read; the AAAI PDF for Borghesi et al. 2019 remains unobtainable (OJS 404).

### Verification
All 9 new/changed numbers re-checked against `results/tables/*.csv` — 9/9 exact after the label
fix. 140 tests pass. Paper builds at 12 pp. with zero undefined references.

### Titles
Three candidates added. Running leader **T3** on total score (18) but **T1** is the better
scientific title; decision deferred to the final round per the loop rules.

---

## Round 02 — 2026-08-06

**Snapshot:** `paper/versions/main-r02.tex` (12 pp. before, 13 after)
**Review:** `reviews/round-02.md` · **Recommendation:** Minor revision (up from Major)

### Applied

| ID | Change | Why |
|---|---|---|
| C3 | Refreshed **every** linking number | The analysis was re-run on the extended 21-measure profile after round 01's text was written. Mean R² −0.16→−0.19, median Spearman +0.40→+0.50, significant 10/15→9/15, max +0.80→+0.83, level-corrected positive 11/15→10/15, worst family −1.88→−2.39. Every conclusion's direction unchanged; every value was wrong. |
| M5 | Rewrote the ablation claim; added Table 3 | The paper said dropping instrument covariates *improves* the model. With the extended profile it does not (−0.206 vs −0.189). The "not an instrumentation artefact" conclusion survives but needed a different argument: removing them costs almost nothing, using them alone destroys the model (−15.0). |
| M6 | Reported that **removing entropy improves transfer** | `no_entropy` −0.079 is the best of four ablations, beating the full profile at −0.189. Stronger evidence for OI-11 than the correlation data gave. |
| M7 | Reported the **gzip compression ratio as the strongest correlate** | r = −0.42 [−0.52, −0.31], and top of permutation importance at 0.202, double the next feature. A general-purpose compressor outranking every hand-designed entropy measure is a finding, not a detail. |
| — | Added 4 method citations, wired at point of use | Richman & Moorman (sample entropy), Dickey & Fuller (ADF), Kwiatkowski et al. (KPSS), Truong et al. (changepoint). Closes the gap round 01 opened. Bandt & Pompe and Peng et al. now cited in §4.4 where a reader looks for them. |

### Deferred / resolved-as-exclusion
- **Mo4 `landscape.pdf` — resolved as a deliberate exclusion, not an oversight.** Its claim (entropy
  ≈ repetition fraction) is now superseded by the ablation evidence in M6, which makes the same
  point more strongly. Including it would restate a weaker version of a result the paper already
  makes better. The figure remains generated so the claim stays checkable.
- **Mo5** importance table deferred: with compression ratio at 0.202 and every other feature below
  0.10, a full table would add length without information. The two values that matter are in prose.
- **Unchanged:** three references cite a version of record while a preprint was read; the AAAI PDF
  for Borghesi et al. 2019 remains unobtainable (OJS 404). Not fixable without institutional access.

### Verification
12/12 changed numbers re-checked against `results/tables/*.csv`; 5 stale strings confirmed absent
from the compiled PDF. 144 tests pass. Paper builds at 13 pp., zero undefined references.

### Titles
T4–T6 added. Leader on raw score is still T3 (18), but the scoring weights searchability equally
with accuracy, which flatters a title that foregrounds a secondary result. Leaning T1/T6 for the
final round.

### Note on loop convergence
Round 02 found substantive issues, so the loop continues. The dominant failure mode across both
rounds has been the same: **the analysis code moves faster than the manuscript text**, and every
critical finding so far has been the text lagging the tables rather than a flaw in the analysis.
If round 03 finds only cosmetic issues, that is the stop condition.
