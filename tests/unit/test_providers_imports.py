import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from biomedical_manuscript.errors import NetworkError, RateLimitError
from biomedical_manuscript.providers import (ClinicalTrialsProvider, CrossrefProvider, EuropePMCProvider,
                                           OpenAlexProvider, PubMedProvider, _get_json)
from biomedical_manuscript.references import import_references


class ProviderContractTests(TestCase):
    def test_pubmed_returns_unverified_reference_metadata(self):
        xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Sample title</ArticleTitle><Abstract><AbstractText>Abstract text</AbstractText></Abstract><Journal><Title>Journal</Title><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue></Journal><AuthorList><Author><ForeName>Ada</ForeName><LastName>Researcher</LastName></Author></AuthorList></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/example</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""
        with patch("biomedical_manuscript.providers._get_json", return_value={"esearchresult": {"idlist": ["123"]}}), \
                patch("biomedical_manuscript.providers._get_xml", return_value=__import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring(xml)), \
                patch("biomedical_manuscript.providers.time.sleep"):
            result = PubMedProvider().search("sample", max_results=1)
        self.assertEqual(result[0].pmid, "123")
        self.assertEqual(result[0].doi, "10.1000/example")
        self.assertEqual(result[0].verification_depth.value, "L0_unverified")

    def test_pubmed_retraction_relation_is_surfaced(self):
        xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Retracted study</ArticleTitle><Journal><Title>Journal</Title><JournalIssue><PubDate><Year>2022</Year></PubDate></JournalIssue></Journal></Article><CommentsCorrectionsList><CommentsCorrections RefType="RetractionIn"><PMID>456</PMID></CommentsCorrections></CommentsCorrectionsList></MedlineCitation><PubmedData/></PubmedArticle></PubmedArticleSet>"""
        with patch("biomedical_manuscript.providers._get_json", return_value={"esearchresult": {"idlist": ["123"]}}), \
                patch("biomedical_manuscript.providers._get_xml", return_value=__import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring(xml)), \
                patch("biomedical_manuscript.providers.time.sleep"):
            result = PubMedProvider().search("retracted", max_results=1)
        self.assertEqual(result[0].publication_status, "retracted")

    def test_europe_pmc_adapter_contract(self):
        payload = {"resultList": {"result": [{"title": "EPMC paper", "pmid": "4", "doi": "10.1000/e", "pubYear": "2020", "abstractText": "Abstract", "authorList": {"author": [{"fullName": "A B"}]}}]}}
        with patch("biomedical_manuscript.providers._get_json", return_value=payload):
            result = EuropePMCProvider().search("term", max_results=1)
        self.assertEqual((result[0].pmid, result[0].year, result[0].authors[0]), ("4", 2020, "A B"))

    def test_crossref_adapter_contract(self):
        payload = {"message": {"items": [{"title": ["Crossref title"], "DOI": "10.1000/c", "author": [{"given": "A", "family": "B"}], "published-online": {"date-parts": [[2022, 1]]}, "container-title": ["J"]}]}}
        with patch("biomedical_manuscript.providers._get_json", return_value=payload):
            result = CrossrefProvider().search("term", max_results=1)
        self.assertEqual((result[0].doi, result[0].year, result[0].journal), ("10.1000/c", 2022, "J"))

    def test_openalex_adapter_contract(self):
        payload = {"results": [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1000/o", "title": "OA title", "publication_year": 2019, "authorships": [], "primary_location": {"source": {"display_name": "Journal"}}}]}
        with patch("biomedical_manuscript.providers._get_json", return_value=payload):
            result = OpenAlexProvider().search("term", max_results=1)
        self.assertEqual(result[0].doi, "10.1000/o")

    def test_clinicaltrials_adapter_preserves_nct_id(self):
        payload = {"studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT00000001", "briefTitle": "Trial title"}, "designModule": {"studyType": "INTERVENTIONAL"}, "statusModule": {"overallStatus": "RECRUITING", "studyFirstSubmitDate": "2025-01-01"}}}]}
        with patch("biomedical_manuscript.providers._get_json", return_value=payload):
            result = ClinicalTrialsProvider().search("term", max_results=1)
        self.assertEqual(result[0].trial_id, "NCT00000001")
        self.assertEqual(result[0].year, 2025)

    def test_empty_query_and_result_limit_are_validation_errors(self):
        with self.assertRaises(Exception):
            EuropePMCProvider().search("  ")

    def test_network_errors_are_not_returned_as_zero_results(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            with self.assertRaises(NetworkError):
                _get_json("https://example.org")

    def test_rate_limit_has_distinct_error_type(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://example.org", 429, "slow", {}, None)):
            with self.assertRaises(RateLimitError):
                _get_json("https://example.org")


class ImportTests(TestCase):
    def _parse(self, suffix, content):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / f"refs.{suffix}"
        path.write_text(content, encoding="utf-8")
        return import_references(path)

    def test_ris_import(self):
        result = self._parse("ris", "TY  - JOUR\nTI  - A Sample Article\nAU  - Smith, Alex\nPY  - 2021\nDO  - 10.1000/xyz\nER  - \n")
        self.assertEqual(result[0].title, "A Sample Article")
        self.assertEqual(result[0].doi, "10.1000/xyz")

    def test_nbib_import(self):
        result = self._parse("nbib", "PMID- 12345\nTI  - NBIB title\nFAU - Doe, Jane\nDP  - 2020 Jan\nAID - 10.1000/nbib [doi]\n\n")
        self.assertEqual(result[0].pmid, "12345")
        self.assertEqual(result[0].year, 2020)

    def test_csv_import(self):
        result = self._parse("csv", "title,doi,year,nct_id\nCSV title,10.1000/csv,2021,NCT00000001\n")
        self.assertEqual(result[0].trial_id, "NCT00000001")

    def test_bibtex_import(self):
        result = self._parse("bib", "@article{key,\ntitle={Bib title},\nauthor={Smith, Alex and Doe, Jane},\nyear={2022},\ndoi={10.1000/bib}\n}\n")
        self.assertEqual(result[0].title, "Bib title")
        self.assertEqual(result[0].year, 2022)

    def test_crossref_style_json_import(self):
        result = self._parse("json", json.dumps({"items": [{
            "title": ["JSON title"], "DOI": "10.1000/json", "author": [{"given": "Ada", "family": "Researcher"}],
            "issued": {"date-parts": [[2025, 1]]}, "container-title": ["Journal"]
        }]}))
        self.assertEqual((result[0].title, result[0].doi, result[0].year, result[0].journal),
                         ("JSON title", "10.1000/json", 2025, "Journal"))
        self.assertEqual(result[0].authors, ["Ada Researcher"])

    def test_pubmed_xml_import(self):
        xml = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>456</PMID><Article><ArticleTitle>XML title</ArticleTitle><Journal><Title>Journal</Title><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue></Journal><AuthorList><Author><ForeName>Ada</ForeName><LastName>Researcher</LastName></Author></AuthorList><Abstract><AbstractText>Abstract text</AbstractText></Abstract></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/xml</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""
        result = self._parse("xml", xml)
        self.assertEqual((result[0].title, result[0].pmid, result[0].doi, result[0].year),
                         ("XML title", "456", "10.1000/xml", 2024))
        self.assertEqual(result[0].authors, ["Ada Researcher"])
