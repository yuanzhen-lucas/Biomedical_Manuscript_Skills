# Validation

Run the complete offline validation command from the repository root:

```bash
python scripts/validate.py
```

It validates skill front matter and workflow sections, checks the guideline registry structure, compiles Python modules, and runs unit, integration, adversarial, parser, provider-contract, serialization/provenance, and statistical golden tests. Tests mock network calls. The command does not contact external APIs, run live journal/guideline checks, check PDF extraction unless the optional dependency is installed, or validate a real manuscript.

Optional tools are declared in the `dev` extra: `ruff` and `pytest`. They are not required for the offline validation script. Provider live checks should be an explicit user action, not part of CI.

The CLI parser can be checked without initializing a database using `PYTHONPATH=src python -m biomedical_manuscript --help`. Editable installation uses `python -m pip install -e .` when local packaging dependencies are available.

## Current statistical test fixtures

The generic inverse-variance golden fixture uses two study effects `(0.2, SE 0.1)` and `(0.5, SE 0.2)`. Independent hand calculation gives fixed-effect mean `0.26`, SE `sqrt(1/125)`, Q `1.8`; DerSimonian–Laird gives tau-squared `0.02`, random-effects mean `0.30`, SE `sqrt(0.02)`, and I-squared `44.44%`. Tolerance in tests is 1e-10 for the core calculations. Binary log-OR and continuous mean-difference transforms have separate arithmetic fixtures. These checks do not validate all clinical meta-analysis estimators or replace comparison against a validated statistical package for publication.
