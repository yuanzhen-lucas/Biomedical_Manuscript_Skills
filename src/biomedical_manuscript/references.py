"""Reference normalization, import, conservative deduplication, and DOI checks."""

from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .errors import ParseError, UnsupportedFormatError, ValidationError
from .models import ReferenceRecord, VerificationDepth
from .providers import CrossrefProvider, PubMedProvider

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip().strip("<>\"'")
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = doi.strip().rstrip(".,;)]}")
    doi = re.sub(r"\s+", "", doi)
    return doi.lower() if DOI_RE.fullmatch(doi) else None


def normalize_reference(record: ReferenceRecord) -> ReferenceRecord:
    record.doi = normalize_doi(record.doi)
    record.pmid = str(record.pmid).strip() if record.pmid else None
    record.pmcid = str(record.pmcid).strip().upper() if record.pmcid else None
    record.trial_id = str(record.trial_id).strip().upper() if record.trial_id else None
    record.title = re.sub(r"\s+", " ", record.title).strip()
    if not record.title:
        raise ValidationError("Reference title is required")
    return record


def title_key(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.casefold()))


def find_duplicates(records: list[ReferenceRecord]) -> list[dict[str, Any]]:
    """Identify exact identifier duplicates and flag title collisions as candidates only."""
    seen_doi: dict[str, int] = {}
    seen_pmid: dict[str, int] = {}
    seen_title_year: dict[tuple[str, int | None], int] = {}
    duplicates: list[dict[str, Any]] = []
    for i, record in enumerate(records):
        doi = normalize_doi(record.doi)
        if doi and doi in seen_doi:
            duplicates.append({"record_index": i, "duplicate_of": seen_doi[doi], "match": "doi_exact", "auto_merge": True})
            continue
        if record.pmid and str(record.pmid) in seen_pmid:
            duplicates.append({"record_index": i, "duplicate_of": seen_pmid[str(record.pmid)], "match": "pmid_exact", "auto_merge": True})
            continue
        key = title_key(record.title)
        identity = (key, record.year)
        if key and identity in seen_title_year:
            duplicates.append({"record_index": i, "duplicate_of": seen_title_year[identity], "match": "title_year_candidate", "auto_merge": False})
        if doi:
            seen_doi[doi] = i
        if record.pmid:
            seen_pmid[str(record.pmid)] = i
        if key:
            seen_title_year[identity] = i
    return duplicates


def verify_doi(doi: str, *, expected_title: str | None = None, provider: CrossrefProvider | None = None) -> dict[str, Any]:
    """Verify bibliographic identity via Crossref; never infer claim support from DOI existence."""
    normalized = normalize_doi(doi)
    if normalized is None:
        return {"verified": False, "level": VerificationDepth.L0.value, "reason": "malformed_doi", "doi": doi}
    provider = provider or CrossrefProvider()
    item = provider.by_doi(normalized)
    if not item:
        return {"verified": False, "level": VerificationDepth.L0.value, "reason": "doi_not_found", "doi": normalized}
    title = (item.get("title") or [""])[0]
    similarity = SequenceMatcher(None, title_key(expected_title or ""), title_key(title)).ratio() if expected_title else None
    title_matches = similarity is None or similarity >= 0.82
    return {"verified": bool(title_matches), "level": VerificationDepth.L1.value if title_matches else VerificationDepth.L0.value,
            "reason": "identity_verified" if title_matches else "doi_resolves_to_different_title",
            "doi": normalized, "resolved_title": title, "title_similarity": similarity,
            "warning": "Bibliographic identity verification does not establish that this source supports any claim."}


def verify_pmid(pmid: str, *, expected_title: str | None = None, provider: PubMedProvider | None = None) -> dict[str, Any]:
    """Verify PMID identity against PubMed metadata; this does not validate claim support."""
    identifier = str(pmid).strip()
    if not identifier.isdigit():
        return {"verified": False, "level": VerificationDepth.L0.value, "reason": "malformed_pmid", "pmid": identifier}
    provider = provider or PubMedProvider()
    results = provider.search(f"{identifier}[uid]", max_results=1)
    item = next((record for record in results if str(record.pmid) == identifier), None)
    if item is None:
        return {"verified": False, "level": VerificationDepth.L0.value, "reason": "pmid_not_found", "pmid": identifier}
    similarity = SequenceMatcher(None, title_key(expected_title or ""), title_key(item.title)).ratio() if expected_title else None
    if similarity is not None and similarity < 0.82:
        return {"verified": False, "level": VerificationDepth.L0.value, "reason": "pmid_resolves_to_different_title",
                "pmid": identifier, "resolved_title": item.title, "title_similarity": similarity}
    return {"verified": True, "level": VerificationDepth.L1.value, "reason": "identity_verified",
            "pmid": identifier, "resolved_title": item.title, "title_similarity": similarity,
            "warning": "Bibliographic identity verification does not establish that this source supports any claim."}


