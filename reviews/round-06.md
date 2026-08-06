# Round 06 — review of `paper/paper.pdf` (16 pp.)

**Conflict:** reviewer is the author. **Access:** extracted text; figures re-rendered from source.

## Recommendation: Accept with minor revision

## Critical

**C8 — An information-theoretic ceiling is implemented, tested, and used nowhere. Computing it
overturns the premise of the open issue it was meant to close.**
*Confidence:* High.

`measures.py` gained `entropy_rate`, `max_predictability` and `predictability_ceiling` — the Fano
bound on next-bin accuracy — with 18 test references and no consumer. `OPEN_ISSUES` recorded OI-7
(the error floor) as "planned and never implemented".

Computing it across 1,402 series (`scripts/13_ceiling.py`, ~35 min) gives a median of 0.854 with
sharp family separation: network 0.575 and electrical 0.638 against alarm states and setpoints at
0.996.

**But it is not a floor.** 77.5% of series achieve a skill *above* their own ceiling. Fano bounds
next-*bin* accuracy on a symbolised sequence; skill is a scale-free error ratio on continuous
values. A signal that extrapolates easily but bins poorly exceeds the first while scoring well on
the second. Had this been reported as "the irreducible error floor" — which is what OI-7 asked for
and what the obvious framing would have been — the paper would have carried a claim contradicted by
its own data in three quarters of cases.

**What it is worth instead:** the strongest *ordinal* predictor in the study. Spearman +0.69 with
achieved skill across series and +0.73 across family medians, ahead of the compression ratio
(−0.42) and every entropy measure. It is derived from information theory rather than fitted, which
makes it a stronger instance of the paper's central claim — rank well, calibrate badly — rather
than a repetition of it.

*Applied:* new paragraph in §5.5 stating the value, stating plainly that it is not a bound, and
giving the ordinal result. OI-7 moves to RESOLVED with the residual (a bound in MASE units) named.

## Moderate

- **Mo11** The ceiling is computed on a 16-symbol alphabet by default. Family comparisons are only
  valid at fixed alphabet size, which `predictability_ceiling` returns alongside the value — the
  implementation is careful about this and the paper does not need to belabour it, but the alphabet
  should be stated. Added to the text.
- **Mo12** `scripts/13_ceiling.py` takes ~35 minutes, far longer than any other stage. Noted in the
  pipeline discussion so nobody re-runs the pipeline expecting it to be fast.

## Reference audit

**Second attempt at the AAAI version of record for Borghesi et al. 2019: failed again.** OJS
`/article/view/4997` returns a non-PDF payload; the CDN path returns 403. Three routes have now been
tried across the session. Recorded as *attempted and unavailable* rather than untried — it needs
institutional access.

No other change. Bibliography 12 entries: 5 read in full, 7 definition-only and paywalled. No wrong
papers, no wrong author names, no unsupported claims.

**New method, no new citation needed?** The Fano-inequality construction is standard and the code
implements it directly. The canonical reference for this use — entropy rate plus Fano to bound
sequence predictability — is Song et al., *Limits of Predictability in Human Mobility* (Science,
2010). **The paper should cite it and currently does not.** Flagged for round 07; not added this
round because the source was not obtained and this project does not cite unread work as if read.
