---
name: biomedical-peer-review
description: Critically review a biomedical manuscript or prepare a transparent response to reviewer comments, checking design, evidence, statistics, reporting, interpretation, and claimed revisions.
---

# Peer-review workflow

## When to use
Use for structured scientific review of a paper or response-to-reviewers preparation.

## When not to use
Do not process confidential submitted manuscripts with an external AI service unless the applicable journal/editor and authors explicitly permit it and data handling is assured.

## Required inputs
Manuscript text, review stage, and task (review or revision response).

## Optional inputs
Protocol, supplementary data/code, reviewer comments, target journal policy, and prior versions.

## Workflow
1. Identify confidentiality constraints and review instructions.
2. Assess novelty/scope only against inspected sources; examine methods, results, uncertainty, and limitations.
3. Separate major concerns from minor edits and reporting items from validity concerns.
4. For responses, map each comment to an author-verified action, location, and evidence of change.
5. Use placeholders where work/action is not confirmed; maintain version history.

## Dependencies
Statistical-review, claim-audit, reporting-guideline, and submission skills.

## Scientific safeguards
Never claim an experiment or analysis occurred unless the author confirms it. AI does not become an independent human reviewer.

## Failure behavior
Return a confidentiality or evidence limitation and restrict the review to allowed materials.

## Output contract
Structured review findings or comment-response matrix with priority, evidence, action, location, status, and unresolved items.

## Verification steps
Confirm cited manuscript sections and source findings; verify each revision claim against the revised manuscript/diff.

## Human-review requirements
The named reviewer/author owns judgments and approves all responses; editor/journal rules prevail.
