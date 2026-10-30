---
name: biomedical-systematic-review
description: Plan and track a protocol-driven biomedical systematic or scoping review, including reproducible searches, deduplication, screening decisions, exclusion reasons, extraction, PRISMA counts, and human-review requirements.
---

# Systematic review workflow

## When to use
Use for protocol-based systematic/scoping reviews, screening records, PRISMA flow state, or structured extraction planning.

## When not to use
Do not use for unsystematic topic overviews or to invent search totals, registration IDs, reviewer decisions, or exclusions.

## Required inputs
Question, explicit eligibility criteria, source set/searches, screening stage, and reviewer identity for decisions.

## Optional inputs
Protocol/registration, duplicate report links, extraction form, risk-of-bias method, certainty framework, and update date.

## Workflow
1. Freeze/version protocol, outcomes, eligibility, and conflict-resolution plan before screening.
2. Import exact database exports and record source-specific queries/dates.
3. Deduplicate by identifiers; adjudicate uncertain matches manually.
4. Record per-reviewer title/abstract and full-text decisions; record a controlled full-text exclusion reason.
5. Surface disagreements and AI-only screening explicitly; do not call AI an independent human reviewer.
6. Derive flow counts only from stored records and report missing acquisition totals as unknown.

## Dependencies
Literature-search, reference-manager, paper-reader; local `biomed screen` and `biomed systematic flow` commands.

## Scientific safeguards
Never fabricate PROSPERO IDs or counts. Distinguish reports, records, and studies. AI screening does not replace required human review.

## Failure behavior
If counts do not reconcile or decisions conflict, return unresolved records; do not generate a finished PRISMA diagram.

## Output contract
Versioned protocol state, search records, decisions, reasons, unresolved conflicts, derived counts, and methods limitations.

## Verification steps
Reconcile identification/import totals, duplicates, decisions, retrieval status, exclusion reasons, and included study/report linkage.

## Human-review requirements
Appropriate human reviewers perform or verify screening, extraction, risk-of-bias judgments, and adjudication.
