import json
import tempfile
from pathlib import Path
from unittest import TestCase

from biomedical_manuscript.documents import ingest_document
from biomedical_manuscript.errors import ValidationError
from biomedical_manuscript.evidence import link_claim
from biomedical_manuscript.models import EvidenceClaim, ManuscriptProject, ManuscriptSection, ReferenceRecord, SourceDocument, StudyRecord
from biomedical_manuscript.store import ProjectStore
from biomedical_manuscript.systematic import derive_flow, record_decision


class StoreWorkflowTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.temp.name) / "project.sqlite")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_abstract_only_record_cannot_be_full_text_verified(self):
        ref = ReferenceRecord("Article title", doi="10.1234/a", abstract="Abstract details")
        reference_id = self.store.add_reference(ref)
        claim = EvidenceClaim("A claim")
        self.store.add_claim(claim)
        self.store.set_reference_verification(reference_id, {"verified": True, "level": "L1_identity_verified"})
        self.store.attest_reference_verification(reference_id, level="L2_abstract_checked",
                                                 reviewer="reviewer", rationale="Read the stored abstract.")
        link = link_claim(claim.claim_id, reference_id, "supports", verification_depth="L3_full_text_checked")
        with self.assertRaisesRegex(ValueError, "exceeds the reference's recorded depth"):
            self.store.add_claim_link(link)

    def test_full_text_location_and_human_approval_are_required_for_l4(self):
        ref = ReferenceRecord("Article title", doi="10.1234/a", abstract="Abstract details")
        reference_id = self.store.add_reference(ref)
        claim = EvidenceClaim("A claim")
        self.store.add_claim(claim)
        self.store.set_reference_verification(reference_id, {"verified": True, "level": "L1_identity_verified"})
        self.store.attest_reference_verification(reference_id, level="L2_abstract_checked", reviewer="reviewer", rationale="Checked abstract")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "article.txt"
            path.write_text("Methods\nParticipants were enrolled.", encoding="utf-8")
            document = ingest_document(path, reference_id)
            self.store.add_document(document)
        self.store.attest_reference_verification(reference_id, level="L3_full_text_checked", reviewer="reviewer",
                                                 rationale="Checked methods and results.", document_id=document.document_id,
                                                 locator="Results, paragraph 2")
        self.store.attest_reference_verification(reference_id, level="L4_human_reviewed", reviewer="reviewer",
                                                 rationale="Reviewed interpretation in relation to the claim.",
                                                 document_id=document.document_id, locator="Results, paragraph 2")
        link = link_claim(claim.claim_id, reference_id, "supports", verification_depth="L4_human_reviewed",
                          locator=__import__("biomedical_manuscript.models", fromlist=["EvidenceLocation"]).EvidenceLocation(
                              document.document_id, "section", "Results, paragraph 2"), human_review_status="approved")
        self.store.add_claim_link(link)
        saved = json.loads(self.store.connection.execute("SELECT payload FROM claim_links").fetchone()[0])
        self.assertEqual(saved["verification_depth"], "L4_human_reviewed")

    def test_duplicate_identifier_conflicts_preserved(self):
        ref1 = ReferenceRecord("Original title", doi="10.5555/x", authors=["A"], year=2020)
        ref2 = ReferenceRecord("Different title", doi="10.5555/x", authors=["B"], year=2021, source_provider="crossref")
        first = self.store.add_reference(ref1)
        second = self.store.add_reference(ref2)
        self.assertEqual(first, second)
        stored = self.store.get_reference(first)
        self.assertIn("metadata_conflicts", stored)
        self.assertEqual(len(stored["import_variants"]), 1)

    def test_real_doi_identity_does_not_semantically_verify_a_claim(self):
        from biomedical_manuscript.evidence import claim_evidence_matrix
        from biomedical_manuscript.models import ClaimSourceLink, SupportDirection, VerificationDepth
        ref = ReferenceRecord("A real paper", doi="10.1234/real")
        reference_id = self.store.add_reference(ref)
        self.store.set_reference_verification(reference_id, {"verified": True, "level": "L1_identity_verified"})
        claim = EvidenceClaim("An unrelated manuscript claim")
        self.store.add_claim(claim)
        link = link_claim(claim.claim_id, reference_id, "supports", verification_depth="L1_identity_verified")
        self.store.add_claim_link(link)
        self.assertEqual(claim.epistemic_status, "unverified")
        self.assertEqual(claim_evidence_matrix([claim], [link])[0]["matrix_status"],
                         "linkage_recorded_not_semantically_verified")

    def test_search_history_does_not_convert_failure_into_zero_results(self):
        self.store.add_failed_search(execution_id="s-fail", provider="pubmed", query="x", executed_at="2026-01-01T00:00:00Z",
                                     error_category="network_error", error_message="offline", parameters={})
        row = self.store.search_history()[0]
        self.assertEqual(row["status"], "failed")
        self.assertIsNone(row["result_count"])

    def test_screening_counts_come_from_saved_decisions_and_surface_ai(self):
        ids = []
        for n in range(3):
            ids.append(self.store.add_reference(ReferenceRecord(f"Study {n}")))
        record_decision(self.store, study_id=ids[0], stage="title_abstract", reviewer="R1", decision="exclude")
        record_decision(self.store, study_id=ids[1], stage="title_abstract", reviewer="AI", reviewer_type="ai", decision="include")
        record_decision(self.store, study_id=ids[1], stage="title_abstract", reviewer="R1", decision="include")
        record_decision(self.store, study_id=ids[2], stage="title_abstract", reviewer="R1", decision="uncertain")
        record_decision(self.store, study_id=ids[1], stage="full_text", reviewer="R1", decision="exclude",
                        exclusion_reason="wrong_population")
        record_decision(self.store, study_id=ids[2], stage="full_text", reviewer="R1", decision="include")
        flow = derive_flow(self.store)
        self.assertEqual(flow["records_screened_title_abstract"], 3)
        self.assertEqual(flow["records_excluded_title_abstract"], 1)
        self.assertEqual(flow["reports_sought_for_retrieval"], 2)
        self.assertEqual(flow["reports_excluded_full_text"], 1)
        self.assertEqual(flow["studies_included"], 1)
        self.assertIsNone(flow["records_identified_by_source"])
        self.assertTrue(flow["human_screening_warning"])
        self.assertEqual(flow["records_with_ai_and_human_title_abstract_screening"], [ids[1]])

    def test_ai_only_screening_is_not_misrepresented_as_human(self):
        study = self.store.add_reference(ReferenceRecord("AI reviewed study"))
        record_decision(self.store, study_id=study, stage="title_abstract", reviewer="AI", reviewer_type="ai", decision="include")
        self.assertTrue(derive_flow(self.store)["human_screening_warning"])

    def test_full_text_ai_screening_is_reported_separately(self):
        study = self.store.add_reference(ReferenceRecord("Full-text AI reviewed study"))
        record_decision(self.store, study_id=study, stage="full_text", reviewer="AI", reviewer_type="ai", decision="include")
        flow = derive_flow(self.store)
        self.assertEqual(flow["reports_with_ai_only_full_text_screening"], [study])
        self.assertEqual(flow["reports_with_ai_involved_full_text_screening"], [study])
        self.assertTrue(flow["human_screening_warning"])

    def test_manuscript_edits_are_versioned_with_reproducible_diff(self):
        manuscript_id = self.store.create_manuscript(ManuscriptProject(
            title="Synthetic study", manuscript_type="original_research"))
        section = ManuscriptSection(manuscript_id=manuscript_id, name="Results", text="The estimate was 1.2.")
        saved = self.store.add_manuscript_section(section, change_type="initial", reason="Author-provided draft",
                                                  scientific_impact="No change assessed", edited_by="author")
        updated = self.store.update_manuscript_section(section.section_id, "The estimate was 1.3.",
                                                       change_type="numerical_correction", reason="Corrected from verified analysis",
                                                       scientific_impact="Changes reported result", edited_by="author",
                                                       human_confirmed=True)
        self.assertEqual(saved["version"], 1)
        self.assertEqual(updated["version"], 2)
        self.assertIn("-The estimate was 1.2.", updated["diff_from_previous"])
        self.assertEqual(self.store.get_manuscript_section(section.section_id, 1)["text"], "The estimate was 1.2.")

    def test_ai_manuscript_edit_cannot_be_marked_human_confirmed(self):
        manuscript_id = self.store.create_manuscript(ManuscriptProject(
            title="Synthetic study", manuscript_type="original_research"))
        section = ManuscriptSection(manuscript_id=manuscript_id, name="Methods", text="Methods supplied by author.")
        with self.assertRaisesRegex(ValidationError, "AI edits cannot be marked human-confirmed"):
            self.store.add_manuscript_section(section, change_type="style", reason="Editing",
                                              scientific_impact="No scientific change intended", edited_by="model",
                                              editor_type="ai", human_confirmed=True)

    def test_disagreement_is_unresolved_not_silently_included(self):
        study = self.store.add_reference(ReferenceRecord("Disagreement study"))
        record_decision(self.store, study_id=study, stage="title_abstract", reviewer="R1", decision="include")
        record_decision(self.store, study_id=study, stage="title_abstract", reviewer="R2", decision="exclude")
        flow = derive_flow(self.store)
        self.assertIn(study, flow["title_abstract_conflicts_unresolved"])
        self.assertEqual(flow["reports_sought_for_retrieval"], 0)

    def test_multiple_reports_for_one_study_do_not_inflate_included_study_count(self):
        report_a = self.store.add_reference(ReferenceRecord("Primary report"))
        report_b = self.store.add_reference(ReferenceRecord("Follow-up report"))
        study_id = self.store.add_study_record(StudyRecord(reference_id=report_a, design="randomized trial"),
                                               mapped_by="reviewer", rationale="Same participant cohort and trial registration")
        self.store.link_report_to_study(study_id, report_b, mapped_by="reviewer",
                                        rationale="Reports a prespecified follow-up from the same trial")
        for report_id in (report_a, report_b):
            record_decision(self.store, study_id=report_id, stage="title_abstract", reviewer="R1", decision="include")
            record_decision(self.store, study_id=report_id, stage="full_text", reviewer="R1", decision="include")
        flow = derive_flow(self.store)
        self.assertEqual(flow["reports_included"], 2)
        self.assertEqual(flow["studies_included"], 1)
        self.assertTrue(flow["study_count_uses_user_recorded_report_linkage"])

    def test_exclusion_reasons_count_reports_once_and_flag_disagreement(self):
        same_reason = self.store.add_reference(ReferenceRecord("Same reason exclusion"))
        mixed_reason = self.store.add_reference(ReferenceRecord("Mixed reason exclusion"))
        for reviewer in ("R1", "R2"):
            record_decision(self.store, study_id=same_reason, stage="full_text", reviewer=reviewer,
                            decision="exclude", exclusion_reason="wrong_population")
        record_decision(self.store, study_id=mixed_reason, stage="full_text", reviewer="R1",
                        decision="exclude", exclusion_reason="wrong_population")
        record_decision(self.store, study_id=mixed_reason, stage="full_text", reviewer="R2",
                        decision="exclude", exclusion_reason="wrong_study_design")
        flow = derive_flow(self.store)
        self.assertEqual(flow["full_text_exclusion_reasons"], {"wrong_population": 1})
        self.assertEqual(flow["full_text_exclusion_reason_conflicts_unresolved"], [mixed_reason])
