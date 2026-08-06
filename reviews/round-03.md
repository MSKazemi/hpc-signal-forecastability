# Round 03 — review of `paper/paper.pdf` (13 pp.)

**Conflict:** reviewer is the author. **Access:** extracted text; figures re-rendered from source.

## Recommendation: Minor revision

Round 03 is dominated by one addition: a **synthetic protocol control** (`scripts/11_protocol_control.py`,
`results/tables/protocol_control.csv`) that was not in the paper. It is the most consequential
control in the study and it changes what the paper is entitled to conclude — in the paper's favour
on one axis, and against its stated mechanism on another.

## Critical

**C4 — The protocol control is absent from the paper, and it answers the paper's strongest objection.**
*Location:* §5.5 (missing). *Confidence:* High.

Three synthetic arms run through the *identical* pipeline — same measures, same forecast harness,
same `leave_one_family_out` — differing only in how the series were generated:

| arm | mean R² | median R² | families +ve | median Spearman |
|---|---:|---:|---:|---:|
| `portable` — a genuine portable law | **+0.248** | +0.248 | 13/15 | **+0.584** |
| `portable_oracle` — same, with the true parameter given | +0.233 | +0.214 | 13/15 | +0.576 |
| `disjoint` — same law, non-overlapping per-family bands | −0.096 | −0.102 | 2/15 | **−0.050** |
| `no_law` — skill permuted across series | −0.070 | −0.053 | 6/15 | +0.100 |
| **M100 (real)** | **−0.189** | +0.053 | 9/15 | **+0.495** |

The `portable` arm is the positive control the study lacked: the protocol **does** recover a genuine
portable law, at R² +0.25 with 13 of 15 families positive. So M100's negative R² is a statement
about M100, not about leave-one-family-out cross-validation on this feature set. Without this arm,
"we found no portable law" was indistinguishable from "our protocol cannot find one."

*Fix:* add the control as its own subsection with the table; it belongs before the M100 result, not
after it.

**C5 — The control refutes the mechanism the code's own docstring proposes, and the paper must not
adopt it.**
*Confidence:* High.

`11_protocol_control.py` describes the `disjoint` arm as "the hypothesis for what M100 actually
does" and predicts "R² collapses while the within-family ordering survives." **The ordering does not
survive:** disjoint's median Spearman is **−0.050**, against **+0.495** for M100 and +0.584 for
`portable`.

M100's ordering transfer therefore looks like a genuine shared law (+0.495 vs +0.584), not like
band-disjoint extrapolation (−0.050), while its R² looks like the failures. That is direct evidence
for the "ordinally portable, cardinally not" reading the paper already adopted in round 01 — but it
also means the paper must **not** explain the level failure as disjoint parameter ranges, which is
the natural story and is now ruled out. The mechanism remains open.

## Major

**M8 — `no_law` scores −0.070 while M100 scores −0.189 on raw R².** On the headline metric alone,
M100 transfers *worse* than data with no relation at all. This is not a contradiction — M100's
Spearman (+0.495) is five times `no_law`'s (+0.100), so the relation is plainly there — but it is a
sharp demonstration that raw R² is the wrong summary statistic for this question, and the paper
should say so explicitly rather than leaving a reader to notice that its headline number is worse
than noise.

## Moderate

- **Mo6** `portable_oracle` (the true generating parameter supplied as a feature) scores +0.233,
  *slightly below* `portable` at +0.248. Worth one sentence: even a perfect feature does not lift
  transfer above the level the measured features already reach, which bounds how much of the
  remaining gap is a feature-quality problem.
- **Mo7** The synthetic arms use 600 series across 15 families against M100's 1,082 across 15;
  close enough not to confound, but the paper should state it rather than leave it inferable.

## Reference audit

No change from round 02. Bibliography is 12 entries: 5 read in full (ExaData, catch22, Zeng et al.,
Borghesi et al. 2019, Truong et al.), 7 definition-only and paywalled. No wrong papers, no wrong
author names, no unsupported claims.

**Unchanged and unfixable here:** three entries cite a version of record while a preprint was read;
the AAAI PDF for Borghesi et al. 2019 remains unobtainable (OJS 404). Both need institutional
access.

**Note:** the protocol control introduces no new external methods — it reuses the study's own
pipeline — so it creates no new citation obligation, unlike the measure additions in round 01.
