---
name: biomedical-manuscript
description: Orchestrate evidence-grounded biomedical manuscript work across original research, narrative or systematic reviews, meta-analysis, revision, and submission; choose only the necessary specialist workflow and preserve source traceability.
---

# Biomedical manuscript orchestrator

## When to use
Use when a researcher asks for end-to-end help, does not know which specialist workflow applies, or needs manuscript state and quality gates coordinated.

## When not to use
Use a specialist skill directly for a bounded task. Do not treat this skill as an automatic paper generator or as a substitute for a statistician, librarian, clinician, ethics body, or author.

## Required inputs
Manuscript or project materials available to the user, task goal, study/review type if known, and the intended output. Preserve unknown values as unknown.

## Optional inputs
Research question, protocol, dataset/code outputs, references, journal instructions, prior decisions, reporting guideline, and privacy constraints.

## Workflow
1. Classify work: original research, narrative review, systematic/scoping review, meta-analysis, editing, audit, peer review, or submission.
2. Identify project state and inspect existing evidence, provenance, unresolved fields, and confidentiality restrictions.
3. Route only to relevant skills under `skills/`; avoid loading unrelated materials.
4. Keep reference identity, evidence strength, verification depth, reporting completeness, statistical validity, and human interpretation distinct.
5. Record missing information, conflicts, and required human decisions before drafting.
6. Run the applicable audits and return a traceable output plus unresolved items.

## Dependencies
Specialist skills in this directory; optional local `biomed` CLI and SQLite project database. Network access is provider-specific and never assumed.

## Scientific safeguards
Never invent references, data, methods, results, registrations, ethics approvals, disclosures, or completed work. A real DOI is not proof of claim support. Abstract-only sources cannot be labeled full-text verified. Reporting compliance is not study quality.

## Failure behavior
Stop the affected inference when inputs are missing, contradictory, or unverifiable. State what was inspected and the next evidence needed. Do not silently substitute assumptions.

## Output contract
Give workflow classification, files/materials inspected, evidence and verification state, findings, unresolved items, and next human action. Label machine-generated checks as triage.

## Verification steps
Check all substantive claims against mapped sources/data; check numbers across sections; check the applicable live guideline and journal instructions; check provenance and unresolved markers.

## Human-review requirements
Named author/researcher approval is required for scientific interpretation, final claims, ethics/disclosure statements, systematic-review adjudication, and submission readiness.
