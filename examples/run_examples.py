#!/usr/bin/env python3
"""Run four offline synthetic workflow examples; no provider requests are made."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from biomedical_manuscript.audits import audit_manuscript, compare_numeric_tokens
from biomedical_manuscript.evidence import claim_evidence_matrix, link_claim
from biomedical_manuscript.meta import StudyEffect, analyze, forest_plot_svg
from biomedical_manuscript.models import EvidenceClaim, ManuscriptProject, ManuscriptSection, ReferenceRecord
from biomedical_manuscript.store import ProjectStore
from biomedical_manuscript.systematic import derive_flow, record_decision, save_protocol


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="Directory for synthetic SQLite and report outputs")
    args = parser.parse_args()
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    store = ProjectStore(out / "synthetic-project.sqlite")
    try:
        # A. Original research: preserve an author draft, link a claim, and triage it.
        manuscript = ManuscriptProject(title="Synthetic biomarker study", manuscript_type="original_research")
        manuscript_id = store.create_manuscript(manuscript)
        section_text = (
            "## Introduction\nSynthetic introduction.\n\n## Methods\nSynthetic assay protocol.\n\n"
            "## Results\nThe synthetic biomarker was associated with outcome Y (estimate 1.2).\n\n"
            "## Discussion\nThe synthetic finding is exploratory.\n")
        section = ManuscriptSection(manuscript_id=manuscript_id, name="Draft", text=section_text)
        store.add_manuscript_section(section, change_type="initial", reason="Synthetic demonstration draft",
                                     scientific_impact="No real scientific result is represented", edited_by="example")
        original_ref = ReferenceRecord("SYNTHETIC RECORD A — not a publication")
        original_ref_id = store.add_reference(original_ref)
        claim = EvidenceClaim("The synthetic biomarker was associated with outcome Y.", claim_type="associative",
                              manuscript_section="Results", epistemic_status="unverified")
        store.add_claim(claim)
        claim_link = link_claim(claim.claim_id, original_ref_id, "supports")
        store.add_claim_link(claim_link)
        findings = audit_manuscript(section_text, study_design="synthetic randomized study")
        write_json(out / "original-research-audit.json", {
            "claim_link_semantically_verified": False,
            "claim_evidence_matrix": claim_evidence_matrix([claim], [claim_link]),
            "manuscript_findings": [{"code": finding.code, "severity": finding.severity,
                                    "message": finding.message, "excerpt": finding.excerpt}
                                   for finding in findings],
            "numeric_comparison_findings": [finding.code for finding in compare_numeric_tokens("n=20", "n=20")]
        })

        # B. Narrative review: retain conflicting directions in a matrix; do not collapse them.
        narrative_claim = EvidenceClaim("Synthetic evidence for mechanism Z is mixed.", claim_type="mechanistic",
                                        manuscript_section="Synthesis", epistemic_status="unverified")
        ref_support = ReferenceRecord("SYNTHETIC RECORD B — supports mechanism Z")
        ref_conflict = ReferenceRecord("SYNTHETIC RECORD C — conflicts with mechanism Z")
        support_id, conflict_id = store.add_reference(ref_support), store.add_reference(ref_conflict)
        support_link = link_claim(narrative_claim.claim_id, support_id, "supports")
        conflict_link = link_claim(narrative_claim.claim_id, conflict_id, "contradicts")
        write_json(out / "narrative-review-matrix.json", {
            "scope": "Synthetic only; these records are not citations or evidence.",
            "matrix": claim_evidence_matrix([narrative_claim], [support_link, conflict_link]),
            "synthesis_status": "conflicting_directions_preserved; human evidence appraisal required"
        })

        # C. Systematic review: use saved decisions and separate reports from studies.
        protocol = {
            "title": "Synthetic review protocol example",
            "question": "In synthetic population P, does synthetic exposure X relate to outcome Y?",
            "eligibility": "Synthetic cohort reports with outcome Y",
            "sources": ["Synthetic local corpus"],
            "screening_plan": "Two human reviewers screen independently; disagreements are adjudicated.",
            "outcomes": ["Synthetic outcome Y"],
            "registration_id": None,
            "version": "1"
        }
        save_protocol(store, protocol)
        included_report = store.add_reference(ReferenceRecord("SYNTHETIC REPORT D"))
        excluded_report = store.add_reference(ReferenceRecord("SYNTHETIC REPORT E"))
        for ref_id in (included_report, excluded_report):
            record_decision(store, study_id=ref_id, stage="title_abstract", reviewer="Reviewer 1", decision="include")
        record_decision(store, study_id=included_report, stage="full_text", reviewer="Reviewer 1", decision="include")
        record_decision(store, study_id=excluded_report, stage="full_text", reviewer="Reviewer 1",
                        decision="exclude", exclusion_reason="wrong_population")
        write_json(out / "systematic-review-flow.json", derive_flow(store))

        # D. Meta-analysis: clearly synthetic values, with reproducible JSON and SVG outputs.
        effect_rows = json.loads((ROOT / "examples/meta-analysis/synthetic-effects.json").read_text(encoding="utf-8"))
        result = analyze([StudyEffect(**row) for row in effect_rows], model="random")
        write_json(out / "meta-analysis-result.json", result)
        (out / "meta-analysis-forest.svg").write_text(forest_plot_svg(result), encoding="utf-8")
    finally:
        store.close()
    print(json.dumps({"status": "completed", "data": "synthetic_only", "provider_requests": 0,
                      "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
