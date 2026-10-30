---
name: biomedical-reference-manager
description: Import, normalize, deduplicate, and verify biomedical references from DOI, PMID, RIS, NBIB, BibTeX, CSV, or public metadata providers while preserving conflicting metadata and verification depth.
---

# Reference management workflow

## When to use
Use when cleaning or validating a reference library or reconciling records from different databases.

## When not to use
Do not use a citation formatter as proof of source identity, claim support, or evidence quality.

## Required inputs
Reference records or a bibliography export and the project database/location if persistence is needed.

## Optional inputs
Expected title, author/year, DOI, PMID/PMCID, source database, and correction/retraction context.

## Workflow
1. Import RIS, NBIB, BibTeX, CSV, or provider results.
2. Normalize DOI/PMID and preserve original provider metadata and conflicts.
3. Deduplicate exact identifiers; leave title/year collisions as candidates for a human.
4. Resolve DOI identity using Crossref and compare the resolved title with the supplied title.
5. Record only the verification level actually completed; search-result presence is L0.

## Dependencies
Public Crossref API for online DOI resolution; local parser and SQLite store for offline work.

## Scientific safeguards
L0–L4 describe verification depth, not study quality. A verified DOI does not validate a linked claim. Preserve retraction/correction notices and version relationships.

## Failure behavior
Malformed or unresolved identifiers remain L0 with a reason; provider errors remain errors, not rejection as nonexistent.

## Output contract
Return normalized record, identifier resolution, metadata conflicts, duplicate candidates, and verification depth.

## Verification steps
Check title, authors, year, journal, DOI/PMID, publication status, and source-specific URL against the returned record.

## Human-review requirements
Humans adjudicate uncertain duplicates, preprint/final versions, corrections, and whether an article is appropriate for a particular claim.
