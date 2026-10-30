# Evidence-Centric Biomedical Writing

Biomedical Manuscript Skills is an open-source collection of 16 task-specific Skills and a local Python CLI for biomedical literature workflows, evidence synthesis, manuscript review, and submission preparation.

Repository names: Biomedical_Manuscript_Skills · biomedical-manuscript-skills.

## What’s included

- **Literature:** adapters for PubMed, Europe PMC, Crossref, OpenAlex, and ClinicalTrials.gov; reference import from RIS, NBIB, BibTeX, CSV, JSON, and PubMed XML.
- **Evidence records:** local SQLite storage for references, documents, extracted evidence, claims, claim–source links, verification depth, and provenance.
- **Manuscripts:** rule-based claim and consistency checks, versioned section revisions, and reporting-guideline routing.
- **Evidence synthesis:** review protocols, screening decisions, report-to-study links, flow counts, human-entered appraisal records, and a limited generic inverse-variance meta-analysis.
- **Submission support:** response-to-reviewer drafts and readiness checks for unresolved findings, journal-source verification, and human approval.

The CLI uses public metadata APIs for searches. Full-text files are selected and read locally. The project does not include a model-generation endpoint or manuscript-upload integration.

## Install

Install the Python package and initialize a local project database:

~~~bash
python -m pip install -e .
biomed init
~~~

This installs the local `biomed` command-line application. It does not install or register Skills in Codex or ChatGPT.

Install the Skills for all your local Codex projects:

~~~bash
mkdir -p ~/.agents/skills
ln -s "$PWD"/skills/biomedical-* ~/.agents/skills/
~~~

Run this from the repository root. Codex also supports repository-scoped Skills under .agents/skills; use that location if you only want them available in this project. The symlinks point to this checkout, so keep the repository in place or recreate them after moving it.

If a newly installed Skill does not appear in Codex, restart Codex and check its Skills selector.

### Install Skills in ChatGPT

Local Codex skill folders and the Python CLI installation do not sync to your ChatGPT account. Standalone skill folders are available in the ChatGPT desktop app; if Skills are available for your account or workspace, open **Skills** in the sidebar and use **Create → Upload from your computer** to upload the Skill you want. This repository contains 16 separate Skills; upload each one you want ChatGPT to use. Confirm it appears under **Installed**, then choose it from the `@` menu in a new chat.

For ChatGPT Chat or Work on the web or mobile, OpenAI documents Skills as available when bundled in a plugin. This repository includes the plugin manifests and icon needed to package all 16 skills. From the repository root, create the plugin archive:

~~~bash
zip -r /tmp/biomedical-manuscript-skills-plugin.zip plugin.json .codex-plugin assets/biomedical.svg skills
~~~

