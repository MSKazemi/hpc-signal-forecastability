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
