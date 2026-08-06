# Round 10 — review of `paper/paper.pdf` (19 pp.) — final round

**Conflict:** reviewer is the author. **Access:** complete — text read, all six figures rendered
and inspected visually, all generating scripts re-run and diffed.

## Method

Round 09 established that re-reading finds stale numbers one at a time while **re-running finds
them in classes**. Round 09 applied that to the tables. This round applies it to the one artefact
class it did not cover: the figures.

## Findings

**No new Critical or Major findings.** Specifically:

*Figures are not stale.* All six regenerate from `09_figures.py` with byte-identical text content
(labels, ticks, annotations, legends). The defect that produced OI-16 in the tables does not exist
in the figures.

*Figures agree with their tables, checked visually rather than by extraction.* Figure 4's sixteen
plotted points match `skill_by_tier.csv` at every tier × horizon, including the fact the paper
leans on — that the neural tier beats gradient-boosted trees at three of four horizons, so the
x-axis is a-priori capacity order and not a skill ranking. Figure 5's per-family headroom labels
match `ceiling_gap.csv` to the displayed precision across all 17 families, and its shaded
calibration band matches the 0.237–0.304 over-statement range in `ceiling_calibration.csv`.

*The ceiling section's derived claims recompute.* "Ceiling error varies by 0.067 while the Bayes
optimum varies by 0.441" → 0.0669 and 0.4406. "Persistence falls short by at most 0.008" → max
0.0075. "0.24–0.30 over-statement" → 0.237–0.304.

**Two Minor points, recorded and not changed:**

1. The abstract's "nine [families] leaving 12–31 percentage points" counts humidity, whose actual
   headroom is 0.118 and which the figure labels +0.12. The rounding is consistent between text
   and figure; stating "11.8" in an abstract would be false precision about a quantity the same
   section withdraws.
2. "Four sitting at their ceiling" includes error counters, which sit 0.026 *above* their ceiling.
   The paper already reports and explains ceiling over-statement at length, and §5.6 states the
   18% exceedance directly, so the summary word "at" is not concealing anything.

## Reference audit

No change across rounds 08–10. 14 entries; 6 read in full; 8 definition-only, paywalled, and
attributed no finding. No wrong papers, no wrong author names, no unsupported claims about prior
work. Unchanged known limitations: three entries cite a version of record while a preprint was
read, and the AAAI PDF for Borghesi et al. 2019 was unobtainable after three attempts.

## Verdict

The stop condition is met, and this time for the right reason: the round that applied round 09's
method to the remaining artefact class found nothing. Title T13 stands. See `FINAL.md`.