The archive has `.codex-plugin/plugin.json` and `skills/<skill-name>/SKILL.md` at its root. In ChatGPT, use **Plugins → Plugin Directory → Upload plugin** and choose the archive; after validation, install the plugin and select a skill with `@` in a new chat. The plugin's `websiteURL` points to this repository: <https://github.com/yuanzhen-lucas/Biomedical_Manuscript_Skills>. Product availability and workspace settings can affect which controls are shown; see [OpenAI's Skills in ChatGPT guide](https://help.openai.com/en/articles/20001066-skills-in-chatgpt) and [Build skills](https://learn.chatgpt.com/docs/build-skills).

For command syntax, run `biomed --help`. The Python interface requires Python 3.11 or later. PDF text extraction is optional and requires the `pdf` extra.

## Reporting and publication guidance

The registry records guideline editions and routing terms. Check the linked source and the target journal’s instructions before applying a checklist. The registry was reviewed on 2026-10-30; extensions and journal policies may change.

| Topic | Guideline and official source |
|---|---|
| Publication recommendations and AI use | [ICMJE Recommendations](https://www.icmje.org/recommendations/) |
| Guideline discovery | [EQUATOR Network](https://www.equator-network.org/reporting-guidelines/) |
| Randomized trials and protocols | [CONSORT 2025](https://www.consort-spirit.org/published-statements) · [SPIRIT 2025](https://www.consort-spirit.org/published-statements) |
| Observational studies | [STROBE](https://www.strobe-statement.org/) · [STROBE-EPIC 2026](https://equator-network.org/reporting-guidelines/strobe-epic/index.html) |
| Systematic reviews and search reporting | [PRISMA 2020](https://www.prisma-statement.org/prisma-2020) · [PRISMA-S](https://www.prisma-statement.org/prisma-search) · [PRISMA-P](https://www.prisma-statement.org/protocols) · [PRISMA-ScR](https://www.prisma-statement.org/scoping) · [PRISMA-C 2026](https://www.prisma-statement.org/children) |
| Animal research | [ARRIVE 2.0](https://arriveguidelines.org/arrive-guidelines) |
| Case reports | [CARE](https://www.care-statement.org/downloads) |
| Diagnostic accuracy | [STARD](https://www.equator-network.org/reporting-guidelines/stard/) · [STARD-AI](https://www.nature.com/articles/s41591-025-03953-8) |
| Prediction models and healthcare LLM studies | [TRIPOD+AI](https://www.tripod-statement.org/) · [TRIPOD-LLM](https://www.nature.com/articles/s41591-024-03425-5) |
| Routinely collected health data | [RECORD](https://www.record-statement.org/) |
| Genetic association studies | [STREGA](https://www.equator-network.org/reporting-guidelines/strega/) |
| Health economic evaluations | [CHEERS 2022](https://www.ispor.org/heor-resources/good-practices/cheers) |
| Qualitative research | [COREQ](https://www.equator-network.org/reporting-guidelines/coreq/) · [SRQR](https://www.equator-network.org/reporting-guidelines/srqr/) |
| Meta-analysis of observational studies | [MOOSE](https://www.equator-network.org/reporting-guidelines/moose/) |

Reporting checklist completion describes what is reported; it does not establish methodological quality, low risk of bias, or statistical validity.

## Examples

Run the four synthetic workflows from the repository root:

~~~bash
PYTHONPATH=src python examples/run_examples.py --output-dir /tmp/biomed-synthetic-examples
~~~

The script makes no provider requests. It writes a local SQLite database and the following reports:

| Workflow | Demonstration | Output |
|---|---|---|
| Original Research | Versioned draft, claim–source link, and manuscript triage | `original-research-audit.json` |
| Narrative Review | Evidence matrix retaining conflicting directions | `narrative-review-matrix.json` |
| Systematic Review | Saved protocol and screening records with derived flow counts | `systematic-review-flow.json` |
| Meta-analysis | Synthetic pooled estimate and forest plot | `meta-analysis-result.json`, `meta-analysis-forest.svg` |

All example records and effect estimates are synthetic. They are not publications or biomedical evidence and must not be cited. See [examples/README.md](examples/README.md) for details.

## Validation

From the repository root, run:

~~~bash
python scripts/validate.py
~~~

The command checks Skill metadata and required workflow sections, validates the guideline registry, compiles the Python package, and runs offline unit, integration, adversarial, provider-contract, import, provenance, and statistical golden tests. As of 2026-10-30, **63 checks pass**. Provider HTTP requests are mocked.

To inspect the CLI without creating a database, run `PYTHONPATH=src python -m biomedical_manuscript --help`. CI installs the package, checks `biomed --help`, and runs the validation script. Validation does not certify live provider behavior or validate real manuscripts. See [docs/validation.md](docs/validation.md) for test scope and statistical fixtures.

## Skills

The Skills are under `skills/` and can be used independently or through the `biomedical-manuscript` orchestrator:

**Core workflow:** `biomedical-manuscript`, `biomedical-research-question`, `biomedical-literature-search`, `biomedical-reference-manager`, `biomedical-paper-reader`, `biomedical-evidence-synthesis`.

**Writing and review:** `biomedical-original-article`, `biomedical-narrative-review`, `biomedical-systematic-review`, `biomedical-meta-analysis`, `biomedical-statistical-review`, `biomedical-scientific-editing`, `biomedical-claim-audit`, `biomedical-reporting-guidelines`, `biomedical-peer-review`, `biomedical-submission`.

Each Skill contains its own inputs, workflow, safeguards, failure behavior, and review requirements.

## Status and limitations

All four development phases are partial. See [docs/implementation-status.md](docs/implementation-status.md) for implemented scope, tests, and remaining work.

| Phase | Current scope |
|---|---|
| 1. Literature and evidence | Public metadata adapters, imports, identity checks, local document ingestion, evidence and claim records |
| 2. Manuscript development | Claim and manuscript triage, claim–source matrix, versioned section revisions |
| 3. Systematic review and meta-analysis | Protocol and screening records, derived flow, manual appraisal records, limited inverse-variance models |
| 4. Submission checks | Guideline routing, checklist status records, reviewer-response drafts, readiness gates |

The CLI does not semantically verify whether a source supports a claim. Risk-of-bias and certainty frameworks require human judgments; this repository does not implement validated instrument scoring. Meta-analysis methods are limited and need independent statistical review. Full-text access and PDF extraction may be incomplete.

Data are stored locally in SQLite, without encryption. Use appropriate device access controls and backups. Search queries are sent to the selected metadata provider. Do not enter patient-level or confidential content into external services without authorization.

## License and contributions

Project code, Skills, templates, and documentation are licensed under Apache-2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Third-party guideline materials remain subject to their own terms. Contribution and security reporting instructions are in [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
