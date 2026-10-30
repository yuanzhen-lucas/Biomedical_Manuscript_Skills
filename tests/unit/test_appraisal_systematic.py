import tempfile
from pathlib import Path
from unittest import TestCase

from biomedical_manuscript.appraisal import create_certainty_assessment, create_risk_of_bias
from biomedical_manuscript.errors import ValidationError
from biomedical_manuscript.store import ProjectStore
from biomedical_manuscript.systematic import save_protocol, validate_protocol


class AppraisalAndProtocolTests(TestCase):
    def test_risk_of_bias_requires_domain_rationales(self):
        with self.assertRaises(ValidationError):
            create_risk_of_bias(study_id="s1", instrument="test", domains={"selection": "high"},
                                rationale={}, reviewer="human")

    def test_ai_cannot_be_marked_human_approved(self):
        with self.assertRaises(ValidationError):
            create_risk_of_bias(study_id="s1", instrument="test", domains={"selection": "unclear"},
                                rationale={"selection": "Needs a human judgment."}, reviewer="agent",
                                reviewer_type="ai", human_review_status="approved")

    def test_certainty_assessment_is_human_recorded(self):
        assessment = create_certainty_assessment(outcome_id="outcome-1", framework="GRADE", certainty="low",
                                                 domains={"risk_of_bias": "serious", "imprecision": "no_information"},
                                                 rationale="Author adjudication required.", reviewer="reviewer")
        self.assertEqual(assessment.certainty, "low")

    def test_protocol_missing_fields_are_not_filled(self):
        data = {"title": "Review", "question": "Question"}
        self.assertEqual(set(validate_protocol(data)), {"eligibility", "sources", "screening_plan", "outcomes"})

    def test_protocol_versions_are_persisted_and_linked(self):
        protocol = {"title": "Review", "question": "Question", "eligibility": "criteria",
                    "sources": ["PubMed"], "screening_plan": "Two human reviewers", "outcomes": ["outcome"],
                    "registration_id": None, "version": "1"}
        with tempfile.TemporaryDirectory() as folder:
            store = ProjectStore(Path(folder) / "p.sqlite")
            saved = save_protocol(store, protocol)
            self.assertIsNone(saved.get("previous_protocol_id"))
            next_protocol = {**protocol, "protocol_id": "protocol_2", "version": "2"}
            save_protocol(store, next_protocol)
            stored = store.list_protocols()
            self.assertEqual(len(stored), 2)
            self.assertEqual(stored[1]["previous_protocol_id"], stored[0]["protocol_id"])
            store.close()
