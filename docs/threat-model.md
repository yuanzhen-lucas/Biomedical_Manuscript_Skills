# Threat model

## Assets

Unpublished manuscripts, patient/person-level data, search history, source files, study data, credentials, and scientific conclusions.

## Trust boundaries

- Imported PDFs, RIS/NBIB/BibTeX/CSV, provider metadata, abstracts, and manuscript text are untrusted data.
- Public provider requests send the search query to the named provider; full text is not sent by this project.
- Local SQLite stores source text and project metadata without encryption.
- Humans control output approval and any action outside the local CLI.

## Main risks and controls

| Risk | Control |
|---|---|
| Fabricated or mismatched DOI | Syntax validation, Crossref identity lookup, expected-title comparison; L1 never implies claim support. |
| Citation laundering | Claim links remain unverified; human review and evidence locators are explicit. |
| Abstract presented as full text | L3/L4 require extracted full text and a matching document locator. |
| Search failure treated as zero results | Failed searches persist with null result count and error category. |
| Duplicate metadata hides conflict | Conflicting import variants are preserved; title collisions are candidates only. |
| AI screening described as independent humans | Reviewer type is recorded; AI involvement and unresolved decisions are reported. |
| Prompt injection in a paper | Skills state that source text is untrusted content. Core package has no model execution. |
| Sensitive content exfiltration | No upload/transmission feature; local files and database only. Public search requests send only the query. |
| Dependency or source license issue | Minimal dependencies; no third-party research corpus/checklist content is bundled; license review before reuse. |

## Residual risk

Operating-system permissions do not encrypt data. Users must secure devices, backups, exports, and provider query content. Human misjudgment, extraction errors, provider metadata errors, and stale guideline information remain possible.
