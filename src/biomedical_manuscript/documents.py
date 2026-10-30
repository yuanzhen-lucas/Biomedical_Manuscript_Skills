"""Local document ingestion with extraction provenance and explicit limitations."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .errors import ParseError, UnsupportedFormatError
from .models import SourceDocument


def ingest_document(path: str | Path, reference_id: str) -> SourceDocument:
    """Read only a user-selected local file; no remote upload or OCR is performed."""
    file = Path(path).expanduser()
    raw = file.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    suffix = file.suffix.casefold()
    warnings: list[str] = []
    if suffix in {".txt", ".md", ".html", ".htm", ".xml"}:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ParseError("Text document is not valid UTF-8; convert it explicitly before ingestion") from exc
        method = "utf8_text_extraction"
        if suffix in {".html", ".htm"}:
            warnings.append("HTML tags were preserved; no DOM cleanup or article-content verification was performed.")
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise UnsupportedFormatError("PDF text extraction requires the optional dependency: pip install .[pdf]") from exc
        try:
            reader = PdfReader(str(file))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ParseError(f"Could not extract text from PDF: {exc}") from exc
        method = "pypdf_text_extraction"
        if not text.strip():
            warnings.append("No selectable text was extracted. OCR was not attempted; source remains unverified.")
        else:
            warnings.append("PDF extraction can miss tables, equations, layout, and text order; inspect the source PDF.")
    else:
        raise UnsupportedFormatError(f"Unsupported document format: {suffix}")
    return SourceDocument(reference_id=reference_id, access_level="full_text_extracted" if text.strip() else "full_text_inaccessible",
                          text=text, source_path=str(file.resolve()), content_sha256=digest,
                          extraction_method=method, extraction_warnings=warnings)
