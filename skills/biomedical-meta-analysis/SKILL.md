---
name: biomedical-meta-analysis
description: Validate compatibility and compute reproducible generic inverse-variance fixed- or random-effects meta-analysis from study-level biomedical effect estimates or supported binary and continuous summary data.
---

# Meta-analysis workflow

## When to use
Use when studies report comparable outcomes and a quantitative synthesis is justified.

## When not to use
Do not pool incompatible populations, outcomes, estimands, effect measures, or directions without a justified prespecified harmonization.

## Required inputs
One independent effect estimate and standard error per study, common outcome identifier, effect measure, direction, and model choice.

## Optional inputs
Binary 2×2 counts, continuous group summaries, continuity correction rationale, sensitivity analyses, subgroup plan, and protocol.

## Workflow
1. Verify study independence, outcome compatibility, effect scale/direction, and input provenance.
2. Resolve zero cells explicitly; no continuity correction is automatic.
3. Run the documented generic inverse-variance model and preserve every input/parameter.
4. Review Q, tau-squared, I-squared, confidence interval, and approximate prediction interval where available.
5. Generate a forest plot only from the computed result and label model/scale.

## Dependencies
`src/biomedical_manuscript/meta.py`; CLI accepts JSON study effects.

## Scientific safeguards
Pooling is not justified by software acceptance. Statistical significance is not clinical importance. Funnel asymmetry is not proof of publication bias.

## Failure behavior
Reject incompatible or malformed inputs with an explicit reason; surface heterogeneity and model assumptions.

## Output contract
Study effects/weights, pooled estimate, uncertainty, heterogeneity, estimator, warnings, input provenance, and reproducible output.

## Verification steps
Check independent benchmark values, transformations, effect direction, study membership, and results against a validated implementation when used for publication.

## Human-review requirements
A qualified statistician/reviewer confirms model suitability, clinical interpretation, sensitivity analyses, and reporting.
