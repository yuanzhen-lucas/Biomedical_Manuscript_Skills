# Evidence model

## Entities

Typed, versioned models cover projects and questions; manuscript projects, sections, and statements; search strategies, executions, and results; references; source access and documents; studies, populations, exposures, and outcomes; evidence extracts; claims and claim-source links; risk-of-bias and certainty assessments; reporting guidelines/checklists/assessments; audit findings; human approvals; and provenance events.

The local SQLite implementation currently persists references, searches/results, documents, evidence, claims/links, screening decisions, appraisals, systematic-review protocols, and provenance. Remaining typed entities are available as models for incremental persistence work.

## Verification depth

| Level | Recorded work | Evidence needed |
|---|---|---|
| L0 | Discovered/imported, not independently verified | None |
| L1 | Bibliographic identity checked | DOI resolution and title comparison |
| L2 | Abstract content checked | Stored abstract and explicit reviewer attestation |
| L3 | Relevant full text checked | Stored extracted full text, reviewer attestation, and locator |
| L4 | Human scientific interpretation reviewed | L3 plus separate human approval on the claim-source link |

These levels measure verification depth, not study quality, certainty, or claim support. A reference may resolve to a real article while being irrelevant to a claim.

## Claims and links

Each substantive statement should be decomposed into claim-sized units. A link records support direction (`supports`, `partially_supports`, `contradicts`, `mixed`, `unclear`, or `not_applicable`), source ID, verification depth, directness, limitations, and location. Link creation does not semantically validate the assigned direction. The claim remains unverified until a human checks the source and the claim in context.

## Missingness and contradiction

Unknown information is retained as null or an explicit marker such as `[DATA REQUIRED]`, `[SOURCE NEEDED]`, or `[AUTHOR CONFIRMATION REQUIRED]`. Contradictory sources remain separate links and are not averaged into one opaque confidence score.

## Provenance

The store records search success/failure, reference imports and reconciliations, source ingestion, extraction, claim creation/linkage, screening decisions, appraisals, protocol versions, and reference attestations. The database preserves local project text and search queries; protect it as confidential research material.
