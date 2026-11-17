# Retrospective surrogate evidence audit

All arithmetic and saved-file consistency checks pass. This audit had access to final outputs and labels; it is not another blinded evaluation.

## Recalculated results

| Stage | Alias | Candidate | Repeat | TP | TN | FP | FN | Correct | Description characters |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| development | K | v0 | — | 12 | 12 | 0 | 0 | 24/24 | 175 |
| development | R | v3 | — | 12 | 12 | 0 | 0 | 24/24 | 623 |
| development | M | v2 | — | 12 | 12 | 0 | 0 | 24/24 | 505 |
| development | T | v1 | — | 12 | 12 | 0 | 0 | 24/24 | 176 |
| development | U | v4 | — | 12 | 12 | 0 | 0 | 24/24 | 155 |
| holdout | A | v4 | 2 | 12 | 12 | 0 | 0 | 24/24 | 155 |
| holdout | B | v0 | 0 | 12 | 12 | 0 | 0 | 24/24 | 175 |
| holdout | C | v0 | 2 | 12 | 12 | 0 | 0 | 24/24 | 175 |
| holdout | D | v4 | 1 | 12 | 12 | 0 | 0 | 24/24 | 155 |
| holdout | E | v4 | 0 | 12 | 12 | 0 | 0 | 24/24 | 155 |
| holdout | F | v0 | 1 | 12 | 12 | 0 | 0 | 24/24 | 175 |

Character lengths use Python Unicode code-point counts, not tokens or bytes. v4 saves 20/175 = 11.43% against v0. All 11 outputs contain exactly 24 unique boolean decisions, with no missing, unexpected, or duplicate IDs.

## Integrity and selection

Development and holdout each contain 12 positives and 12 negatives. Holdout has 12 English and 12 Chinese queries, with six of each language per class. Queries are unique within each set, with no exact overlap between sets. Every evaluation input reproduces its respective queries exactly; holdout input order changes without changing identity or content. Candidate descriptions match their maps. The six holdout runs map to v0 and v4, repeats 0, 1, and 2 once each.

Raw `holdout.json` SHA256 matches `selection-protocol.json`: `f509ffc67c3088025e87047ca8194ac11b9d65f361a1f142ceb63f5a2a3522a2`. The numbered labels reproduce the same ordered queries and labels. Stored development summaries and v4 score match independent recalculation and the supplied scorer.

The 155-character proposal meets the 175-character baseline budget and the recorded development qualification/tie-break. Its wording preserves the workflow and continuation scope and limits mixed CAD/preview work to photo-body fitting. Selection explicitly keeps the proxy candidate separate from the installed-description claim.

## Limits and defensible conclusions

- All five development candidates and both holdout candidates saturate this explicit routing surrogate. No observed accuracy gain distinguishes v4 from v0.
- This is retrospective arithmetic/file-consistency auditing after outputs and labels are known; it is not a new blinded evaluation.
- The protocol states one model family. Distinct routing agents are repeated runs, not evidence of model diversity or proven statistical independence; model identities, sampling settings, and actual call logs are absent from the permitted artifacts.
- Explicit prompted trigger booleans and reasons are metadata judgments, not observed native Skill/Read routing events. No native trigger accuracy or end-to-end image/body-fitting quality follows.
- Each candidate has three evaluations of the same 24 holdout queries. 72 decisions per candidate are 24 distinct items with repeats, not 72 independent holdout samples. Six runs together are 144 judgments on 24 distinct items.
- The saved hash confirms current holdout bytes match the protocol commitment. Without append-only timestamps or execution/access logs it cannot prove registration preceded every evaluation, absence of tuning after opening, or lack of data access.
- Inputs omit labels and candidate/repeat identities. Sealed-directory instructions and claimed optimizer access restrictions establish intended blinding, not a security boundary; common workspace access means isolation cannot be independently guaranteed from these files.
- Small manually constructed, balanced English/Chinese boundary cases share task-contract semantics with development. Zero exact query overlap establishes literal novelty only, not representative production coverage or semantic independence.
- The v4 text covers six independent reference outputs, adjustable body fitting, render/OpenCV checks, parameter provenance, continuations/audits/slider-mesh-export repair, and mixed CAD/preview only when photo-body fitting is included. It lists broad exclusions without development IDs, filenames, or enumerated cases. This is a content judgment, not execution validation.
- Selection reports v0 retained and no native best candidate; the installed skill itself is outside the permitted audit inputs, so installation state is not independently verified.

Observed explicit routing correctness ties at 24/24 in every run. v4 is 155 versus baseline 175 Unicode code points (20 fewer; 11.43% shorter). It qualifies for the proxy shortlist by the registered tie-break, without evidence of improved accuracy, native routing performance, or task execution quality.

Machine-readable detail: `audit.json` (68 checks; 0 failures).
