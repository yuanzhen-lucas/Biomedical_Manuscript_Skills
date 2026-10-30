---
name: biomedical-literature-search
description: Plan, execute, document, or reproduce biomedical searches across public sources and user-provided database exports, retaining the exact query, source, date, limits, and retrieval status.
---

# Literature search workflow

## When to use
Use for PubMed, Europe PMC, Crossref, OpenAlex, ClinicalTrials.gov searches, search-strategy drafting, or importing searches from licensed databases.

## When not to use
Do not claim live access to Embase, Scopus, Web of Science, CENTRAL, CINAHL, or PsycINFO unless a user-authorized integration exists. Do not treat a search snippet as evidence.

## Required inputs
Search concepts or a research question, source/provider, date of execution, and desired record limit.

## Optional inputs
Controlled vocabulary, date/language/design filters, search history, database exports, and update-search dates.

## Workflow
1. Translate the question into concepts and synonyms; separate text words from controlled vocabulary.
2. Draft a database-specific query; do not assert sensitivity without testing.
3. Execute via a public provider or record the user-run licensed database search and import its export.
4. Preserve exact query, provider, timestamp, limit, result count, errors, and IDs.
5. Deduplicate conservatively; flag title matches for review rather than auto-merging.

## Dependencies
`biomedical-reference-manager`; public API adapters in `src/biomedical_manuscript/providers.py`.

## Scientific safeguards
Network errors are not zero results. Results remain unverified metadata until checked. Report source coverage and any inaccessible databases.

## Failure behavior
Report provider, rate-limit, parse, or authentication errors distinctly and keep the failed execution visible.

## Output contract
Return reproducible search record, result counts, source coverage, limitations, and import/deduplication actions.

## Verification steps
Re-run exact query/date/parameters where possible; reconcile provider totals to imported records and document changes.

## Human-review requirements
For systematic reviews, a qualified librarian/information specialist should review the strategy where feasible; authors confirm search scope and date.
