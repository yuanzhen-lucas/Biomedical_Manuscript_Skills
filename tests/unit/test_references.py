from unittest import TestCase

from biomedical_manuscript.models import ReferenceRecord
from biomedical_manuscript.references import find_duplicates, normalize_doi, normalize_reference, verify_doi


class FakeCrossref:
    def __init__(self, result):
        self.result = result

    def by_doi(self, doi):
        self.seen = doi
        return self.result


class ReferenceTests(TestCase):
    def test_normalize_doi(self):
        self.assertEqual(normalize_doi("https://doi.org/10.1000/ABC."), "10.1000/abc")
        self.assertIsNone(normalize_doi("not-a-doi"))

    def test_fake_and_mismatched_doi_do_not_verify(self):
        self.assertFalse(verify_doi("bad", provider=FakeCrossref({}))['verified'])
        result = verify_doi("10.1000/real", expected_title="An unrelated title",
                            provider=FakeCrossref({"title": ["The actual paper title"]}))
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "doi_resolves_to_different_title")

    def test_doi_identity_does_not_claim_semantic_support(self):
        result = verify_doi("10.1000/real", expected_title="The actual paper title",
                            provider=FakeCrossref({"title": ["The actual paper title"]}))
        self.assertTrue(result["verified"])
        self.assertIn("does not establish", result["warning"])

    def test_deduplicate_identifier_only_and_flag_title_candidate(self):
        records = [
            ReferenceRecord("A study", doi="10.1234/x", year=2020),
            ReferenceRecord("A study", doi="https://doi.org/10.1234/X", year=2020),
            ReferenceRecord("A title collision", year=2021),
            ReferenceRecord("A title collision", year=2021),
        ]
        matches = find_duplicates(records)
        self.assertEqual(matches[0]["match"], "doi_exact")
        self.assertTrue(matches[0]["auto_merge"])
        self.assertFalse(matches[1]["auto_merge"])

    def test_normalize_reference_preserves_title_and_doi(self):
        record = normalize_reference(ReferenceRecord("  A   title ", doi="doi:10.5555/ABC"))
        self.assertEqual(record.title, "A title")
        self.assertEqual(record.doi, "10.5555/abc")
