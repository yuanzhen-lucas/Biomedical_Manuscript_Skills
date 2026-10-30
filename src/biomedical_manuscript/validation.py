"""Repository-level skill and registry contract validation."""

from __future__ import annotations

import json
import re
from pathlib import Path

REQUIRED_SKILL_SECTIONS = (
    "When to use", "When not to use", "Required inputs", "Optional inputs", "Workflow",
    "Dependencies", "Scientific safeguards", "Failure behavior", "Output contract",
    "Verification steps", "Human-review requirements",
)
REQUIRED_SKILLS = {
    "biomedical-manuscript", "biomedical-research-question", "biomedical-literature-search",
    "biomedical-reference-manager", "biomedical-paper-reader", "biomedical-evidence-synthesis",
    "biomedical-original-article", "biomedical-narrative-review", "biomedical-systematic-review",
    "biomedical-meta-analysis", "biomedical-statistical-review", "biomedical-scientific-editing",
    "biomedical-claim-audit", "biomedical-reporting-guidelines", "biomedical-peer-review",
    "biomedical-submission",
}


def validate_skill_files(root: str | Path) -> list[str]:
    root = Path(root)
    skill_root = root / "skills"
    errors: list[str] = []
    found: dict[str, Path] = {}
    for file in skill_root.glob("*/SKILL.md"):
        content = file.read_text(encoding="utf-8")
        lines = content.splitlines()
        if not lines or lines[0] != "---":
            errors.append(f"{file}: missing YAML front matter")
            continue
        try:
            end = lines.index("---", 1)
        except ValueError:
            errors.append(f"{file}: unterminated YAML front matter")
            continue
        metadata = {}
        for line in lines[1:end]:
            match = re.fullmatch(r"(name|description):\s*(.+)", line)
            if not match:
                errors.append(f"{file}: unsupported front matter field: {line}")
                continue
            metadata[match.group(1)] = match.group(2).strip().strip("\"'")
        name = metadata.get("name")
        if not name or not metadata.get("description") or len(metadata.get("description", "")) < 40:
            errors.append(f"{file}: name and a specific description are required")
        elif name in found:
            errors.append(f"{file}: duplicate skill name {name}")
        else:
            found[name] = file
        if file.parent.name != name:
            errors.append(f"{file}: directory name must match front matter name")
        for section in REQUIRED_SKILL_SECTIONS:
            if f"## {section}" not in content:
                errors.append(f"{file}: missing required section: {section}")
    missing = REQUIRED_SKILLS - found.keys()
    unexpected = found.keys() - REQUIRED_SKILLS
    if missing:
        errors.append(f"Missing required skills: {', '.join(sorted(missing))}")
    if unexpected:
        errors.append(f"Unexpected skill names: {', '.join(sorted(unexpected))}")
    return errors


def validate_registry(root: str | Path) -> list[str]:
    path = Path(root) / "guidelines" / "registry.yaml"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Invalid guideline registry: {exc}"]
    errors = []
    if registry.get("registry_schema") != "1.0":
        errors.append("Registry schema version must be 1.0")
    ids = [item.get("id") for item in registry.get("guidelines", [])]
    if len(ids) != len(set(ids)):
        errors.append("Guideline IDs must be unique")
    for item in registry.get("guidelines", []):
        if not item.get("version") or not item.get("source_url") or not item.get("last_verified"):
            errors.append(f"Guideline {item.get('id')} lacks version, source, or verification date")
    return errors