def _parse_ris(content: str) -> list[ReferenceRecord]:
    records, current = [], {}
    for line in content.splitlines() + ["ER  - "]:
        if line.startswith("TY  - "):
            current = {"authors": [], "keywords": []}
        elif line.startswith("ER  -"):
            if current:
                records.append(_record_from_fields(current, "ris"))
                current = {}
        elif current and len(line) >= 6 and line[2:6] == "  - ":
            tag, value = line[:2], line[6:].strip()
            if tag in {"AU", "A1"}:
                current.setdefault("authors", []).append(value)
            elif tag in {"TI", "T1", "CT"} and not current.get("title"):
                current["title"] = value
            elif tag in {"DO", "AN"}:
                current["doi"] = value if tag == "DO" else current.get("doi")
            elif tag in {"PY", "Y1", "DA"}:
                current["year"] = value
            elif tag in {"JO", "JF", "T2"}:
                current["journal"] = value
            elif tag in {"AB", "N2"}:
                current["abstract"] = value
            elif tag == "UR":
                current["url"] = value
    return records


def _record_from_fields(fields: dict[str, Any], source: str) -> ReferenceRecord:
    year_match = re.search(r"(?:19|20)\d{2}", str(fields.get("year", "")))
    raw_title = fields.get("title")
    return normalize_reference(ReferenceRecord(title=str(raw_title).strip() if raw_title is not None else "",
                                                authors=list(fields.get("authors", [])),
                                                year=int(year_match.group()) if year_match else None,
                                                journal=fields.get("journal"), doi=fields.get("doi"),
                                                pmid=fields.get("pmid"), trial_id=fields.get("trial_id"),
                                                abstract=fields.get("abstract"),
                                                url=fields.get("url"), source_provider=source))


def _parse_json_references(content: str) -> list[ReferenceRecord]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid reference JSON: {exc}") from exc
    rows = payload.get("records", payload.get("items", [])) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ParseError("Reference JSON must be an array or an object containing a records/items array")
    records = []
    for row in rows:
        if not isinstance(row, dict):
            raise ParseError("Each JSON reference record must be an object")
        title = row.get("title", "")
        if isinstance(title, list):
            title = title[0] if title else ""
        authors = row.get("authors") or row.get("author") or []
        if isinstance(authors, str):
            authors = [name.strip() for name in re.split(r"[;|]", authors) if name.strip()]
        elif isinstance(authors, dict):
            authors = [authors]
        normalized_authors = []
        for author in authors:
            if isinstance(author, dict):
                name = " ".join(str(author.get(key, "")).strip() for key in ("given", "family") if author.get(key))
                if name:
                    normalized_authors.append(name)
            elif author:
                normalized_authors.append(str(author))
        year = row.get("year")
        if year is None:
            date = row.get("published") or row.get("issued") or row.get("published-print") or row.get("published-online")
            if isinstance(date, dict):
                parts = date.get("date-parts", [])
                year = parts[0][0] if parts and parts[0] else None
        journal = row.get("journal") or row.get("container-title")
        if isinstance(journal, list):
            journal = journal[0] if journal else None
        records.append(_record_from_fields({"title": title, "authors": normalized_authors,
                                             "year": year, "journal": journal,
                                             "doi": row.get("doi") or row.get("DOI"), "pmid": row.get("pmid") or row.get("PMID"),
                                             "pmcid": row.get("pmcid") or row.get("PMCID"), "trial_id": row.get("trial_id") or row.get("nct_id"),
                                             "abstract": row.get("abstract"), "url": row.get("url") or row.get("URL")}, "json"))
    return records


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].casefold()


