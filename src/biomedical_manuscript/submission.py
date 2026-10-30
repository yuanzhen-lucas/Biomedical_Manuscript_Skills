"""Peer-review response drafts and final human-approval readiness gates."""

from __future__ import annotations

from typing import Any


def draft_reviewer_response(*, reviewer_comment: str, author_verified_action: str | None = None,
                            manuscript_location: str | None = None,
                            evidence_of_change: str | None = None) -> dict[str, Any]:
    if not author_verified_action:
        response = "[AUTHOR CONFIRMATION REQUIRED: describe what was actually done. Do not claim an experiment, analysis, or text change unless completed and verified.]"
    else:
        response = author_verified_action.strip()
    return {"reviewer_comment": reviewer_comment,
            "response": response,
            "manuscript_location": manuscript_location or "[AUTHOR CONFIRMATION REQUIRED]",
            "evidence_of_change": evidence_of_change or "[AUTHOR CONFIRMATION REQUIRED]",
            "status": "draft_requires_author_verification"}


def submission_readiness(*, journal_instructions_url: str | None,
                         journal_instructions_checked_at: str | None,
                         journal_instructions_source_verified: bool = False,
                         unresolved_findings: list[str], human_approval: str,
                         consent_to_external_transfer: bool = False) -> dict[str, Any]:
    findings = list(unresolved_findings)
    if not journal_instructions_url or not journal_instructions_checked_at:
        findings.append("journal_instructions_not_source_verified")
    elif not journal_instructions_source_verified:
        findings.append("journal_instructions_verification_not_attested")
    if human_approval != "approved":
        findings.append("explicit_final_human_approval_missing")
    return {"status": "submission_ready_candidate" if not findings else "not_ready",
            "findings": findings,
            "human_approval": human_approval,
            "journal_instructions_source_verified": bool(journal_instructions_source_verified),
            "external_transfer_authorized": bool(consent_to_external_transfer),
            "automatic_transmission_performed": False,
            "note": "A candidate status is not a guarantee of correctness, acceptance, or journal compliance."}
