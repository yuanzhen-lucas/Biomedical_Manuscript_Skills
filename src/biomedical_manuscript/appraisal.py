"""Human-led risk-of-bias and certainty record validation; no automated rating."""

from __future__ import annotations

from .errors import ValidationError
from .models import EvidenceCertaintyAssessment, HumanReviewStatus, RiskOfBiasAssessment

ROB_JUDGMENTS = {"low", "some_concerns", "moderate", "serious", "high", "critical", "unclear", "no_information", "not_applicable"}
CERTAINTIES = {"high", "moderate", "low", "very_low", "not_assessed"}
CERTAINTY_DOMAIN_JUDGMENTS = {"not_serious", "serious", "very_serious", "no_information", "not_assessed"}


def create_risk_of_bias(*, study_id: str, instrument: str, domains: dict[str, str],
                        rationale: dict[str, str], reviewer: str,
                        reviewer_type: str = "human", human_review_status: str = "not_reviewed") -> RiskOfBiasAssessment:
    if not study_id or not instrument.strip() or not reviewer.strip() or not domains:
        raise ValidationError("Study ID, instrument, reviewer, and domain judgments are required")
    if set(domains) != set(rationale) or any(not text.strip() for text in rationale.values()):
        raise ValidationError("Each risk-of-bias domain needs a rationale, and domains must match exactly")
    invalid = {domain: judgment for domain, judgment in domains.items() if judgment not in ROB_JUDGMENTS}
    if invalid:
        raise ValidationError(f"Unrecognized risk-of-bias judgments: {invalid}")
    try:
        status = HumanReviewStatus(human_review_status)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    if reviewer_type != "human" and status in {HumanReviewStatus.REVIEWED, HumanReviewStatus.APPROVED}:
        raise ValidationError("AI output cannot be marked human-reviewed or approved")
    return RiskOfBiasAssessment(study_id=study_id, instrument=instrument, domains=domains,
                                rationale=rationale, reviewer=reviewer,
                                human_review_status=status)


def create_certainty_assessment(*, outcome_id: str, framework: str, certainty: str,
                                domains: dict[str, str], rationale: str,
                                reviewer: str) -> EvidenceCertaintyAssessment:
    if not outcome_id or not framework.strip() or not reviewer.strip() or not rationale.strip() or not domains:
        raise ValidationError("Outcome, framework, reviewer, domain judgments, and rationale are required")
    if certainty not in CERTAINTIES:
        raise ValidationError(f"certainty must be one of {sorted(CERTAINTIES)}")
    invalid = {domain: rating for domain, rating in domains.items() if rating not in CERTAINTY_DOMAIN_JUDGMENTS}
    if invalid:
        raise ValidationError(f"Unrecognized certainty-domain judgments: {invalid}")
    return EvidenceCertaintyAssessment(outcome_id=outcome_id, framework=framework,
                                       certainty=certainty, domains=domains,
                                       rationale=rationale, reviewer=reviewer)
