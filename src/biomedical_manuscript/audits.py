"""Rule-based triage for common manuscript risks; findings require human review."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class AuditFinding:
    code: str
    severity: str
    message: str
    excerpt: str | None = None
    requires_human_review: bool = True


P_VALUE_RE = re.compile(r"\b[Pp]\s*(?:=|<|>)\s*0?\.\d+", re.I)
CAUSAL_RE = re.compile(r"\b(caused?|causes|causing|causal effect|led to|resulted in|demonstrates? that)\b", re.I)
HUMAN_EFFICACY_RE = re.compile(r"\b(effective treatment|effective therapy|treats? patients|improves? survival|clinical efficacy)\b", re.I)
MISSING_MARKER_RE = re.compile(r"\[(?:DATA REQUIRED|SOURCE NEEDED|FULL TEXT REQUIRED|VERIFICATION REQUIRED|METHOD REQUIRED|STATISTICAL REVIEW REQUIRED|AUTHOR CONFIRMATION REQUIRED|HUMAN REVIEW REQUIRED)\]", re.I)


def _finding(code: str, severity: str, message: str, match: re.Match[str] | None = None) -> AuditFinding:
    excerpt = None
    if match:
        start, end = max(0, match.start() - 60), min(len(match.string), match.end() + 60)
        excerpt = match.string[start:end].replace("\n", " ")
    return AuditFinding(code, severity, message, excerpt)


def audit_claim_language(text: str, *, study_design: str | None = None,
                         model_level: str | None = None) -> list[AuditFinding]:
    """Find signals for human review; does not infer validity from individual verbs."""
    findings: list[AuditFinding] = []
    design = (study_design or "").casefold()
    if any(x in design for x in ("observational", "cohort", "case-control", "cross-sectional")):
        for match in CAUSAL_RE.finditer(text):
            findings.append(_finding("causal_language_observational", "high",
                                     "Review whether causal wording is justified by the design and analysis; the trigger is a prompt for reasoning, not an automatic verdict.", match))
    if model_level and model_level.casefold() in {"in vitro", "organoid", "animal", "mouse", "rat", "preclinical"}:
        for match in HUMAN_EFFICACY_RE.finditer(text):
            findings.append(_finding("preclinical_to_human_escalation", "high",
                                     f"Review translational level: evidence is labeled {model_level}; human efficacy is not established by this model alone.", match))
    for match in re.finditer(r"\bP\s*(?:=|>)\s*(0?\.0[5-9]\d*|0?\.[1-9]\d*)", text):
        neighborhood = text[max(0, match.start() - 80):min(len(text), match.end() + 80)]
        if re.search(r"\b(significant|statistically significant)\b", neighborhood, re.I):
            findings.append(_finding("nonsignificant_result_overstated", "high",
                                     "A P value at or above .05 is described as significant nearby; verify prespecified thresholds, multiplicity, and context.", match))
    for match in MISSING_MARKER_RE.finditer(text):
        findings.append(_finding("unresolved_placeholder", "medium", "Replace or explicitly retain this unresolved item before submission.", match))
    return findings


def detect_missing_required_sections(text: str, *, research_type: str = "original_research") -> list[AuditFinding]:
    normalized = text.casefold()
    findings = []
    if research_type == "original_research":
        for heading in ("introduction", "methods", "results", "discussion"):
            if not re.search(rf"(?im)^\s*(?:#+\s*)?{heading}\s*$", normalized):
                findings.append(AuditFinding("missing_imrad_section", "medium", f"Could not find an explicit {heading.title()} heading."))
    declarations = {
        "ethics": r"ethic(?:s|al)|institutional review board|irb|animal care",
        "funding": r"funding|financial support",
        "conflict_of_interest": r"conflict of interest|competing interest",
        "data_availability": r"data availability|availability of data",
    }
    for name, pattern in declarations.items():
        if not re.search(pattern, normalized):
            findings.append(AuditFinding(f"missing_{name}_statement", "medium",
                                         f"No {name.replace('_', ' ')} statement was detected. Confirm whether one is required and supply author-verified information."))
    return findings


def compare_numeric_tokens(text_a: str, text_b: str, *, labels: tuple[str, str] = ("section A", "section B")) -> list[AuditFinding]:
    """Flag differing numeric token multisets between two supplied text regions."""
    token = re.compile(r"(?<![A-Za-z])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:%|\s?%|\s?(?:mg|kg|mL|mmol/L|years?|months?|days?))?", re.I)
    left = [re.sub(r"\s+", "", m.group()).casefold() for m in token.finditer(text_a)]
    right = [re.sub(r"\s+", "", m.group()).casefold() for m in token.finditer(text_b)]
    if sorted(left) == sorted(right):
        return []
    return [AuditFinding("numeric_consistency_difference", "high",
                         f"Numeric tokens differ between {labels[0]} and {labels[1]}; review manually because not all numbers should match.",
                         f"{labels[0]}={left}; {labels[1]}={right}")]


def audit_manuscript(text: str, *, study_design: str | None = None,
                     model_level: str | None = None, research_type: str = "original_research") -> list[AuditFinding]:
    return (audit_claim_language(text, study_design=study_design, model_level=model_level)
            + detect_missing_required_sections(text, research_type=research_type))
