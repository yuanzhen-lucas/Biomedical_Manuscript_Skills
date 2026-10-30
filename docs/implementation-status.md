# Implementation status

Status as of 2026-10-30. “Implemented” applies only to the listed, tested scope. It does not mean every capability in the development brief is complete.

## Phase summary

| Phase | Status | Implemented location | Validation | Known limits |
|---|---|---|---|---|
| 1. Literature/evidence foundation | **Partial, runnable core** | `src/biomedical_manuscript/{providers,references,documents,evidence,store,models}.py`; `biomed` CLI | Provider contracts are mocked; import, duplicate, verification-depth, failure/zero-result, and local-store tests | No live API certification; no full-text resolver; some provider-specific correction/retraction coverage is incomplete; no migration framework. |
| 2. Original research/narrative review | **Partial** | Skills; `audits.py`; claim matrix; templates; versioned manuscript sections in `store.py` and CLI | Rule-based adverse cases, number comparison, immutable section revisions with hashes and diffs | No data-driven manuscript compiler, semantic claim verification, or complete table/figure reconciliation. |
| 3. Systematic review/meta-analysis | **Partial** | `systematic.py`, `appraisal.py`, `meta.py`, SQLite protocol/decision/study-report/appraisal state | Derived flow, conflict, AI-screening, multi-report study-count and exclusion-reason tests; hand-derived statistical golden values | No full extraction database/forms, validated instrument implementation, advanced meta-analysis, or independent external package comparison in CI. |
| 4. Submission QC | **Partial** | `reporting.py`, `submission.py`, version registry, reviewer-response and audit CLI | Registry routing, checklist-status and final human/source gate tests | Journal requirements are not automatically retrieved; no submission/upload integration or full revision manager. |

## Skills

All 16 requested skills have non-placeholder `SKILL.md` workflows and are validated for metadata plus required sections. They guide researcher/model behavior; instructions alone are not counted as implemented software capability.

## Providers

PubMed/NCBI E-utilities, Europe PMC, Crossref, OpenAlex, and ClinicalTrials.gov have standard-library HTTP adapters. RIS, NBIB, BibTeX, CSV, generic/Crossref-style JSON, and PubMed XML reference imports are implemented. PDF extraction is optional via `pypdf`; plain text/Markdown/HTML/XML documents are read locally. Embase, Scopus, Web of Science, CENTRAL, CINAHL, and PsycINFO require a user-generated export/search log.

## Reporting guidelines

Registry includes CONSORT 2025, SPIRIT 2025, STROBE and STROBE-EPIC 2026, PRISMA 2020, PRISMA-S, PRISMA-ScR, PRISMA-P, PRISMA-C 2026, ARRIVE 2.0, CARE, STARD, STARD-AI discovery, TRIPOD+AI, TRIPOD-LLM 2025, RECORD, STREGA, CHEERS, COREQ, SRQR, and MOOSE. Each use must verify current official source/journal policy. Audits only store item statuses; they do not semantically assess checklist items.

## Statistical methods

Implemented: generic inverse-variance fixed effect; DerSimonian–Laird random effects; pooled estimate/SE/normal CI; Q, tau-squared, I-squared; approximate normal prediction interval for at least three studies; binary log-OR calculation with explicit correction requirement; continuous mean difference; and forest SVG.

Not implemented: general pairwise/arm-level meta-analysis orchestration, standardized mean differences, Mantel–Haenszel/Peto/GLMM models, REML/Paule–Mandel estimators, multi-arm/correlated-effects models, subgroup/meta-regression, influence/sensitivity analysis, funnel plots, or publication-bias tests.

## Test status

Last run: `python scripts/validate.py` — **63 offline checks passed**. Tests mock HTTP calls. No live source/provider or real-manuscript validation has been run.

## External dependencies and human review

Core runtime uses Python 3.11+ standard library. Optional `pypdf` supports PDF text extraction; optional dev extras provide `pytest`/`ruff`. Human scientific interpretation, screening, risk-of-bias and certainty judgments, authorship/disclosures, journal policy verification, and final submission approval remain required.
