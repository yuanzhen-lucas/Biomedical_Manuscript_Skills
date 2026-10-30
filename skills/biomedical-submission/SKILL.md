---
name: biomedical-submission
description: Prepare a biomedical manuscript for a specified journal by verifying current author instructions, reporting checklists, disclosures, cover-letter content, revision history, and final human-approval gates.
---

# Submission workflow

## When to use
Use for journal-specific formatting/readiness checks, cover-letter drafting, AI-use disclosures, or final file/checklist preparation.

## When not to use
Do not present a manuscript as submitted or submission-ready without verified instructions and explicit author approval. Do not transmit confidential files automatically.

## Required inputs
Target journal and manuscript version; author-confirmed ethics, consent, funding, COI, data, registration, and contributions where applicable.

## Optional inputs
Author instructions URL, checklist, cover-letter requirements, reviewer responses, and AI-use record.

## Workflow
1. Retrieve and date-stamp the journal's current official instructions.
2. Check article type, length, abstract, references, figures, supplements, reporting checklist, disclosures, and file format.
3. Draft cover letter and AI-use disclosure only from author-confirmed facts.
4. Validate response-to-reviewer claims against actual revision files.
5. Run claim, statistical, reporting, and consistency checks.
6. Require explicit human approval and leave any external transfer to a separately authorized user action.

## Dependencies
Peer-review, reporting-guideline, scientific-editing, and local audit commands.

## Scientific safeguards
Journal rules change. Never invent missing declarations or describe a checklist as proof of validity.

## Failure behavior
If instructions cannot be verified, return the outstanding requirement and mark readiness as blocked/not ready.

## Output contract
Source-dated checklist, unresolved findings, cover-letter/disclosure drafts, version/diff summary, and approval state.

## Verification steps
Open the current journal source, compare every requirement against the files, and check all author-supplied declarations.

## Human-review requirements
Corresponding author confirms all statements, policy fit, author agreement, final files, and submission action.
