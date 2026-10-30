---
name: biomedical-statistical-review
description: Review biomedical statistical methods, assumptions, model reporting, uncertainty, multiplicity, missing data, subgroup claims, effect interpretation, and reproducibility using supplied analysis outputs.
---

# Statistical review workflow

## When to use
Use to audit statistical plans, code/output, results sections, and interpretations.

## When not to use
Do not use as a substitute for re-running an analysis when data/code are unavailable or as a stand-alone clinical decision tool.

## Required inputs
Study design, outcome definitions, analysis plan/methods, and reported result or output.

## Optional inputs
Raw/derived data, code, assumptions, missingness, multiplicity plan, software/version, and protocol/SAP.

## Workflow
1. Match estimand, design, sampling, clustering, repeated measures, and model.
2. Check denominators, missing data, assumptions, effect estimates, intervals, P values, and multiplicity.
3. Distinguish statistical from clinical importance and null evidence from evidence of no effect.
4. Check subgroup, interaction, causal, and prediction claims against design and prespecification.
5. Report issues as questions/risks with reproducibility steps.

## Dependencies
Study-design and evidence model references; optional meta-analysis engine for supported models.

## Scientific safeguards
Do not recompute from rounded prose if source data are needed. Do not label a method invalid solely from a heuristic.

## Failure behavior
Identify unavailable inputs and limit conclusions to the supplied methods/results.

## Output contract
Structured finding, evidence/section, severity, rationale, and requested correction or data.

## Verification steps
Recalculate selected values from raw data/code or independently validated outputs where feasible.

## Human-review requirements
Statistician of record or qualified reviewer adjudicates substantive methods and model choices.
