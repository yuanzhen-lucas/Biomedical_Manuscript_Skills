# Reference project analysis

Reviewed on 2026-10-30. This is a design analysis, not a code reuse record. No source code, prompts, or third-party checklist text from these projects was copied into this repository.

## zLanqing/codex-claude-academic-skills

The repository presents complementary skills for academic writing, document work, and scientific computing, with Chinese-language support; its README identifies MIT licensing. Source: <https://github.com/zlanqing/codex-claude-academic-skills>.

- **ADOPT:** Separate reusable academic workflows into discoverable skill directories; support bilingual researchers and keep procedural guidance near its intended task.
- **ADAPT:** Keep skills interoperable while adding strict evidence, verification-depth, privacy, and human-review contracts for biomedical work.
- **REJECT:** Treating writing, document generation, or analysis instructions alone as an implemented evidence system; broad tool coverage without persisted claim-source provenance does not meet this project's scientific requirements.

## bytedance/deer-flow

DeerFlow is a long-horizon agent harness with skills, tools, memory, delegation, and sandboxed execution. The repository identifies MIT licensing. Its public systematic-literature-review skill uses staged search, extraction, synthesis, and report generation, and explicitly scopes its source set to arXiv. Sources: <https://github.com/bytedance/deer-flow>, <https://github.com/bytedance/deer-flow/blob/main/skills/public/systematic-literature-review/SKILL.md>.

- **ADOPT:** Stage long tasks, preserve intermediate state, separate per-source extraction from synthesis, and require cross-paper themes and disagreements.
- **ADAPT:** Replace the arXiv-only assumption with public biomedical providers plus user-authorized exports; replace mandatory subagents with capability-neutral, human-verifiable work; require protocol and record-derived counts before using “systematic review.”
- **REJECT:** Any assumption that a generic agent harness can validate medical evidence, that AI extraction is an independent human review, or that a multi-paper survey is automatically a systematic review. Do not adopt runtime-specific delegation instructions as core project requirements.

## affaan-m/ECC (Everything Claude Code)

ECC is a large multi-harness collection of skills, rules, hooks, memory, security tooling, and release validation. The repository identifies MIT licensing. Source: <https://github.com/affaan-m/ecc>.

- **ADOPT:** Specific skill descriptions, reusable workflow boundaries, security awareness, repository validators, and an explicit validation command.
- **ADAPT:** Use only a small validator and task-relevant references for this repository; prefer auditable plain files and local provenance over harness-specific hooks or state.
- **REJECT:** Making a large orchestration framework, hooks, automatic learning, or multi-agent runtime a prerequisite for scientific workflows. Those mechanisms add execution and confidentiality risk without establishing evidence validity.

## Licensing and reuse

The reviewed repositories expose MIT licenses, while this project uses Apache-2.0 for original materials. MIT-licensed content may be redistributed under compatible conditions with required notices, but this implementation intentionally reuses no code or checklist wording. External guidelines, articles, assessment tools, and datasets retain their own copyright/license terms. Recheck each upstream license and file-level notices before any future reuse; do not infer a repository-wide license for nested assets.
