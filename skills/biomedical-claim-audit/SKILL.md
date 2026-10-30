---
name: biomedical-claim-audit
description: Audit biomedical manuscript claims for source traceability, evidence location, verification depth, study-design fit, contradictory evidence, uncertainty, causal overreach, and preclinical-to-human escalation.
---

# Claim audit workflow

## When to use
Use for manuscript claims, abstract conclusions, evidence tables, or claim-source mappings.

## When not to use
Do not treat lexical triggers or a reference's existence as semantic proof that it supports a statement.

## Required inputs
Claims/text, cited sources or data, study design/model level, and available source-access state.

## Optional inputs
Claim type, section, evidence locations, directness, limitations, contradictions, and appraisal.

## Workflow
1. Split compound sentences into auditable claims.
2. Link each claim to source/data records and specific locations.
3. Check identity verification separately from abstract/full-text access and human interpretation.
4. Compare claim type, population/model, study design, effect, uncertainty, and directness.
5. Find contradictory evidence, causal overclaim, negative-result misreading, and unsupported translation.
6. Use the CLI heuristic audit only for triage; record human status separately.

## Dependencies
Evidence synthesis, paper reader, and `biomed audit`.

## Scientific safeguards
Do not collapse support into a numeric confidence score. A DOI, P value, or checklist does not prove a claim.

## Failure behavior
Classify unsupported, conflicting, abstract-only, or inaccessible evidence explicitly; preserve missingness.

## Output contract
Claim matrix and finding-level reason, source/locator, verification depth, counterevidence, and human review state.

## Verification steps
Open the cited evidence and confirm source population, outcome, design, result, limitations, and wording alignment.

## Human-review requirements
Expert interpretation and final claim approval are required.
