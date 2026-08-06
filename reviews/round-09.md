# Round 09 — review of `paper/paper.pdf` (19 pp.)

**Conflict:** reviewer is the author. **Access:** complete — extracted text, plus every generating
script re-run and diffed against its committed output.

## Method this round

Rounds 08, 04 and 02 all found the same class of defect: a number in the manuscript that no longer
matched the table under it. Finding them one at a time was not working, so this round did the
systematic version — enumerate every numeric claim, recompute it from `results/tables/`, and
separately **re-run every generating script and diff**. That second half is what found the two
worst issues, and no amount of reading would have.

## Critical

**C15 — A table row in the paper that no committed artefact reproduces.**
*Confidence:* High. Table 5's `M100 (real)` row read −0.189 / 9-of-15 / +0.495. The linking
analysis gives **−0.167 / 10-of-15 / +0.523**. The row had been hand-entered and never derived,
and `protocol_control.csv` contains only the four synthetic arms.

This is the specific defect the study's reproducibility claim exists to exclude, and its stale
values had propagated into two prose passages (§5.4's "9 of 15 on R²", contradicting §5.3's
"10 of the 15" three pages earlier, and the "M100 (−0.189)" comparison against the null arm).

Fixed at the source: `12_protocol_control.py` now derives the real row from `link_cv.csv` with the
same expressions it applies to the synthetic arms.

**C17 — A committed table went stale against its own generating code (OI-16).**
*Confidence:* High. `protocol_control.csv` was generated in round 03; the measures then changed in
rounds 04–07 and the script was never re-run. Re-running moves three of four arms — `no_law` from
6/15 to 7/15 families positive and its median Spearman from +0.100 to +0.156, `disjoint` from
−0.050 to −0.035.

The diagnostic pattern is worth recording: `portable_oracle` reproduced to fifteen significant
digits while the other three arms moved. The oracle arm uses the true generating parameter as its
only feature and is therefore invariant to any change in the measures. **My first reading of this
was that the pipeline was nondeterministic. It is not** — features, targets and the
cross-validation each reproduce exactly across processes, and every `link_*.csv` reproduces to
within 4e-15. The evidence was consistent with two explanations and I initially named the wrong one.

**C16 — Two tables shared one label, and the build check could not see it.**
*Confidence:* High. `\label{tab:fewshot}` was defined twice, so both `\ref`s silently pointed at
the second table. `paper.log` had warned since at least round 06; the `make paper` target only ever
grepped for *undefined* references. The duplicate table is removed and the check now fails the
build on `multiply defined`.

## Major

**C11 — The few-shot "families > 0" column did not count families.**
*Confidence:* High. Its values (60/61/64/68/70/72%) were the fraction of *(family, draw)* rows.
Counted over families the series is 8/13 → 8/13, essentially flat. The paper therefore claimed in
§5.3 that labelling "raise[s] the share of families above zero from 60% to 72%" while stating
correctly in §5.5 that the count "does not rise with k". **The manuscript contradicted itself
about its own experiment**, and the mislabelled column is why.

**C12 — Three of four per-family few-shot values were wrong, one with the sign of the change
reversed.** *Confidence:* High. Error counters improve to −0.14 (paper: −0.03); alarm states to
−0.74 (paper: −1.15); CPU utilisation goes +0.18 → **+0.20**, which the paper reported as a
decline to +0.12.

**C18 — The k-sweep compared different family sets across its own rows.**
*Confidence:* High. Storage and weather have too few series to give up 10 and still leave a
held-out set, so k=10 and k=20 were scored on 13 families and k=0–5 on 15. The headline "−0.21 to
+0.06" spanned that change. On the 13 families scorable at every k it is **−0.26 to +0.06** — a
larger improvement, so the finding strengthens once stated honestly.

**C14 — All three extrapolation correlations were stale, and one wording claim does not survive
correction.** *Confidence:* High. Reported +0.78 / −0.66 / −0.22; actual Pearson **+0.85**
(p<0.001), **−0.60** (p=0.019), **−0.40** (p=0.14, n=15). The paper called the third "barely
touching the ordering", which −0.40 does not support. It does hold on ranks (Spearman +0.01), so
the paper now reports both and says which carries the claim.

## Reference audit

No change from round 08. 14 entries, 6 read in full, 8 definition-only and paywalled; no wrong
papers, no wrong author names, no unsupported claims. Nothing this round touched a citation:
every correction was a number against a committed table.

## What the round says about the process

Eight rounds of reading found stale numbers one at a time. One round of *re-running the scripts*
found the two worst defects in the study — a hand-entered table row and a table stale against its
own code — and neither was visible in the text. The gap is that `make reproduce` exists but nothing
runs it, so a stale table stays invisible until someone re-runs by hand. That is now the largest
remaining process risk and is recorded as OI-16.
