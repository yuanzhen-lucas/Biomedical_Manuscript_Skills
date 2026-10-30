# Limitations

- No automated system can guarantee manuscript correctness or scientific validity.
- Public database coverage, API metadata, indexing, and update timing may be incomplete; licensed databases require user access and exports.
- Full-text access may be limited. PDF text extraction can lose layout, tables, equations, and reading order; OCR is not implemented.
- Evidence appraisal, directness, causal interpretation, risk of bias, certainty, and clinical importance require domain expertise.
- The risk-of-bias and certainty module records human judgments; it does not implement a complete validated instrument or calculate ratings.
- Statistical automation is limited to specified methods and needs independent validation before publication use. The prediction interval uses a normal approximation, does not fully represent small-k uncertainty, and advanced methods are not implemented.
- Journal requirements and guideline extensions change; the registry is a dated routing aid and each source must be checked before use.
- Reporting completeness is not methodological validity, low risk of bias, or statistical validity.
- Systematic-review automation does not remove the need for appropriate human screening, extraction, adjudication, and appraisal.
- AI-generated scientific text, if produced by an external system, requires author verification and applicable disclosure; this repository has no model generation endpoint.
- Local databases are not encrypted. Users are responsible for confidentiality, device security, backups, and retention.
- Bibliographic identity verification does not establish that a paper supports a specific claim.
- Search and claim audits are rules-based triage tools and can have false positives and false negatives.
- Source retrieval live tests are mocked in CI; external API availability, quota behavior, and current metadata are not validated by the offline test suite.
