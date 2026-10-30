"""Versioned, JSON-safe biomedical evidence and provenance entities."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from . import SCHEMA_VERSION


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class VerificationDepth(str, Enum):
    L0 = "L0_unverified"
    L1 = "L1_identity_verified"
    L2 = "L2_abstract_checked"
    L3 = "L3_full_text_checked"
    L4 = "L4_human_reviewed"


class SupportDirection(str, Enum):
    SUPPORTS = "supports"
    PARTIAL = "partially_supports"
    CONTRADICTS = "contradicts"
    MIXED = "mixed"
    UNCLEAR = "unclear"
    NA = "not_applicable"


class HumanReviewStatus(str, Enum):
    NOT_REVIEWED = "not_reviewed"
    REQUESTED = "review_requested"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass(slots=True)
class ResearchQuestion:
    question: str
    framework: str | None = None
    population: str | None = None
    intervention_exposure: str | None = None
    comparator: str | None = None
    outcomes: list[str] = field(default_factory=list)
    study_designs: list[str] = field(default_factory=list)
    question_id: str = field(default_factory=lambda: new_id("rq"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class ResearchProject:
    title: str
    domain: str | None = None
    project_stage: str = "planning"
    project_id: str = field(default_factory=lambda: new_id("project"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class ManuscriptProject:
    title: str
    manuscript_type: str
    target_journal: str | None = None
    status: str = "draft"
    manuscript_id: str = field(default_factory=lambda: new_id("ms"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class SearchStrategy:
    provider: str
    query: str
    database_name: str
    fields: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    strategy_id: str = field(default_factory=lambda: new_id("strategy"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class SearchResult:
    execution_id: str
    reference_id: str
    rank: int
    result_id: str = field(default_factory=lambda: new_id("result"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class SourceAccessRecord:
    reference_id: str
    access_level: str
    provider_or_path: str | None = None
    reason: str | None = None
    accessed_at: str = field(default_factory=now_utc)
    access_id: str = field(default_factory=lambda: new_id("access"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class StudyPopulation:
    description: str
    population_id: str = field(default_factory=lambda: new_id("pop"))
    source_id: str | None = None
    model_level: str | None = None
    sample_size: int | None = None
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class InterventionExposure:
    description: str
    kind: str
    comparator: str | None = None
    duration: str | None = None
    intervention_id: str = field(default_factory=lambda: new_id("int"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class OutcomeRecord:
    name: str
    definition: str | None = None
    timepoint: str | None = None
    measure: str | None = None
    outcome_id: str = field(default_factory=lambda: new_id("outcome"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class StudyRecord:
    reference_id: str
    design: str
    study_id: str = field(default_factory=lambda: new_id("study"))
    population: StudyPopulation | None = None
    intervention_exposure: InterventionExposure | None = None
    outcomes: list[OutcomeRecord] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class RiskOfBiasAssessment:
    study_id: str
    instrument: str
    domains: dict[str, str]
    rationale: dict[str, str] = field(default_factory=dict)
    reviewer: str | None = None
    human_review_status: HumanReviewStatus = HumanReviewStatus.NOT_REVIEWED
    assessment_id: str = field(default_factory=lambda: new_id("rob"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class EvidenceCertaintyAssessment:
    outcome_id: str
    framework: str
    certainty: str
    domains: dict[str, str] = field(default_factory=dict)
    rationale: str | None = None
    reviewer: str | None = None
    assessment_id: str = field(default_factory=lambda: new_id("certainty"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class ManuscriptSection:
    manuscript_id: str
    name: str
    text: str = ""
    version: str = "1"
    section_id: str = field(default_factory=lambda: new_id("section"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class ManuscriptStatement:
    section_id: str
    text: str
    claim_id: str | None = None
    statement_id: str = field(default_factory=lambda: new_id("statement"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class ReportingGuideline:
    identifier: str
    version: str
    source_url: str
    verified_at: str | None = None
    guideline_id: str = field(default_factory=lambda: new_id("guideline"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class ReportingChecklist:
    guideline_id: str
    manuscript_id: str
    version: str
    checklist_id: str = field(default_factory=lambda: new_id("checklist"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class ChecklistAssessment:
    checklist_id: str
    item_id: str
    status: str
    manuscript_location: str | None = None
    rationale: str | None = None
    assessment_id: str = field(default_factory=lambda: new_id("assessment"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class AuditFinding:
    audit_type: str
    code: str
    severity: str
    message: str
    entity_id: str | None = None
    location: str | None = None
    finding_id: str = field(default_factory=lambda: new_id("finding"))
    schema_version: str = SCHEMA_VERSION


@dataclass(slots=True)
class HumanApproval:
    entity_type: str
    entity_id: str
    reviewer: str
    status: HumanReviewStatus
    rationale: str | None = None
    approval_id: str = field(default_factory=lambda: new_id("approval"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class ReferenceRecord:
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    trial_id: str | None = None
    abstract: str | None = None
    url: str | None = None
    source_provider: str = "user"
    provider_record_id: str | None = None
    verification_depth: VerificationDepth = VerificationDepth.L0
    publication_status: str = "unknown"
    relations: list[dict[str, Any]] = field(default_factory=list)
    reference_id: str = field(default_factory=lambda: new_id("ref"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceDocument:
    reference_id: str
    access_level: str
    text: str | None = None
    source_path: str | None = None
    content_sha256: str | None = None
    extraction_method: str | None = None
    extraction_warnings: list[str] = field(default_factory=list)
    document_id: str = field(default_factory=lambda: new_id("doc"))
    schema_version: str = SCHEMA_VERSION
    accessed_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class EvidenceLocation:
    document_id: str
    locator_type: str
    locator: str
    quote: str | None = None
    page: int | None = None


@dataclass(slots=True)
class ExtractedEvidence:
    reference_id: str
    text: str
    location: EvidenceLocation | None = None
    study_design: str | None = None
    population: str | None = None
    outcome: str | None = None
    result: str | None = None
    limitations: list[str] = field(default_factory=list)
    extraction_method: str = "human_or_model_assisted"
    human_review_status: HumanReviewStatus = HumanReviewStatus.NOT_REVIEWED
    evidence_id: str = field(default_factory=lambda: new_id("ev"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class EvidenceClaim:
    claim_text: str
    claim_type: str = "background"
    manuscript_section: str | None = None
    epistemic_status: str = "unverified"
    study_context: str | None = None
    limitations: list[str] = field(default_factory=list)
    contradictory_sources: list[str] = field(default_factory=list)
    human_review_status: HumanReviewStatus = HumanReviewStatus.NOT_REVIEWED
    claim_id: str = field(default_factory=lambda: new_id("claim"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)
    updated_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class ClaimSourceLink:
    claim_id: str
    source_id: str
    support_direction: SupportDirection
    evidence_location: EvidenceLocation | None = None
    verification_depth: VerificationDepth = VerificationDepth.L0
    directness: str = "unknown"
    limitations: list[str] = field(default_factory=list)
    human_review_status: HumanReviewStatus = HumanReviewStatus.NOT_REVIEWED
    link_id: str = field(default_factory=lambda: new_id("link"))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=now_utc)


@dataclass(slots=True)
class ProvenanceEvent:
    event_type: str
    entity_type: str
    entity_id: str
    details: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: new_id("evt"))
    schema_version: str = SCHEMA_VERSION
    occurred_at: str = field(default_factory=now_utc)


def to_dict(value: Any) -> dict[str, Any]:
    """Convert dataclasses/enums recursively without discarding missing values."""
    def convert(item: Any) -> Any:
        if isinstance(item, Enum):
            return item.value
        if hasattr(item, "__dataclass_fields__"):
            return {k: convert(v) for k, v in asdict(item).items()}
        if isinstance(item, dict):
            return {str(k): convert(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [convert(v) for v in item]
        return item

    return convert(value)
