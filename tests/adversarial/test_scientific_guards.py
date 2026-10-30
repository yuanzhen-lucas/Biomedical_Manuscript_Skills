from unittest import TestCase

from biomedical_manuscript.errors import ValidationError
from biomedical_manuscript.meta import StudyEffect, analyze
from biomedical_manuscript.references import normalize_doi, verify_doi
from biomedical_manuscript.submission import draft_reviewer_response


class AdversarialScientificGuards(TestCase):
    def test_fake_doi_is_not_normalized_into_valid_identifier(self):
        self.assertIsNone(normalize_doi("10.1234/"))

    def test_unrelated_real_doi_does_not_verify_expected_title(self):
        class Provider:
            def by_doi(self, doi):
                return {"title": ["A real but unrelated paper"]}
        self.assertFalse(verify_doi("10.1234/real", expected_title="Different paper", provider=Provider())["verified"])

    def test_incompatible_outcomes_refuse_pooling(self):
        with self.assertRaises(ValidationError):
            analyze([StudyEffect("A", 0.2, 0.1, "survival"), StudyEffect("B", 0.3, 0.1, "response")])

    def test_reviewer_response_never_asserts_unconfirmed_work(self):
        response = draft_reviewer_response(reviewer_comment="Run a new analysis")
        self.assertNotIn("We performed", response["response"])
        self.assertIn("AUTHOR CONFIRMATION REQUIRED", response["response"])
