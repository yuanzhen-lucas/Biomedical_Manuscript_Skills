from unittest import TestCase

from biomedical_manuscript.audits import audit_claim_language, compare_numeric_tokens
from biomedical_manuscript.reporting import load_registry, reporting_audit, route_guidelines
from biomedical_manuscript.submission import draft_reviewer_response, submission_readiness


class AuditAndReportingTests(TestCase):
    def test_observational_causal_and_preclinical_escalation_are_flagged(self):
        findings = audit_claim_language("Exposure caused a clinical efficacy benefit in patients.",
                                        study_design="observational cohort", model_level="animal")
        codes = {item.code for item in findings}
        self.assertIn("causal_language_observational", codes)
        self.assertIn("preclinical_to_human_escalation", codes)

    def test_p_value_and_missingness_are_not_strengthened(self):
        findings = audit_claim_language("P = 0.08 was statistically significant. [DATA REQUIRED]")
        codes = {item.code for item in findings}
        self.assertIn("nonsignificant_result_overstated", codes)
        self.assertIn("unresolved_placeholder", codes)

    def test_numbers_differ_are_flagged_for_manual_review(self):
        result = compare_numeric_tokens("n=20, mean 4.2", "n=22, mean 4.2")
        self.assertEqual(result[0].code, "numeric_consistency_difference")

    def test_guideline_registry_routes_by_design_and_is_not_quality_score(self):
        registry = load_registry()
        ids = {item["id"] for item in route_guidelines(study_design="randomized trial", registry=registry)}
        self.assertIn("CONSORT", ids)
        audit = reporting_audit("CONSORT", {"1a": "addressed", "1b": "not_assessed"}, registry=registry)
        self.assertEqual(audit["status"], "reporting_completeness_only")
        self.assertFalse(audit["methodological_quality_assessed"])

    def test_new_pediatric_systematic_review_extension_is_in_registry(self):
        ids = {entry["id"] for entry in load_registry()["guidelines"]}
        self.assertIn("PRISMA-C", ids)

    def test_specialized_extensions_route_only_when_all_required_signals_match(self):
        registry = load_registry()
        strobe_ids = {item["id"] for item in route_guidelines(
            study_design="cohort", study_features=["disease prevalence"], registry=registry)}
        self.assertIn("STROBE-EPIC", strobe_ids)
        llm_ids = {item["id"] for item in route_guidelines(
            study_design="healthcare evaluation", study_features=["large language model"], registry=registry)}
        self.assertIn("TRIPOD-LLM", llm_ids)
        no_epic = {item["id"] for item in route_guidelines(
            study_design="randomized trial", study_features=["disease prevalence"], registry=registry)}
        self.assertNotIn("STROBE-EPIC", no_epic)

    def test_reviewer_response_does_not_invent_actions(self):
        response = draft_reviewer_response(reviewer_comment="Please add a sensitivity analysis.")
        self.assertIn("AUTHOR CONFIRMATION REQUIRED", response["response"])

    def test_submission_needs_explicit_human_approval_and_verified_journal(self):
        result = submission_readiness(journal_instructions_url="https://example.org", journal_instructions_checked_at="2026-10-30",
                                      journal_instructions_source_verified=False,
                                      unresolved_findings=[], human_approval="not_reviewed")
        self.assertEqual(result["status"], "not_ready")
        self.assertIn("explicit_final_human_approval_missing", result["findings"])
