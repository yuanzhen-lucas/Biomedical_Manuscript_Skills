"""Local SQLite project store with append-only provenance events."""

from __future__ import annotations

import hashlib
import difflib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .models import ProvenanceEvent, now_utc, to_dict


class ProjectStore:
    """Persist evidence objects locally; never uploads project content."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()
        self._restrict_permissions()

    def close(self) -> None:
        self.connection.close()

    def _initialize(self) -> None:
        metadata_exists = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'"
        ).fetchone()
        if metadata_exists:
            row = self.connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if row and row["value"] != "1.0":
                raise ValidationError(f"Unsupported project schema {row['value']}; migration is required")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reference_records (
                id TEXT PRIMARY KEY,
                doi TEXT,
                pmid TEXT,
                trial_id TEXT UNIQUE,
                title TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(doi),
                UNIQUE(pmid)
            );
            CREATE TABLE IF NOT EXISTS search_executions (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                query TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                result_count INTEGER,
                status TEXT NOT NULL,
                error_category TEXT,
                error_message TEXT,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS search_results (
                execution_id TEXT NOT NULL REFERENCES search_executions(id),
                reference_id TEXT NOT NULL REFERENCES reference_records(id),
                rank INTEGER NOT NULL,
                PRIMARY KEY(execution_id, reference_id)
            );
            CREATE TABLE IF NOT EXISTS source_documents (
                id TEXT PRIMARY KEY,
                reference_id TEXT NOT NULL REFERENCES reference_records(id),
                access_level TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                reference_id TEXT NOT NULL REFERENCES reference_records(id),
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                claim_text TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS claim_links (
                id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES claims(id),
                source_id TEXT NOT NULL REFERENCES reference_records(id),
                support_direction TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS review_decisions (
                id TEXT PRIMARY KEY,
                study_id TEXT NOT NULL REFERENCES reference_records(id),
                stage TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS study_records (
                id TEXT PRIMARY KEY,
                design TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS study_reports (
                study_id TEXT NOT NULL REFERENCES study_records(id),
                reference_id TEXT NOT NULL REFERENCES reference_records(id),
                mapped_by TEXT NOT NULL,
                rationale TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(study_id, reference_id)
            );
            CREATE TABLE IF NOT EXISTS appraisals (
                id TEXT PRIMARY KEY,
                assessment_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS systematic_protocols (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                payload TEXT NOT NULL,
                saved_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS manuscript_projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                manuscript_type TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS manuscript_sections (
                id TEXT PRIMARY KEY,
                manuscript_id TEXT NOT NULL REFERENCES manuscript_projects(id),
                name TEXT NOT NULL,
                latest_version INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS manuscript_section_versions (
                section_id TEXT NOT NULL REFERENCES manuscript_sections(id),
                version INTEGER NOT NULL,
                text TEXT NOT NULL,
                change_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                scientific_impact TEXT NOT NULL,
                edited_by TEXT NOT NULL,
                editor_type TEXT NOT NULL,
                human_confirmed INTEGER NOT NULL,
                previous_sha256 TEXT,
                content_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(section_id, version)
            );
            CREATE TABLE IF NOT EXISTS provenance_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_claim_links_claim ON claim_links(claim_id);
            CREATE INDEX IF NOT EXISTS idx_decisions_study ON review_decisions(study_id);
            CREATE INDEX IF NOT EXISTS idx_events_entity ON provenance_events(entity_type, entity_id);
            """
        )
        self.connection.execute(
            "INSERT OR IGNORE INTO metadata(key, value) VALUES('schema_version', '1.0')"
        )
        self.connection.commit()

    def _restrict_permissions(self) -> None:
        for target in (self.path, Path(f"{self.path}-wal"), Path(f"{self.path}-shm")):
            if target.exists():
                try:
                    os.chmod(target, 0o600)
                except OSError:
                    pass

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(to_dict(value), ensure_ascii=False, sort_keys=True)

    def event(self, event: ProvenanceEvent) -> None:
        self.connection.execute(
            "INSERT INTO provenance_events VALUES (?, ?, ?, ?, ?, ?)",
            (event.event_id, event.event_type, event.entity_type, event.entity_id,
             event.occurred_at, self._json(event)),
        )

    def add_reference(self, reference: Any, *, event_type: str = "reference_imported") -> str:
        payload = to_dict(reference)
        doi = payload.get("doi")
        pmid = payload.get("pmid")
        matches = [self.find_reference(doi=doi), self.find_reference(pmid=pmid),
                   self.find_reference(trial_id=payload.get("trial_id"))]
        matched_ids = {item["id"] for item in matches if item}
        if len(matched_ids) > 1:
            raise ValidationError("DOI, PMID, or trial ID point to different stored records; resolve identifier collision manually")
        existing = matches[0] or matches[1] or matches[2]
        if existing:
            current = existing["payload"]
            compared = ("title", "authors", "year", "journal")
            conflicts = {key: {"stored": current.get(key), "incoming": payload.get(key)}
                         for key in compared if current.get(key) and payload.get(key) and current.get(key) != payload.get(key)}
            variants = current.setdefault("import_variants", [])
            variants.append({"source_provider": payload.get("source_provider"),
                             "provider_record_id": payload.get("provider_record_id"),
                             "metadata": payload, "conflicts": conflicts})
            if conflicts:
                current.setdefault("metadata_conflicts", []).append({"incoming_source": payload.get("source_provider"), "fields": conflicts})
            if not current.get("pmid") and pmid:
                current["pmid"] = pmid
                self.connection.execute("UPDATE reference_records SET pmid=? WHERE id=?", (pmid, existing["id"]))
            self.connection.execute("UPDATE reference_records SET payload=? WHERE id=?", (self._json(current), existing["id"]))
            self.event(ProvenanceEvent("duplicate_reference_reconciled", "reference", existing["id"],
                                       {"incoming_source": payload.get("source_provider"), "metadata_conflicts": conflicts}))
            self.connection.commit()
            return existing["id"]
        self.connection.execute(
            "INSERT INTO reference_records(id, doi, pmid, trial_id, title, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (payload["reference_id"], doi, pmid, payload.get("trial_id"), payload["title"], self._json(payload)),
        )
        self.event(ProvenanceEvent(event_type, "reference", payload["reference_id"],
                                   {"source_provider": payload.get("source_provider")}))
        self.connection.commit()
        return payload["reference_id"]

    def find_reference(self, *, doi: str | None = None, pmid: str | None = None,
                       trial_id: str | None = None) -> dict[str, Any] | None:
        if doi:
            row = self.connection.execute("SELECT id, payload FROM reference_records WHERE doi=?", (doi,)).fetchone()
            if row:
                return {"id": row["id"], "payload": json.loads(row["payload"])}
        if pmid:
            row = self.connection.execute("SELECT id, payload FROM reference_records WHERE pmid=?", (str(pmid),)).fetchone()
            if row:
                return {"id": row["id"], "payload": json.loads(row["payload"])}
        if trial_id:
            row = self.connection.execute("SELECT id, payload FROM reference_records WHERE trial_id=?", (trial_id,)).fetchone()
            if row:
                return {"id": row["id"], "payload": json.loads(row["payload"])}
        return None

    def get_reference(self, reference_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT payload FROM reference_records WHERE id=?", (reference_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def set_reference_verification(self, reference_id: str, verification: dict[str, Any]) -> None:
        row = self.connection.execute("SELECT payload FROM reference_records WHERE id=?", (reference_id,)).fetchone()
        if not row:
            raise KeyError(f"Unknown reference: {reference_id}")
        if verification.get("verified") and verification.get("level") != "L1_identity_verified":
            raise ValidationError("Provider identity checks may record L1 only; content levels require separate review")
        payload = json.loads(row["payload"])
        payload["verification_depth"] = verification["level"] if verification.get("verified") else "L0_unverified"
        payload["verification_result"] = verification
        self.connection.execute("UPDATE reference_records SET payload=? WHERE id=?", (self._json(payload), reference_id))
        self.event(ProvenanceEvent("reference_verification_recorded", "reference", reference_id, verification))
        self.connection.commit()

    def attest_reference_verification(self, reference_id: str, *, level: str, reviewer: str,
                                      rationale: str, document_id: str | None = None,
                                      locator: str | None = None) -> None:
        """Record an explicit human attestation for content-level verification."""
        levels = {"L2_abstract_checked": 2, "L3_full_text_checked": 3, "L4_human_reviewed": 4}
        if level not in levels or not reviewer.strip() or not rationale.strip():
            raise ValueError("L2-L4 attestation requires a valid level, reviewer, and rationale")
        row = self.connection.execute("SELECT payload FROM reference_records WHERE id=?", (reference_id,)).fetchone()
        if not row:
            raise KeyError(f"Unknown reference: {reference_id}")
        payload = json.loads(row["payload"])
        if payload.get("verification_depth", "L0_unverified") == "L0_unverified":
            raise ValueError("L2-L4 require bibliographic identity to be verified first")
        if level == "L2_abstract_checked" and not payload.get("abstract"):
            raise ValueError("L2 requires an abstract stored with this reference")
        if levels[level] >= 3:
            doc = self.connection.execute("SELECT payload FROM source_documents WHERE id=? AND reference_id=?", (document_id, reference_id)).fetchone()
            if not doc:
                raise ValueError("L3/L4 requires a stored document for this reference")
            document = json.loads(doc["payload"])
            if document.get("access_level") != "full_text_extracted" or not document.get("text", "").strip() or not locator:
                raise ValueError("L3/L4 requires extracted full text and a specific evidence locator")
        if level == "L4_human_reviewed" and payload.get("verification_depth") != "L3_full_text_checked":
            raise ValueError("L4 requires an existing L3 full-text verification")
        payload["verification_depth"] = level
        payload["verification_attestation"] = {"reviewer": reviewer, "rationale": rationale,
                                                  "document_id": document_id, "locator": locator}
        self.connection.execute("UPDATE reference_records SET payload=? WHERE id=?", (self._json(payload), reference_id))
        self.event(ProvenanceEvent("reference_content_attested", "reference", reference_id,
                                   {"level": level, "reviewer": reviewer, "rationale": rationale,
                                    "document_id": document_id, "locator": locator}))
        self.connection.commit()

    def add_search(self, execution: Any, reference_ids: list[str]) -> None:
        payload = to_dict(execution)
        payload["result_count"] = len(reference_ids)
        payload["status"] = "completed"
        self.connection.execute(
            "INSERT INTO search_executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (payload["execution_id"], payload["provider"], payload["query"], payload["executed_at"],
             len(reference_ids), payload.get("status", "completed"), None, None, self._json(payload)),
        )
        for rank, reference_id in enumerate(reference_ids, 1):
            self.connection.execute("INSERT INTO search_results VALUES (?, ?, ?)",
                                    (payload["execution_id"], reference_id, rank))
        self.event(ProvenanceEvent("search_executed", "search", payload["execution_id"],
                                   {"provider": payload["provider"], "query": payload["query"], "count": len(reference_ids)}))
        self.connection.commit()

    def add_failed_search(self, *, execution_id: str, provider: str, query: str, executed_at: str,
                          error_category: str, error_message: str, parameters: dict[str, Any]) -> None:
        payload = {"execution_id": execution_id, "provider": provider, "query": query,
                   "executed_at": executed_at, "result_count": None, "status": "failed",
                   "error_category": error_category, "error_message": error_message,
                   "parameters": parameters}
        self.connection.execute("INSERT INTO search_executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (execution_id, provider, query, executed_at, None, "failed", error_category,
                                 error_message, self._json(payload)))
        self.event(ProvenanceEvent("search_failed", "search", execution_id,
                                   {"provider": provider, "query": query, "error_category": error_category}))
        self.connection.commit()

    def search_history(self) -> list[dict[str, Any]]:
        return [json.loads(row[0]) for row in self.connection.execute(
            "SELECT payload FROM search_executions ORDER BY executed_at, id")]

    def add_document(self, document: Any) -> None:
        item = to_dict(document)
        self.connection.execute("INSERT INTO source_documents VALUES (?, ?, ?, ?)",
                                (item["document_id"], item["reference_id"], item["access_level"], self._json(item)))
        self.event(ProvenanceEvent("document_ingested", "source_document", item["document_id"],
                                   {"reference_id": item["reference_id"], "access_level": item["access_level"]}))
        self.connection.commit()

    def add_evidence(self, evidence: Any) -> None:
        item = to_dict(evidence)
        self.connection.execute("INSERT INTO evidence VALUES (?, ?, ?)",
                                (item["evidence_id"], item["reference_id"], self._json(item)))
        self.event(ProvenanceEvent("evidence_extracted", "evidence", item["evidence_id"],
                                   {"reference_id": item["reference_id"], "extraction_method": item["extraction_method"]}))
        self.connection.commit()

    def add_claim(self, claim: Any) -> None:
        item = to_dict(claim)
        self.connection.execute("INSERT INTO claims VALUES (?, ?, ?)",
                                (item["claim_id"], item["claim_text"], self._json(item)))
        self.event(ProvenanceEvent("claim_created", "claim", item["claim_id"], {}))
        self.connection.commit()

    def add_claim_link(self, link: Any) -> None:
        item = to_dict(link)
        ref = self.get_reference(item["source_id"])
        if not ref:
            raise ValueError("Claim link source is not a stored reference")
        depth = item["verification_depth"]
        if depth in {"L1_identity_verified", "L2_abstract_checked", "L3_full_text_checked", "L4_human_reviewed"}:
            recorded = ref.get("verification_depth", "L0_unverified")
            allowed = {"L1_identity_verified": 1, "L2_abstract_checked": 2, "L3_full_text_checked": 3, "L4_human_reviewed": 4}
            if allowed.get(recorded, 0) < allowed[depth]:
                raise ValueError(f"Link verification depth {depth} exceeds the reference's recorded depth {recorded}")
        if depth in {"L3_full_text_checked", "L4_human_reviewed"}:
            doc_id = (item.get("evidence_location") or {}).get("document_id")
            doc = self.connection.execute("SELECT access_level FROM source_documents WHERE id=? AND reference_id=?", (doc_id, item["source_id"])).fetchone()
            if not doc or doc["access_level"] != "full_text_extracted":
                raise ValueError("L3/L4 requires a stored full-text document for this reference and a matching evidence location")
        if depth == "L4_human_reviewed" and item.get("human_review_status") != "approved":
            raise ValueError("L4 requires explicit human_review_status='approved'")
        self.connection.execute("INSERT INTO claim_links VALUES (?, ?, ?, ?, ?)",
                                (item["link_id"], item["claim_id"], item["source_id"],
                                 item["support_direction"], self._json(item)))
        self.event(ProvenanceEvent("claim_linked", "claim", item["claim_id"],
                                   {"source_id": item["source_id"], "support_direction": item["support_direction"]}))
        self.connection.commit()

    def add_review_decision(self, decision: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO review_decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (decision["decision_id"], decision["study_id"], decision["stage"], decision["reviewer"],
             decision["decision"], decision.get("rationale"), self._json(decision)),
        )
        self.event(ProvenanceEvent("review_decision_recorded", "study", decision["study_id"],
                                   {"stage": decision["stage"], "decision": decision["decision"],
                                    "reviewer": decision["reviewer"]}))
        self.connection.commit()

    def add_study_record(self, study: Any, *, mapped_by: str, rationale: str) -> str:
        item = to_dict(study)
        if not item.get("design", "").strip() or not mapped_by.strip() or not rationale.strip():
            raise ValidationError("Study design, mapper, and rationale are required")
        if not self.get_reference(item["reference_id"]):
            raise KeyError(f"Unknown report reference: {item['reference_id']}")
        self.connection.execute("INSERT INTO study_records VALUES (?, ?, ?)",
                                (item["study_id"], item["design"], self._json(item)))
        now = now_utc()
        self.connection.execute("INSERT INTO study_reports VALUES (?, ?, ?, ?, ?)",
                                (item["study_id"], item["reference_id"], mapped_by, rationale, now))
        self.event(ProvenanceEvent("study_record_created", "study", item["study_id"],
                                   {"initial_report_id": item["reference_id"], "mapped_by": mapped_by,
                                    "rationale": rationale}))
        self.connection.commit()
        return item["study_id"]

    def link_report_to_study(self, study_id: str, reference_id: str, *, mapped_by: str, rationale: str) -> None:
        if not mapped_by.strip() or not rationale.strip():
            raise ValidationError("Report-to-study mapping requires a reviewer and rationale")
        if not self.connection.execute("SELECT 1 FROM study_records WHERE id=?", (study_id,)).fetchone():
            raise KeyError(f"Unknown study: {study_id}")
        if not self.get_reference(reference_id):
            raise KeyError(f"Unknown report reference: {reference_id}")
        exists = self.connection.execute("SELECT 1 FROM study_reports WHERE study_id=? AND reference_id=?",
                                         (study_id, reference_id)).fetchone()
        if exists:
            return
        now = now_utc()
        self.connection.execute("INSERT INTO study_reports VALUES (?, ?, ?, ?, ?)",
                                (study_id, reference_id, mapped_by, rationale, now))
        self.event(ProvenanceEvent("report_linked_to_study", "study", study_id,
                                   {"reference_id": reference_id, "mapped_by": mapped_by, "rationale": rationale}))
        self.connection.commit()

    def study_ids_for_reports(self, reference_ids: set[str]) -> dict[str, list[str]]:
        if not reference_ids:
            return {}
        grouped: dict[str, list[str]] = {}
        requested = list(reference_ids)
        for start in range(0, len(requested), 500):
            chunk = requested[start:start + 500]
            placeholders = ",".join("?" for _ in chunk)
            rows = self.connection.execute(
                f"SELECT reference_id, study_id FROM study_reports WHERE reference_id IN ({placeholders})", tuple(chunk))
            for row in rows:
                grouped.setdefault(row["reference_id"], []).append(row["study_id"])
        return grouped

    def add_appraisal(self, assessment: Any, assessment_type: str, entity_id: str) -> None:
        item = to_dict(assessment)
        self.connection.execute("INSERT INTO appraisals VALUES (?, ?, ?, ?)",
                                (item.get("assessment_id"), assessment_type, entity_id, self._json(item)))
        self.event(ProvenanceEvent("appraisal_recorded", assessment_type, entity_id,
                                   {"assessment_id": item.get("assessment_id"), "reviewer": item.get("reviewer")}))
        self.connection.commit()

    def add_protocol(self, protocol: dict[str, Any]) -> None:
        from .models import new_id, now_utc
        protocol_id = protocol.setdefault("protocol_id", new_id("protocol"))
        protocol.setdefault("schema_version", "1.0")
        protocol.setdefault("version", "1")
        previous = self.connection.execute("SELECT id FROM systematic_protocols ORDER BY rowid DESC LIMIT 1").fetchone()
        if previous:
            protocol.setdefault("previous_protocol_id", previous["id"])
        saved_at = now_utc()
        self.connection.execute("INSERT INTO systematic_protocols VALUES (?, ?, ?, ?)",
                                (protocol_id, protocol["version"], self._json(protocol), saved_at))
        self.event(ProvenanceEvent("protocol_version_saved", "systematic_protocol", protocol_id,
                                   {"version": protocol["version"], "registration_id": protocol.get("registration_id")}))
        self.connection.commit()

    def create_manuscript(self, manuscript: Any) -> str:
        item = to_dict(manuscript)
        if item.get("schema_version") != "1.0":
            raise ValidationError("Unsupported manuscript schema version")
        if not item.get("title", "").strip() or not item.get("manuscript_type", "").strip():
            raise ValidationError("Manuscript title and type are required")
        self.connection.execute("INSERT INTO manuscript_projects VALUES (?, ?, ?, ?)",
                                (item["manuscript_id"], item["title"], item["manuscript_type"], self._json(item)))
        self.event(ProvenanceEvent("manuscript_project_created", "manuscript", item["manuscript_id"],
                                   {"manuscript_type": item["manuscript_type"]}))
        self.connection.commit()
        return item["manuscript_id"]

    def add_manuscript_section(self, section: Any, *, change_type: str, reason: str,
                               scientific_impact: str, edited_by: str,
                               editor_type: str = "human", human_confirmed: bool = False) -> dict[str, Any]:
        item = to_dict(section)
        if item.get("schema_version") != "1.0" or item.get("version") != "1":
            raise ValidationError("New manuscript sections must start at schema 1.0, version 1")
        if not item.get("text", "").strip() or not all(x.strip() for x in (change_type, reason, scientific_impact, edited_by)):
            raise ValidationError("Section text, change type, reason, scientific impact, and editor are required")
        if editor_type not in {"human", "ai"}:
            raise ValidationError("editor_type must be human or ai")
        if editor_type == "ai" and human_confirmed:
            raise ValidationError("AI edits cannot be marked human-confirmed")
        now = item.get("created_at") or now_utc()
        manuscript = self.connection.execute("SELECT 1 FROM manuscript_projects WHERE id=?", (item["manuscript_id"],)).fetchone()
        if not manuscript:
            raise KeyError(f"Unknown manuscript: {item['manuscript_id']}")
        digest = hashlib.sha256(item["text"].encode("utf-8")).hexdigest()
        self.connection.execute("INSERT INTO manuscript_sections VALUES (?, ?, ?, ?, ?)",
                                (item["section_id"], item["manuscript_id"], item["name"], 1, now))
        self.connection.execute("INSERT INTO manuscript_section_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (item["section_id"], 1, item["text"], change_type, reason, scientific_impact,
                                 edited_by, editor_type, int(human_confirmed), None, digest, now))
        self.event(ProvenanceEvent("manuscript_section_version_saved", "manuscript_section", item["section_id"],
                                   {"version": 1, "change_type": change_type, "scientific_impact": scientific_impact,
                                    "editor_type": editor_type, "human_confirmed": human_confirmed,
                                    "content_sha256": digest}))
        self.connection.commit()
        return self.get_manuscript_section(item["section_id"])

    def update_manuscript_section(self, section_id: str, text: str, *, change_type: str,
                                  reason: str, scientific_impact: str, edited_by: str,
                                  editor_type: str = "human", human_confirmed: bool = False) -> dict[str, Any]:
        if not text.strip() or not all(x.strip() for x in (change_type, reason, scientific_impact, edited_by)):
            raise ValidationError("Section text, change type, reason, scientific impact, and editor are required")
        if editor_type not in {"human", "ai"}:
            raise ValidationError("editor_type must be human or ai")
        if editor_type == "ai" and human_confirmed:
            raise ValidationError("AI edits cannot be marked human-confirmed")
        row = self.connection.execute("SELECT latest_version FROM manuscript_sections WHERE id=?", (section_id,)).fetchone()
        if not row:
            raise KeyError(f"Unknown manuscript section: {section_id}")
        previous_version = row["latest_version"]
        previous = self.connection.execute("SELECT text, content_sha256 FROM manuscript_section_versions WHERE section_id=? AND version=?",
                                            (section_id, previous_version)).fetchone()
        version = previous_version + 1
        from .models import now_utc
        now = now_utc()
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.connection.execute("INSERT INTO manuscript_section_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (section_id, version, text, change_type, reason, scientific_impact, edited_by,
                                 editor_type, int(human_confirmed), previous["content_sha256"], digest, now))
        self.connection.execute("UPDATE manuscript_sections SET latest_version=? WHERE id=?", (version, section_id))
        self.event(ProvenanceEvent("manuscript_section_version_saved", "manuscript_section", section_id,
                                   {"version": version, "change_type": change_type, "scientific_impact": scientific_impact,
                                    "editor_type": editor_type, "human_confirmed": human_confirmed,
                                    "previous_sha256": previous["content_sha256"], "content_sha256": digest}))
        self.connection.commit()
        result = self.get_manuscript_section(section_id)
        result["diff_from_previous"] = "".join(difflib.unified_diff(previous["text"].splitlines(keepends=True),
                                                                  text.splitlines(keepends=True),
                                                                  fromfile=f"version-{previous_version}",
                                                                  tofile=f"version-{version}"))
        return result

    def get_manuscript_section(self, section_id: str, version: int | None = None) -> dict[str, Any] | None:
        if version is None:
            row = self.connection.execute("SELECT s.id AS section_id, s.manuscript_id, s.name, v.version, v.text, "
                                           "v.change_type, v.reason, v.scientific_impact, v.edited_by, v.editor_type, "
                                           "v.human_confirmed, v.previous_sha256, v.content_sha256, v.created_at "
                                           "FROM manuscript_sections s JOIN manuscript_section_versions v "
                                           "ON v.section_id=s.id AND v.version=s.latest_version WHERE s.id=?",
                                           (section_id,)).fetchone()
        else:
            row = self.connection.execute("SELECT s.id AS section_id, s.manuscript_id, s.name, v.version, v.text, "
                                           "v.change_type, v.reason, v.scientific_impact, v.edited_by, v.editor_type, "
                                           "v.human_confirmed, v.previous_sha256, v.content_sha256, v.created_at "
                                           "FROM manuscript_sections s JOIN manuscript_section_versions v ON v.section_id=s.id "
                                           "WHERE s.id=? AND v.version=?", (section_id, version)).fetchone()
        result = dict(row) if row else None
        if result is not None:
            result["human_confirmed"] = bool(result["human_confirmed"])
        return result

    def list_manuscript_sections(self, manuscript_id: str) -> list[dict[str, Any]]:
        return [self.get_manuscript_section(row[0]) for row in self.connection.execute(
            "SELECT id FROM manuscript_sections WHERE manuscript_id=? ORDER BY created_at, id", (manuscript_id,))]

    def list_protocols(self) -> list[dict[str, Any]]:
        return [json.loads(row[0]) for row in self.connection.execute(
            "SELECT payload FROM systematic_protocols ORDER BY rowid")]

    def list_appraisals(self) -> list[dict[str, Any]]:
        return [json.loads(row[0]) for row in self.connection.execute("SELECT payload FROM appraisals ORDER BY rowid")]

    def list_references(self) -> list[dict[str, Any]]:
        return [json.loads(row[0]) for row in self.connection.execute("SELECT payload FROM reference_records ORDER BY title")]

    def events(self, *, entity_type: str | None = None, entity_id: str | None = None) -> list[dict[str, Any]]:
        query, params = "SELECT payload FROM provenance_events", []
        filters = []
        if entity_type:
            filters.append("entity_type=?")
            params.append(entity_type)
        if entity_id:
            filters.append("entity_id=?")
            params.append(entity_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY occurred_at, id"
        return [json.loads(row[0]) for row in self.connection.execute(query, params)]

    def count(self, table: str) -> int:
        allowed = {"references", "reference_records", "search_executions", "source_documents", "evidence", "claims", "claim_links", "review_decisions", "study_records", "study_reports", "appraisals", "systematic_protocols", "manuscript_projects", "manuscript_sections", "manuscript_section_versions"}
        if table not in allowed:
            raise ValueError("Unsupported project table")
        if table == "references":
            table = "reference_records"
        return int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
