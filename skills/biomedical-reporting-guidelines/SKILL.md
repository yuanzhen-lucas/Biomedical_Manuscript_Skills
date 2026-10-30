---
name: biomedical-reporting-guidelines
description: Select and audit the current reporting guideline for a biomedical study design or review type, recording source version and checklist completeness separately from methodological quality.
---

# Reporting guideline workflow

## When to use
Use to select a guideline, prepare a reporting checklist, or audit reporting completeness.

## When not to use
Do not use reporting compliance as evidence of good design, low bias, statistical validity, or trustworthy conclusions.

## Required inputs
Study design/review type, manuscript/protocol version, and journal if known.

## Optional inputs
Specialty, population/model, guideline extension, checklist status, and journal instructions.

## Workflow
1. Route via `guidelines/registry.yaml` and EQUATOR discovery.
2. Open the official guideline source and journal instructions; confirm exact version and any extension.
3. Record item statuses as addressed, partial, not addressed, not applicable, or not assessed.
4. Point to manuscript locations and unresolved reporting items.
5. Keep reporting, methodology/risk of bias, statistics, and claim validity as separate audits.

## Dependencies
Version-aware registry, `biomed guidelines route|audit`, and official linked pages.

## Scientific safeguards
Do not reproduce checklist text beyond the source license; do not imply checklist completeness validates the science.

## Failure behavior
If version/currentness is uncertain, label the entry as unverified and ask for or retrieve the source before final audit.

## Output contract
Selected guideline/version/source, checklist status and locations, reporting gaps, and explicit separate quality-audit status.

## Verification steps
Confirm official source and journal requirements as of the review date; reconcile each item manually.

## Human-review requirements
Authors confirm applicability, item interpretation, and final checklist.
