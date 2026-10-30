"""Protocol and screening state with PRISMA-style counts derived from saved records."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .errors import ValidationError
from .store import ProjectStore

SCREEN_DECISIONS = {"include", "exclude", "uncertain"}
EXCLUSION_REASONS = {"wrong_population", "wrong_intervention_exposure", "wrong_comparator", "wrong_outcome",
                     "wrong_study_design", "wrong_publication_type", "wrong_setting", "other"}


def validate_protocol(protocol: dict[str, Any]) -> list[str]:
    required = ("title", "question", "eligibility", "sources", "screening_plan", "outcomes")
    missing = [key for key in required if not protocol.get(key)]
    if not protocol.get("registration_id"):
        # Registration is optional; never synthesize an identifier.
        pass
    return missing


def save_protocol(store: ProjectStore, protocol: dict[str, Any]) -> dict[str, Any]:
    missing = validate_protocol(protocol)
    if missing:
        raise ValidationError(f"Protocol is incomplete; missing fields: {', '.join(missing)}")
    store.add_protocol(protocol)
    return protocol


def record_decision(store: ProjectStore, *, study_id: str, stage: str, reviewer: str,
                    decision: str, rationale: str | None = None, exclusion_reason: str | None = None,
                    reviewer_type: str = "human", round_id: str | None = None) -> dict[str, Any]:
    if stage not in {"title_abstract", "full_text"}:
        raise ValidationError("stage must be title_abstract or full_text")
    if decision not in SCREEN_DECISIONS:
        raise ValidationError(f"decision must be one of {sorted(SCREEN_DECISIONS)}")
    if decision == "exclude" and stage == "full_text" and exclusion_reason not in EXCLUSION_REASONS:
        raise ValidationError("Full-text exclusion requires a controlled exclusion_reason")
    if decision != "exclude" and exclusion_reason:
        raise ValidationError("exclusion_reason is valid only for exclude decisions")
    from .models import now_utc
    record = {"decision_id": f"decision_{uuid4().hex}", "study_id": study_id, "stage": stage,
              "reviewer": reviewer, "reviewer_type": reviewer_type, "decision": decision,
              "rationale": rationale, "exclusion_reason": exclusion_reason, "round_id": round_id,
              "created_at": now_utc()}
    store.add_review_decision(record)
    return record


def derive_flow(store: ProjectStore, *, records_identified_by_source: dict[str, int] | None = None,
                duplicates_removed: int | None = None) -> dict[str, Any]:
    """Counts are read from stored study IDs/decisions; omitted acquisition counts remain null."""
    import json
    if duplicates_removed is not None and duplicates_removed < 0:
        raise ValidationError("duplicates_removed must be non-negative")
    if records_identified_by_source is not None and any(not isinstance(v, int) or v < 0 for v in records_identified_by_source.values()):
        raise ValidationError("Per-source identified counts must be non-negative integers")
    rows = []
    for row in store.connection.execute("SELECT study_id, stage, reviewer, decision, payload FROM review_decisions ORDER BY rowid"):
        payload = json.loads(row["payload"])
        rows.append({"study_id": row["study_id"], "stage": row["stage"], "reviewer": row["reviewer"],
                     "decision": row["decision"], "reviewer_type": payload.get("reviewer_type", "unknown"),
                     "payload": payload})
    by_stage: dict[str, dict[str, list[dict[str, Any]]]] = {"title_abstract": {}, "full_text": {}}
    for row in rows:
        by_stage[row["stage"]].setdefault(row["study_id"], []).append(row)
    ta = by_stage["title_abstract"]
    ft = by_stage["full_text"]
    # Keep the latest recorded decision per reviewer; preserve prior events in provenance.
    for stage in by_stage:
        for study, decisions in by_stage[stage].items():
            latest = {}
            for item in decisions:
                latest[item["reviewer"]] = item
            by_stage[stage][study] = list(latest.values())
    title_screened = len(ta)
    title_conflicts = {study for study, decisions in ta.items() if {x["decision"] for x in decisions} & {"exclude"} and {x["decision"] for x in decisions} & {"include", "uncertain"}}
    title_included = {study for study, decisions in ta.items() if study not in title_conflicts and any(x["decision"] in {"include", "uncertain"} for x in decisions)}
    title_excluded = {study for study, decisions in ta.items() if decisions and all(x["decision"] == "exclude" for x in decisions)}
    full_text = set(ft)
    full_conflicts = {study for study, decisions in ft.items()
                      if len({x["decision"] for x in decisions}) > 1
                      or (decisions and any(x["decision"] == "uncertain" for x in decisions))}
    full_text_excluded = {study for study, decisions in ft.items() if decisions and all(x["decision"] == "exclude" for x in decisions)}
    missing_reason = [study for study in full_text_excluded if not any(x["payload"].get("exclusion_reason") for x in ft[study])]
    excluded_reasons: dict[str, int] = {}
    exclusion_reason_conflicts = []
    for study in full_text_excluded:
        reasons = {item["payload"].get("exclusion_reason") for item in ft[study]
                   if item["payload"].get("exclusion_reason")}
        if len(reasons) == 1:
            reason = next(iter(reasons))
            excluded_reasons[reason] = excluded_reasons.get(reason, 0) + 1
        elif len(reasons) > 1:
            exclusion_reason_conflicts.append(study)
    def screening_ai_metrics(decisions_by_study: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        ai_only, ai_involved, ai_assisted, fewer_than_two_humans = [], [], [], []
        for study, decisions in decisions_by_study.items():
            ai = any(x["reviewer_type"] == "ai" for x in decisions)
            humans = len({x["reviewer"] for x in decisions if x["reviewer_type"] == "human"})
            if ai:
                ai_involved.append(study)
            if ai and humans == 0:
                ai_only.append(study)
            if ai and humans > 0:
                ai_assisted.append(study)
            if humans < 2:
                fewer_than_two_humans.append(study)
        return {"ai_only": ai_only, "ai_involved": ai_involved, "ai_assisted": ai_assisted,
                "fewer_than_two_humans": fewer_than_two_humans}

    ta_ai = screening_ai_metrics(ta)
    ft_ai = screening_ai_metrics(ft)
    included_reports = {study for study in full_text if study not in full_conflicts and ft[study]
                        and all(x["decision"] == "include" for x in ft[study])}
    report_study_map = store.study_ids_for_reports(included_reports)
    included_studies = {study_id for report_id in included_reports
                         for study_id in report_study_map.get(report_id, [report_id])}
    return {
        "records_identified_by_source": records_identified_by_source,
        "duplicates_removed": duplicates_removed,
        "records_screened_title_abstract": title_screened,
        "records_excluded_title_abstract": len(title_excluded),
        "title_abstract_conflicts_unresolved": sorted(title_conflicts),
        "reports_sought_for_retrieval": len(title_included),
        "reports_not_retrieved": len(title_included - full_text),
        "reports_assessed_full_text": len(full_text),
        "reports_excluded_full_text": len(full_text_excluded),
        "full_text_conflicts_unresolved": sorted(full_conflicts),
        "full_text_exclusion_reasons": excluded_reasons,
        "full_text_exclusion_reason_conflicts_unresolved": sorted(exclusion_reason_conflicts),
        "full_text_exclusions_missing_reason": missing_reason,
        "reports_included": len(included_reports),
        "studies_included": len(included_studies),
        "study_count_uses_user_recorded_report_linkage": bool(report_study_map),
        "records_with_ai_only_title_abstract_screening": ta_ai["ai_only"],
        "records_with_ai_involved_title_abstract_screening": ta_ai["ai_involved"],
        "records_with_ai_and_human_title_abstract_screening": ta_ai["ai_assisted"],
        "records_with_fewer_than_two_human_title_abstract_reviewers": ta_ai["fewer_than_two_humans"],
        "reports_with_ai_only_full_text_screening": ft_ai["ai_only"],
        "reports_with_ai_involved_full_text_screening": ft_ai["ai_involved"],
        "reports_with_ai_and_human_full_text_screening": ft_ai["ai_assisted"],
        "reports_with_fewer_than_two_human_full_text_reviewers": ft_ai["fewer_than_two_humans"],
        "counts_status": "derived_from_saved_decisions; acquisition totals are null unless supplied",
        "human_screening_warning": bool(ta_ai["ai_involved"] or ft_ai["ai_involved"]),
    }
