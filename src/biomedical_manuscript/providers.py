"""Rate-conscious adapters for public bibliographic and trial APIs.

These adapters retrieve metadata only. Database results, abstracts, and snippets
are not a substitute for inspecting relevant full text.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Protocol

from .errors import AuthenticationError, NetworkError, ProviderError, RateLimitError, ValidationError
from .models import ReferenceRecord

USER_AGENT = "BiomedicalManuscriptSkills/0.1 (research metadata; contact: configure BIOMED_CONTACT)"


class LiteratureProvider(Protocol):
    name: str

    def search(self, query: str, *, max_results: int = 20) -> list[ReferenceRecord]: ...


def _get_json(url: str, *, timeout: float = 20.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RateLimitError(f"HTTP 429 from provider at {urllib.parse.urlsplit(url).netloc}") from exc
        if exc.code == 401:
            raise AuthenticationError(f"HTTP {exc.code} from provider at {urllib.parse.urlsplit(url).netloc}") from exc
        if exc.code == 403:
            raise ProviderError(f"HTTP 403 forbidden from provider at {urllib.parse.urlsplit(url).netloc}; provider policy or rate limits may apply") from exc
        raise ProviderError(f"HTTP {exc.code} from provider at {urllib.parse.urlsplit(url).netloc}") from exc
    except urllib.error.URLError as exc:
        raise NetworkError(f"Could not reach provider at {urllib.parse.urlsplit(url).netloc}: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise NetworkError(f"Network request failed for {urllib.parse.urlsplit(url).netloc}: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError("Provider returned malformed JSON") from exc


def _get_xml(url: str, *, timeout: float = 20.0) -> ET.Element:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return ET.fromstring(response.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RateLimitError(f"HTTP 429 from provider at {urllib.parse.urlsplit(url).netloc}") from exc
        if exc.code == 401:
            raise AuthenticationError(f"HTTP {exc.code} from provider at {urllib.parse.urlsplit(url).netloc}") from exc
        if exc.code == 403:
            raise ProviderError(f"HTTP 403 forbidden from provider at {urllib.parse.urlsplit(url).netloc}; provider policy or rate limits may apply") from exc
        raise ProviderError(f"HTTP {exc.code} from provider at {urllib.parse.urlsplit(url).netloc}") from exc
    except urllib.error.URLError as exc:
        raise NetworkError(f"Could not reach provider at {urllib.parse.urlsplit(url).netloc}: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise NetworkError(f"Network request failed for {urllib.parse.urlsplit(url).netloc}: {exc}") from exc
    except ET.ParseError as exc:
        raise ProviderError("Provider returned malformed XML") from exc


def _limit(query: str, max_results: int) -> None:
    if not query.strip():
        raise ValidationError("Search query must not be empty")
    if not 1 <= max_results <= 100:
        raise ValidationError("max_results must be between 1 and 100")


def _year(value: Any) -> int | None:
    text = str(value or "")
    for i in range(len(text) - 3):
        chunk = text[i:i + 4]
        if chunk.isdigit() and 1500 <= int(chunk) <= 2200:
            return int(chunk)
    return None


@dataclass(slots=True)
class SearchExecution:
    provider: str
    query: str
    executed_at: str
    result_ids: list[str]
    parameters: dict[str, Any]
    execution_id: str
    status: str = "completed"


class PubMedProvider:
    name = "pubmed"
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, *, api_key: str | None = None, contact: str | None = None):
        self.api_key = api_key or os.getenv("NCBI_API_KEY")
        self.contact = contact or os.getenv("BIOMED_CONTACT")
        self._last_request = 0.0

    def _throttle(self) -> None:
        minimum = 0.11 if self.api_key else 0.35
        delay = minimum - (time.monotonic() - self._last_request)
        if delay > 0:
            time.sleep(delay)
        self._last_request = time.monotonic()

    def search(self, query: str, *, max_results: int = 20) -> list[ReferenceRecord]:
        _limit(query, max_results)
        params = {"db": "pubmed", "term": query, "retmax": str(max_results), "retmode": "json"}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.contact:
            params["email"] = self.contact
        self._throttle()
        result = _get_json(f"{self.base}/esearch.fcgi?{urllib.parse.urlencode(params)}")
        if not isinstance(result.get("esearchresult"), dict) or "idlist" not in result["esearchresult"]:
            raise ProviderError("PubMed returned an unexpected ESearch response shape")
        ids = result.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        summary_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
        if self.api_key:
            summary_params["api_key"] = self.api_key
        if self.contact:
            summary_params["email"] = self.contact
        self._throttle()
        root = _get_xml(f"{self.base}/efetch.fcgi?{urllib.parse.urlencode(summary_params)}")
        if root.tag != "PubmedArticleSet":
            raise ProviderError("PubMed returned an unexpected EFetch response shape")
        records = []
        for article in root.findall(".//PubmedArticle"):
            med = article.find("./MedlineCitation")
            info = article.find("./PubmedData")
            if med is None:
                continue
            pmid = med.findtext("./PMID")
            title = "".join(med.find("./Article/ArticleTitle").itertext()) if med.find("./Article/ArticleTitle") is not None else ""
            abstract = " ".join("".join(node.itertext()) for node in med.findall("./Article/Abstract/AbstractText")) or None
            authors = []
            for author in med.findall("./Article/AuthorList/Author"):
                collective = author.findtext("./CollectiveName")
                name = " ".join(x for x in [author.findtext("./ForeName"), author.findtext("./LastName")] if x)
                if collective or name:
                    authors.append(collective or name)
            doi = None
            for aid in article.findall("./PubmedData/ArticleIdList/ArticleId"):
                if aid.attrib.get("IdType") == "doi":
                    doi = aid.text
            journal = med.findtext("./Article/Journal/Title")
            pubdate = " ".join(x for x in [med.findtext("./Article/Journal/JournalIssue/PubDate/Year"),
                                             med.findtext("./Article/Journal/JournalIssue/PubDate/MedlineDate")] if x)
            corrections = []
            for relation in med.findall("./CommentsCorrectionsList/CommentsCorrections"):
                corrections.append({"type": relation.attrib.get("RefType"), "pmid": relation.findtext("./PMID")})
            pubstatus = "unknown"
            if any((r.get("type") or "").lower() == "retractionin" for r in corrections):
                pubstatus = "retracted"
            elif any((r.get("type") or "").lower() in {"erratumfor", "correctedandrepublishedfrom"} for r in corrections):
                pubstatus = "correction_or_update"
            records.append(ReferenceRecord(title=title, authors=authors, year=_year(pubdate), journal=journal,
                                           doi=doi, pmid=pmid, abstract=abstract, source_provider=self.name,
                                           provider_record_id=str(pmid or ""), publication_status=pubstatus,
                                           relations=corrections, url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None))
        return records


class EuropePMCProvider:
    name = "europe_pmc"

    def search(self, query: str, *, max_results: int = 20) -> list[ReferenceRecord]:
        _limit(query, max_results)
        params = {"query": query, "format": "json", "pageSize": str(max_results), "resultType": "core"}
        data = _get_json(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{urllib.parse.urlencode(params)}")
        if not isinstance(data.get("resultList"), dict) or not isinstance(data["resultList"].get("result"), list):
            raise ProviderError("Europe PMC returned an unexpected response shape")
        records = []
        for item in data.get("resultList", {}).get("result", []):
            authors_data = item.get("authorList", {}).get("author", [])
            authors = [a.get("fullName") or a.get("lastName", "") for a in authors_data if a.get("fullName") or a.get("lastName")]
            doi = item.get("doi")
            pmid = item.get("pmid")
            pmcid = item.get("pmcid")
            records.append(ReferenceRecord(title=item.get("title", ""), authors=authors, year=_year(item.get("firstPublicationDate") or item.get("pubYear")),
                                           journal=item.get("journalTitle"), doi=doi, pmid=str(pmid) if pmid else None,
                                           pmcid=pmcid, abstract=item.get("abstractText"), source_provider=self.name,
                                           provider_record_id=item.get("id"), publication_status="retracted" if item.get("isOpenAccess") is False and "retract" in str(item.get("pubType", "")).lower() else "unknown",
                                           url=f"https://europepmc.org/article/MED/{pmid}" if pmid else None,
                                           raw_metadata={"pubType": item.get("pubType"), "isOpenAccess": item.get("isOpenAccess")}))
        return records


class CrossrefProvider:
    name = "crossref"

    def search(self, query: str, *, max_results: int = 20) -> list[ReferenceRecord]:
        _limit(query, max_results)
        params = {"query.bibliographic": query, "rows": str(max_results)}
        contact = os.getenv("BIOMED_CONTACT")
        if contact:
            params["mailto"] = contact
        data = _get_json(f"https://api.crossref.org/works?{urllib.parse.urlencode(params)}")
        if not isinstance(data.get("message"), dict) or not isinstance(data["message"].get("items"), list):
            raise ProviderError("Crossref returned an unexpected response shape")
        records = []
        for item in data.get("message", {}).get("items", []):
            date_parts = item.get("published-print", {}).get("date-parts") or item.get("published-online", {}).get("date-parts") or item.get("created", {}).get("date-parts") or []
            year = date_parts[0][0] if date_parts and date_parts[0] else None
            authors = [" ".join(x for x in [a.get("given"), a.get("family")] if x) for a in item.get("author", [])]
            records.append(ReferenceRecord(title=(item.get("title") or [""])[0], authors=authors, year=year,
                                           journal=(item.get("container-title") or [None])[0], doi=item.get("DOI"),
                                           abstract=item.get("abstract"), source_provider=self.name,
                                           provider_record_id=item.get("DOI"), url=item.get("URL"),
                                           publication_status="retracted" if item.get("relation", {}).get("is-retracted-by") else "unknown",
                                           relations=[{"type": key, "items": val} for key, val in item.get("relation", {}).items()],
                                           raw_metadata={"type": item.get("type"), "published": item.get("published-print") or item.get("published-online")}))
        return records

    def by_doi(self, doi: str) -> dict[str, Any] | None:
        quoted = urllib.parse.quote(doi, safe="")
        try:
            return _get_json(f"https://api.crossref.org/works/{quoted}").get("message")
        except ProviderError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise


class OpenAlexProvider:
    name = "openalex"

    def search(self, query: str, *, max_results: int = 20) -> list[ReferenceRecord]:
        _limit(query, max_results)
        params = {"search": query, "per-page": str(max_results), "select": "id,doi,title,publication_year,authorships,primary_location,biblio,cited_by_count"}
        mailto = os.getenv("BIOMED_CONTACT")
        if mailto:
            params["mailto"] = mailto
        data = _get_json(f"https://api.openalex.org/works?{urllib.parse.urlencode(params)}")
        if not isinstance(data.get("results"), list):
            raise ProviderError("OpenAlex returned an unexpected response shape")
        records = []
        for item in data.get("results", []):
            authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
            location = item.get("primary_location", {}).get("source") or {}
            doi = item.get("doi")
            records.append(ReferenceRecord(title=item.get("title", ""), authors=authors, year=item.get("publication_year"),
                                           journal=location.get("display_name"), doi=doi.removeprefix("https://doi.org/") if doi else None,
                                           source_provider=self.name, provider_record_id=item.get("id"), url=item.get("id"),
                                           raw_metadata={"cited_by_count": item.get("cited_by_count")}))
        return records


class ClinicalTrialsProvider:
    name = "clinicaltrials_gov"

    def search(self, query: str, *, max_results: int = 20) -> list[ReferenceRecord]:
        _limit(query, max_results)
        params = {"query.term": query, "pageSize": str(max_results), "format": "json"}
        data = _get_json(f"https://clinicaltrials.gov/api/v2/studies?{urllib.parse.urlencode(params)}")
        if not isinstance(data.get("studies"), list):
            raise ProviderError("ClinicalTrials.gov returned an unexpected response shape")
        records = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            design = protocol.get("designModule", {})
            status = protocol.get("statusModule", {})
            nct = ident.get("nctId")
            records.append(ReferenceRecord(title=ident.get("briefTitle", ""), year=_year(status.get("studyFirstSubmitDate")),
                                           pmid=None, trial_id=nct, source_provider=self.name, provider_record_id=nct,
                                           url=f"https://clinicaltrials.gov/study/{nct}" if nct else None,
                                           publication_status=status.get("overallStatus", "unknown").lower(),
                                           raw_metadata={"nct_id": nct, "study_type": design.get("studyType"),
                                                         "conditions": protocol.get("conditionsModule", {}).get("conditions", [])}))
        return records


PROVIDERS: dict[str, type] = {
    "pubmed": PubMedProvider,
    "europe_pmc": EuropePMCProvider,
    "crossref": CrossrefProvider,
    "openalex": OpenAlexProvider,
    "clinicaltrials_gov": ClinicalTrialsProvider,
}
