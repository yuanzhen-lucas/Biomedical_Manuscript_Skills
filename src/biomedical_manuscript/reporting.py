"""Version-aware reporting-guideline discovery and transparent completeness audits."""

from __future__ import annotations

import json
from pathlib import Path
import sysconfig
from typing import Any

from .errors import ValidationError

_SOURCE_REGISTRY = Path(__file__).resolve().parents[2] / "guidelines" / "registry.yaml"
_INSTALLED_REGISTRY = Path(sysconfig.get_path("data")) / "share" / "biomedical-manuscript-skills" / "guidelines" / "registry.yaml"
DEFAULT_REGISTRY = _SOURCE_REGISTRY if _SOURCE_REGISTRY.exists() else _INSTALLED_REGISTRY


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    """Load JSON-compatible YAML so the core package needs no YAML dependency."""
    file = Path(path) if path else DEFAULT_REGISTRY
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Unable to read guideline registry at {file}: {exc}") from exc
    if data.get("registry_schema") != "1.0" or not isinstance(data.get("guidelines"), list):
        raise ValidationError("Guideline registry schema is invalid")
    return data


def route_guidelines(*, study_design: str, study_features: list[str] | None = None,
                     registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or load_registry()
    signals = " ".join([study_design, *(study_features or [])]).casefold()
    selected = []
    for item in registry["guidelines"]:
        triggers = [x.casefold() for x in item.get("trigger_terms", [])]
        required = [x.casefold() for x in item.get("requires_all_terms", [])]
        required_any = [x.casefold() for x in item.get("requires_any_terms", [])]
        trigger_match = any(term in signals for term in triggers)
        required_match = all(term in signals for term in required) and (not required_any or any(term in signals for term in required_any))
        if trigger_match and required_match:
            selected.append({k: item.get(k) for k in ("id", "version", "title", "source_url", "version_status", "last_verified")})
    if not selected:
        selected = [{"id": "EQUATOR_DISCOVERY", "version": "current database", "title": "Search EQUATOR Network for a design-specific guideline", "source_url": "https://www.equator-network.org/reporting-guidelines/", "version_status": "live_discovery_required", "last_verified": None}]
    return selected


def reporting_audit(guideline_id: str, item_status: dict[str, str], *,
                    registry: dict[str, Any] | None = None,
                    live_source_verified: bool = False) -> dict[str, Any]:
    """Summarize author-supplied checklist assessments, not scientific quality."""
    registry = registry or load_registry()
    matches = [g for g in registry["guidelines"] if g["id"].casefold() == guideline_id.casefold()]
    if not matches:
        raise ValidationError(f"Unknown guideline id: {guideline_id}")
    guideline = matches[0]
    allowed = {"addressed", "partially_addressed", "not_addressed", "not_applicable", "not_assessed"}
    invalid = {key: value for key, value in item_status.items() if value not in allowed}
    if invalid:
        raise ValidationError(f"Invalid checklist status: {invalid}")
    counts = {key: sum(value == key for value in item_status.values()) for key in allowed}
    return {"guideline": {"id": guideline["id"], "version": guideline["version"], "source_url": guideline["source_url"]},
            "checklist_status": item_status, "counts": counts,
            "version_source_verified_for_this_audit": live_source_verified,
            "status": "reporting_completeness_only",
            "methodological_quality_assessed": False,
            "risk_of_bias_assessed": False,
            "human_review_required": True,
            "limitations": ["Checklist statuses are supplied by the user; this tool does not semantically verify each item.",
                            "Reporting completeness is not methodological validity or low risk of bias."]}
