# Current-source verification record

Checked 2026-10-30. Versions below are discovery metadata. Verify the linked official source and journal rules immediately before applying any guideline because extensions and journal policies change.

## Skills and agent conventions

- [OpenAI Skills documentation](https://developers.openai.com/plugins/concepts/skills): skills are folders with a `SKILL.md`, name/description metadata, workflow instructions, and optional supporting references/scripts/assets; metadata supports routing and full instructions load on match.
- [Agent Skills / API skills guide](https://developers.openai.com/api/docs/guides/tools-skills): skills are compatible with the Agent Skills standard; front matter validation follows the specification.

## Publication ethics

- [ICMJE Recommendations](https://www.icmje.org/recommendations/): the official page states “Updated January 2026.” The AI-use section states humans remain responsible for reviewing generated content and addresses authorship, attribution, confidentiality, and disclosure: <https://www.icmje.org/recommendations/browse/artificial-intelligence/>.
- [COPE position on authorship and AI tools](https://doi.org/10.24318/cCVRZBms): COPE's position, last reviewed 2023-02-13, says AI tools should not be listed as authors and calls for transparent disclosure. Journal policy must still be checked because policy may differ or evolve.

## Reporting guidelines confirmed during review

| Guideline | Registry edition | Source check |
|---|---:|---|
| CONSORT | 2025 | [CONSORT/SPIRIT published statements](https://www.consort-spirit.org/published-statements); the [BMJ CONSORT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081123) says it supersedes CONSORT 2010. |
| SPIRIT | 2025 | [CONSORT/SPIRIT published statements](https://www.consort-spirit.org/published-statements); see [SPIRIT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081477). |
| PRISMA | 2020 | [Official PRISMA 2020 page](https://www.prisma-statement.org/prisma-2020). |
| PRISMA-S | 2021 | [Official search extension page](https://www.prisma-statement.org/prisma-search). |
| PRISMA-C | 2026 | [Official children/adolescents extension page](https://www.prisma-statement.org/children); extension to PRISMA 2020 for covered pediatric intervention reviews. |
| ARRIVE | 2.0 (2020) | [ARRIVE 2.0](https://arriveguidelines.org/arrive-guidelines); Essential 10 and Recommended Set. |
| TRIPOD+AI | 2024 | [TRIPOD statement site](https://www.tripod-statement.org/). |
| CARE | 2013 checklist | [CARE downloads](https://www.care-statement.org/downloads). |
| STROBE, PRISMA-P, SRQR, CARE, STARD, TRIPOD+AI, ARRIVE, CHEERS | Registry routes to EQUATOR | [EQUATOR general guideline index](https://equator-network.org/index.html). |

The [EQUATOR full catalogue](https://equator-network.org/reporting-guidelines/) listed newer and study-specific materials at review time, including STROBE-EPIC and STARD-AI. The registry therefore requires extension discovery and does not assert that its historical base edition is universally the latest option.

- [STROBE-EPIC](https://equator-network.org/reporting-guidelines/strobe-epic/index.html) is an extension for reporting observational studies of disease prevalence or incidence; EQUATOR lists the 2026 Annals of Internal Medicine publication.
- [TRIPOD-LLM](https://www.nature.com/articles/s41591-024-03425-5) was published in 2025 as an extension for studies developing, tuning, or evaluating LLMs in healthcare. The paper describes it as a living statement and directs users to check the online version for current items.

## Reference projects

Reviewed the public repositories and their README/license indicators: [zLanqing academic skills](https://github.com/zlanqing/codex-claude-academic-skills), [DeerFlow](https://github.com/bytedance/deer-flow), [DeerFlow systematic literature review skill](https://github.com/bytedance/deer-flow/blob/main/skills/public/systematic-literature-review/SKILL.md), and [ECC](https://github.com/affaan-m/ecc). All three repositories exposed MIT licensing during review. No project code or skill text was copied.
