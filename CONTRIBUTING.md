# Contributing

Contributions should improve evidence traceability, scientific safeguards, usability, or tested workflow behavior.

## Development

1. Use Python 3.11 or later.
2. Keep runtime dependencies minimal and do not add copyrighted article or checklist content.
3. Add or update tests for behavior changes, including adversarial cases where appropriate.
4. Run `python scripts/validate.py` from the repository root.
5. Update `docs/implementation-status.md`, `docs/limitations.md`, and the changelog when capability status or limitations change.

## Scientific behavior

Do not fabricate or silently impute scientific facts. Preserve unknowns and contradictory evidence. Keep source identity, evidence strength, reporting completeness, and methodological validity separate. Rule-based flags must be described as triage unless a validated method supports stronger claims.

## Provider and privacy changes

Document what data is sent to a provider, authentication needs, quota behavior, error classes, and offline fixtures. Do not transmit manuscripts, patient data, or unpublished text implicitly. Live API tests must be opt-in and must not make normal CI network-dependent.

## License and attribution

Original contributions are licensed under Apache-2.0. Do not copy code, prompts, guideline checklist wording, or assets from third-party projects without verifying file-level terms and preserving required attribution.
