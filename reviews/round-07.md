# Round 07 — FINAL round. Review of `paper/paper.pdf` (18 pp.)

**Conflict:** reviewer is the author. **Access:** extracted text; figures re-rendered from source.

## Recommendation: Accept with minor revision

Round 07 had one queued item and produced no new findings beyond it. **Stop condition met.**

## Applied

**The Fano construction is now cited, and the citation is honest about what was read.**
Round 06 used the entropy-rate + Fano construction without citing its origin, and deliberately
did not add a citation because the source had not been obtained.

- **Song et al. 2010** (*Science*) is the origin. **Paywalled, no OA location advertised by
  OpenAlex, not read.** Cited for the definition only, consistent with the four other
  definition-only citations in this bibliography.
- **Lu et al. 2013** (*Sci Rep*) **was obtained and read.** It applies the same construction and
  states, in its own results section, that *"the largest prediction accuracy that can be achieved
  with properly designed predictive algorithms is not given directly by this measure"* — a
  published caveat matching the one round 06 derived independently. Now cited at exactly that
  point, which converts our observation from an isolated anomaly into the sharper case of a known
  limitation.

Two further sources were attempted and refused: the MDPI *Entropy* 2019 review (HTML interstitial,
no PDF) and, for the third time, the AAAI version of record for Borghesi et al. 2019 (OJS non-PDF,
CDN 403).

## No new findings

Both skills were run against the current PDF. The reviewer found no unsupported claim, no stale
number, and no missing architecture element: the pipeline, hyperparameters, failure modes,
ablations, and complexity are all now present as tables. The auditor found no wrong paper, no wrong
author name, and no unsupported claim across 14 entries.

**Per the loop's stop rule, this is the final round.**

## Reference audit — final state

Bibliography: **14 entries. 6 read in full**, 8 definition-only and paywalled.

| read in full | cited for |
|---|---|
| Borghesi et al. 2023 (ExaData) | the dataset; the 15-min aggregation; the aggregation caveat |
| Lubba et al. 2019 (catch22) | feature-based characterisation precedent |
| Zeng et al. 2023 | simple models beating heavy ones |
| Borghesi et al. 2019 | what this telemetry is normally used for |
| Truong et al. 2020 | changepoint detection by binary segmentation |
| **Lu et al. 2013** | **the Fano bound does not give achievable accuracy** |

Definition-only and unread (all paywalled, none attributed a finding): Hyndman & Koehler, Bandt &
Pompe, Peng et al., Assimakopoulos & Nikolopoulos, Richman & Moorman, Dickey & Fuller, Kwiatkowski
et al., Song et al.

**Remaining and not fixable here:** three entries cite a version of record while a preprint was
read (catch22, Zeng, Borghesi 2019); the AAAI PDF is unobtainable after three attempts. Both need
institutional access.
