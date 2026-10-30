"""Evidence capture and claim-evidence linkage with non-semantic integrity guards."""

from __future__ import annotations

from .errors import ValidationError
from .models import ClaimSourceLink, EvidenceClaim, EvidenceLocation, ExtractedEvidence, SupportDirection, VerificationDepth


def extract_evidence(reference_id: str, text: str, *, document_id: str | None = None,
                     locator: str | None = None, quote: str | None = None,
                     study_design: str | None = None, population: str | None = None,
                     outcome: str | None = None, result: str | None = None,
                     limitations: list[str] | None = None) -> ExtractedEvidence:
    if not text.strip():
        raise ValidationError("Evidence text must not be empty")
    location = None
    if document_id and locator:
        location = EvidenceLocation(document_id=document_id, locator_type="user_supplied",
                                    locator=locator, quote=quote)
    return ExtractedEvidence(reference_id=reference_id, text=text.strip(), location=location,
                             study_design=study_design, population=population, outcome=outcome,
                             result=result, limitations=limitations or [])


def link_claim(claim_id: str, source_id: str, support: str, *, verification_depth: str = "L0_unverified",
               directness: str = "unknown", locator: EvidenceLocation | None = None,
               limitations: list[str] | None = None, human_review_status: str = "not_reviewed") -> ClaimSourceLink:
    try:
        direction = SupportDirection(support)
        depth = VerificationDepth(verification_depth)
        from .models import HumanReviewStatus
        review = HumanReviewStatus(human_review_status)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    if not source_id or not claim_id:
        raise ValidationError("Claim and source IDs are required")
    # The link records a human/model-assigned relationship; it does not prove semantic support.
    return ClaimSourceLink(claim_id=claim_id, source_id=source_id, support_direction=direction,
                           verification_depth=depth, directness=directness,
                           evidence_location=locator, limitations=limitations or [], human_review_status=review)


def claim_evidence_matrix(claims: list[EvidenceClaim], links: list[ClaimSourceLink]) -> list[dict[str, object]]:
    by_claim: dict[str, list[ClaimSourceLink]] = {}
    for link in links:
        by_claim.setdefault(link.claim_id, []).append(link)
    rows = []
    for claim in claims:
        claim_links = by_claim.get(claim.claim_id, [])
        rows.append({"claim_id": claim.claim_id, "claim": claim.claim_text,
                     "claim_type": claim.claim_type, "section": claim.manuscript_section,
                     "epistemic_status": claim.epistemic_status,
                     "sources": [{"source_id": item.source_id,
                                  "support_direction": item.support_direction.value,
                                  "verification_depth": item.verification_depth.value,
                                  "directness": item.directness,
                                  "evidence_location": item.evidence_location.locator if item.evidence_location else None}
                                 for item in claim_links],
                     "contradictory_sources": claim.contradictory_sources,
                     "matrix_status": "unlinked" if not claim_links else "linkage_recorded_not_semantically_verified"})
    return rows
