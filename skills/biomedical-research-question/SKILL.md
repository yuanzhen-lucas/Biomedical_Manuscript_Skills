---
name: biomedical-research-question
description: Formulate or refine biomedical research questions, objectives, hypotheses, and eligibility concepts using PICO, PECO, PICOT, SPIDER, or another design-appropriate framework.
---

# Research question workflow

## When to use
Use when defining a biomedical question, objective, hypothesis, review scope, or eligibility framework before retrieval or analysis.

## When not to use
Do not use to select an intervention or make a clinical decision, or to retrofit hypotheses after seeing results without disclosure.

## Required inputs
Research domain, intended population or biological model, and the decision or knowledge gap the question should address.

## Optional inputs
Exposure/intervention, comparator, outcomes, timeframe, setting, study designs, feasibility constraints, and protocol.

## Workflow
1. Identify whether the aim is descriptive, associative, causal, diagnostic, prognostic, mechanistic, or evidence-synthesis.
2. Select a fitting framework; do not force PICO on questions for which it is unsuitable.
3. Define each concept and population/model level; separate primary from exploratory outcomes.
4. Identify estimand, timeframe, eligibility implications, and unresolved choices.
5. Save a versioned ResearchQuestion record and provenance when using the CLI.

## Dependencies
`references/study-designs.md`; optional `biomed` local project.

## Scientific safeguards
Keep hypothesis, objective, and post hoc interpretation distinct. Do not imply causal identifiability from question structure alone.

## Failure behavior
Return alternatives and missing decision fields when the question is under-specified; do not invent a population or outcome.

## Output contract
Provide structured question, framework and rationale, primary concepts/outcomes, design implications, and open decisions.

## Verification steps
Check population, exposure/intervention, comparator, outcome, and timeframe terms for ambiguity and consistency with the target design.

## Human-review requirements
The investigator approves scope, outcome priority, feasibility, and protocol wording.