def _element_text(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    return " ".join("".join(element.itertext()).split()) or None


def _parse_xml_references(content: str) -> list[ReferenceRecord]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ParseError(f"Invalid reference XML: {exc}") from exc
    pubmed_articles = [element for element in root.iter() if _local_name(element) == "pubmedarticle"]
    records = []
    if pubmed_articles:
        for item in pubmed_articles:
            article = next((x for x in item.iter() if _local_name(x) == "article"), None)
            if article is None:
                continue
            title = next((x for x in article.iter() if _local_name(x) == "articletitle"), None)
            authors = []
            for author in (x for x in article.iter() if _local_name(x) == "author"):
                collective = next((x for x in author if _local_name(x) == "collectivename"), None)
                if collective is not None:
                    name = _element_text(collective)
                else:
                    last = next((x for x in author if _local_name(x) == "lastname"), None)
                    fore = next((x for x in author if _local_name(x) == "forename"), None)
                    name = " ".join(value for value in (_element_text(fore), _element_text(last)) if value)
                if name:
                    authors.append(name)
            journal = next((x for x in article.iter() if _local_name(x) == "title"), None)
            pubdate = next((x for x in article.iter() if _local_name(x) in {"pubdate", "datecompleted"}), None)
            year = next((x for x in pubdate.iter() if _local_name(x) == "year"), None) if pubdate is not None else None
            abstract = next((x for x in article.iter() if _local_name(x) == "abstract"), None)
            ids = {next((value for key, value in x.attrib.items() if key.casefold() == "idtype"), "").casefold(): _element_text(x)
                   for x in item.iter() if _local_name(x) == "articleid"}
            pmid_node = next((x for x in item.iter() if _local_name(x) == "pmid"), None)
            records.append(_record_from_fields({"title": _element_text(title), "authors": authors,
                                                 "year": _element_text(year), "journal": _element_text(journal),
                                                 "doi": ids.get("doi"), "pmid": _element_text(pmid_node),
                                                 "pmcid": ids.get("pmc"), "abstract": _element_text(abstract)}, "pubmed_xml"))
        return records
    for element in (x for x in root.iter() if _local_name(x) in {"record", "article"}):
        children = {_local_name(child): child for child in element}
        if not any(key in children for key in ("title", "articletitle")):
            continue
        records.append(_record_from_fields({"title": _element_text(children.get("title") or children.get("articletitle")),
                                             "authors": [_element_text(x) for x in children.values()
                                                         if _local_name(x) in {"author", "creator"} and _element_text(x)],
                                             "year": _element_text(children.get("year")),
                                             "journal": _element_text(children.get("journal")),
                                             "doi": _element_text(children.get("doi")),
                                             "pmid": _element_text(children.get("pmid")),
                                             "abstract": _element_text(children.get("abstract")),
                                             "url": _element_text(children.get("url"))}, "xml"))
    return records


def import_references(path: str | Path) -> list[ReferenceRecord]:
    file = Path(path)
    content = file.read_text(encoding="utf-8-sig")
    suffix = file.suffix.casefold()
    if suffix in {".ris"}:
        records = _parse_ris(content)
    elif suffix in {".nbib", ".txt"} and ("PMID-" in content or "TI  -" in content):
        rows, current, last_tag = [], {}, None
        for line in content.splitlines() + [""]:
            if not line.strip():
                if current:
                    rows.append(current)
                    current = {}
                last_tag = None
                continue
            if len(line) >= 6 and line[4:6] == "- ":
                tag, value = line[:4].strip(), line[6:].strip()
                last_tag = tag
                if tag in {"AU", "FAU"}:
                    current.setdefault("authors", []).append(value)
                elif tag in {"TI", "BTI"} and not current.get("title"):
                    current["title"] = value
                elif tag in {"AB", "ABSTRACT"}:
                    current["abstract"] = (current.get("abstract", "") + " " + value).strip()
                elif tag in {"JT", "TA"}:
                    current["journal"] = value
                elif tag == "AID" and "[doi]" in value:
                    current["doi"] = value.split("[", 1)[0]
                elif tag == "PMID":
                    current["pmid"] = value.rstrip(".")
                elif tag == "DP":
                    current["year"] = value
            elif last_tag == "AB":
                current["abstract"] = (current.get("abstract", "") + " " + line.strip()).strip()
        records = [_record_from_fields(row, "nbib") for row in rows]
    elif suffix == ".csv":
        records = []
        for row in csv.DictReader(content.splitlines()):
            normalized = {str(k).strip().casefold(): (v or "").strip() for k, v in row.items() if k}
            records.append(_record_from_fields({"title": normalized.get("title", ""),
                                                 "authors": [x.strip() for x in re.split(r"[;|]", normalized.get("authors", "")) if x.strip()],
                                                 "year": normalized.get("year"), "journal": normalized.get("journal"),
                                                 "doi": normalized.get("doi"), "pmid": normalized.get("pmid"),
                                                 "trial_id": normalized.get("trial_id") or normalized.get("nct_id"),
                                                 "abstract": normalized.get("abstract"), "url": normalized.get("url")}, "csv"))
    elif suffix == ".json":
        records = _parse_json_references(content)
    elif suffix == ".xml":
        records = _parse_xml_references(content)
    elif suffix == ".bib":
        records = []
        entries = re.split(r"@\w+\s*\{", content)[1:]
        for entry in entries:
            fields = {key.casefold(): value.strip().strip("{}\" ,\n")
                      for key, value in re.findall(r"(?im)^\s*(\w+)\s*=\s*([\{\"](?:[^{}\"]|\{[^{}]*\})*[}\"])", entry)}
            authors = [part.strip() for part in re.split(r"\s+and\s+", fields.get("author", ""), flags=re.I) if part.strip()]
            records.append(_record_from_fields({"title": fields.get("title", ""), "authors": authors,
                                                 "year": fields.get("year"), "journal": fields.get("journal") or fields.get("booktitle"),
                                                 "doi": fields.get("doi"), "abstract": fields.get("abstract")}, "bibtex"))
    else:
        raise UnsupportedFormatError(f"Unsupported reference format: {suffix or '[no extension]'}")
    if not records:
        raise ParseError(f"No reference records found in {file.name}")
    return records
