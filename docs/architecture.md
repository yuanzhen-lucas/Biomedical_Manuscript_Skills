# Architecture

## Design

The repository separates four layers:

1. **Discoverable skills** under `skills/` route user work and state scientific safeguards.
2. **Local evidence infrastructure** under `src/biomedical_manuscript/` stores versioned records, provider results, source-access state, claim links, review decisions, appraisals, and provenance in SQLite.
3. **Source registry and reference material** under `guidelines/` and `references/` support progressive disclosure and version-aware routing.
4. **Validation and documentation** under `tests/`, `scripts/`, `docs/`, and `.github/workflows/` describe tested behavior and its limits.

The CLI is a local user-operated interface. Public provider adapters fetch metadata only. Full text is read only from a path explicitly supplied by the user. No model API or manuscript upload is integrated.

## Data flow

```text
Question → query + execution record → normalized reference → verified source
        → located evidence → claim ↔ source links → audits → human approval
```

The library records source identity verification separately from abstract/full-text access and scientific interpretation. Links record assigned support direction but do not semantically prove that a source supports a claim.

## Storage and schema

SQLite schema version `1.0` is initialized locally. Records include their schema version where applicable. Provenance events are append-only; current reference metadata can be reconciled while preserving incoming variants and field conflicts. Schema migrations are not yet implemented; unknown schema versions must be handled as migration work rather than silently rewritten.

Databases are created with restrictive file permissions where the platform permits. The store does not encrypt content. Local storage still requires appropriate device, backup, and access controls.

## Provider boundaries

PubMed/NCBI E-utilities, Europe PMC, Crossref, OpenAlex, and ClinicalTrials.gov adapters use public HTTP APIs. Error classes distinguish network failures, provider failures, rate limits, malformed responses, and input validation. A failed request is recorded separately from a completed search with zero results. Licensed databases are supported through user-run exports and saved search descriptions; no subscription entitlement is implied.

## Statistical boundary

The meta-analysis module implements generic inverse-variance pooling, fixed effect, DerSimonian–Laird random effects, Q, I-squared, tau-squared, normal-theory confidence intervals, an explicitly approximate prediction interval, binary log-odds-ratio transformations, continuous mean differences, and SVG forest plots. It does not provide a complete meta-analysis platform or validate whether pooling is scientifically justified.

## Skill discovery

Each skill has a concise `SKILL.md` with the Agent Skills-compatible `name` and `description` front matter and progressive-disclosure support material. Codex's current skills documentation describes skills as folders with a `SKILL.md`, metadata, workflow instructions, and optional references/scripts/assets: <https://developers.openai.com/plugins/concepts/skills>.
