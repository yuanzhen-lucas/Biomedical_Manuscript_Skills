"""Command-line entry point for local evidence and manuscript workflows."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import __version__
from .audits import audit_manuscript, compare_numeric_tokens
from .appraisal import create_certainty_assessment, create_risk_of_bias
from .documents import ingest_document
from .errors import BiomedicalError
from .evidence import extract_evidence, link_claim
from .meta import StudyEffect, analyze, forest_plot_svg
from .models import EvidenceClaim, ManuscriptProject, ManuscriptSection, ReferenceRecord, StudyRecord, VerificationDepth, to_dict
from .providers import PROVIDERS, SearchExecution
from .references import find_duplicates, import_references, normalize_reference, verify_doi, verify_pmid
from .reporting import load_registry, reporting_audit, route_guidelines
from .store import ProjectStore
from .submission import draft_reviewer_response, submission_readiness
from .systematic import derive_flow, record_decision, save_protocol


def _json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=lambda x: x.value if hasattr(x, "value") else str(x))


def _store(args: argparse.Namespace) -> ProjectStore:
    return ProjectStore(getattr(args, "db", None) or "biomedical-project.sqlite3")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="biomed", description="Evidence-centric biomedical manuscript workflows")
    parser.add_argument("--version", action="version", version=f"biomed {__version__}")
    parser.add_argument("--db", default="biomedical-project.sqlite3", help="Local project database (default: ./biomedical-project.sqlite3)")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="Initialize a private local project database")

    search = commands.add_parser("search", help="Search a configured public metadata provider")
    search.add_argument("provider", choices=sorted(PROVIDERS))
    search.add_argument("query")
    search.add_argument("--max-results", type=int, default=20)
    commands.add_parser("search-history", help="Inspect completed and failed search executions")

    refs = commands.add_parser("references", help="Reference import, verification, and listing")
    ref_cmds = refs.add_subparsers(dest="references_command", required=True)
    imp = ref_cmds.add_parser("import", help="Import RIS, NBIB, BibTeX, CSV, JSON, or PubMed XML")
    imp.add_argument("file")
    ref_cmds.add_parser("list", help="List stored references")
    verify = ref_cmds.add_parser("verify", help="Verify bibliographic identity via Crossref")
    verify.add_argument("reference_id")
    attest = ref_cmds.add_parser("attest", help="Record an explicitly human-checked abstract/full text")
    attest.add_argument("reference_id")
    attest.add_argument("level", choices=["L2_abstract_checked", "L3_full_text_checked", "L4_human_reviewed"])
    attest.add_argument("--reviewer", required=True)
    attest.add_argument("--rationale", required=True)
    attest.add_argument("--document-id")
    attest.add_argument("--locator")

    ingest = commands.add_parser("ingest", help="Ingest a user-selected local text or PDF file")
    ingest.add_argument("reference_id")
    ingest.add_argument("file")

    evidence = commands.add_parser("evidence", help="Store human/model-assisted evidence extracts")
    evidence_cmd = evidence.add_subparsers(dest="evidence_command", required=True)
    eadd = evidence_cmd.add_parser("add")
    eadd.add_argument("reference_id")
    eadd.add_argument("text")
    eadd.add_argument("--document-id")
    eadd.add_argument("--locator")
    eadd.add_argument("--quote")
    eadd.add_argument("--study-design")
    eadd.add_argument("--population")
    eadd.add_argument("--outcome")
    eadd.add_argument("--result")
    eadd.add_argument("--limitation", action="append", default=[])

    claim = commands.add_parser("claim", help="Create claims and claim-source links")
    claim_cmd = claim.add_subparsers(dest="claim_command", required=True)
    cadd = claim_cmd.add_parser("add")
    cadd.add_argument("text")
    cadd.add_argument("--type", default="background")
    cadd.add_argument("--section")
    cadd.add_argument("--study-context")
    clink = claim_cmd.add_parser("link")
    clink.add_argument("claim_id")
    clink.add_argument("reference_id")
    clink.add_argument("support", choices=["supports", "partially_supports", "contradicts", "mixed", "unclear", "not_applicable"])
    clink.add_argument("--verification", choices=[e.value for e in VerificationDepth], default=VerificationDepth.L0.value)
    clink.add_argument("--document-id")
    clink.add_argument("--locator")
    clink.add_argument("--directness", default="unknown")
    clink.add_argument("--human-review", default="not_reviewed")
    claim_cmd.add_parser("matrix", help="List saved claims and mapped sources")

    audit = commands.add_parser("audit", help="Run rule-based manuscript triage")
    audit.add_argument("file")
    audit.add_argument("--study-design")
    audit.add_argument("--model-level")
    audit.add_argument("--type", default="original_research")
    audit.add_argument("--compare", help="Optional second section file for numeric token comparison")

    guidelines = commands.add_parser("guidelines", help="Discover or assess reporting checklist completeness")
    guide_cmd = guidelines.add_subparsers(dest="guidelines_command", required=True)
    route = guide_cmd.add_parser("route")
    route.add_argument("study_design")
    route.add_argument("--feature", action="append", default=[])
    gaudit = guide_cmd.add_parser("audit")
    gaudit.add_argument("guideline_id")
    gaudit.add_argument("items_json", help="JSON object mapping item IDs to assessment statuses")
    gaudit.add_argument("--source-verified", action="store_true")
    guide_cmd.add_parser("list")

    screen = commands.add_parser("screen", help="Record one screening decision")
    screen.add_argument("reference_id")
    screen.add_argument("stage", choices=["title_abstract", "full_text"])
    screen.add_argument("decision", choices=["include", "exclude", "uncertain"])
    screen.add_argument("--reviewer", required=True)
    screen.add_argument("--reviewer-type", choices=["human", "ai"], default="human")
    screen.add_argument("--rationale")
    screen.add_argument("--exclusion-reason")
    screen.add_argument("--round-id")

    systematic = commands.add_parser("systematic", help="Report saved screening and PRISMA-style flow state")
    systematic_cmd = systematic.add_subparsers(dest="systematic_command", required=True)
    flow = systematic_cmd.add_parser("flow")
    flow.add_argument("--identified-json", help="Optional source-name to imported count JSON")
    flow.add_argument("--duplicates-removed", type=int)
    protocol = systematic_cmd.add_parser("protocol-save")
    protocol.add_argument("file", help="JSON protocol file")
    systematic_cmd.add_parser("protocol-list")
    study_create = systematic_cmd.add_parser("study-create", help="Create a study group around an included report")
    study_create.add_argument("reference_id")
    study_create.add_argument("design")
    study_create.add_argument("--mapped-by", required=True)
    study_create.add_argument("--rationale", required=True)
    study_link = systematic_cmd.add_parser("study-link", help="Link another report to an existing study")
    study_link.add_argument("study_id")
    study_link.add_argument("reference_id")
    study_link.add_argument("--mapped-by", required=True)
    study_link.add_argument("--rationale", required=True)

    appraisal = commands.add_parser("appraise", help="Record a human-led risk-of-bias or certainty assessment")
    appraisal_cmd = appraisal.add_subparsers(dest="appraisal_command", required=True)
    rob = appraisal_cmd.add_parser("risk-of-bias")
    rob.add_argument("study_id")
    rob.add_argument("instrument")
    rob.add_argument("judgments_json")
    rob.add_argument("rationale_json")
    rob.add_argument("--reviewer", required=True)
    rob.add_argument("--reviewer-type", choices=["human", "ai"], default="human")
    rob.add_argument("--human-review-status", choices=["not_reviewed", "review_requested", "reviewed", "approved", "rejected", "needs_revision"], default="not_reviewed")
    certainty = appraisal_cmd.add_parser("certainty")
    certainty.add_argument("outcome_id")
    certainty.add_argument("framework")
    certainty.add_argument("certainty")
    certainty.add_argument("domains_json")
    certainty.add_argument("rationale")
    certainty.add_argument("--reviewer", required=True)

    meta = commands.add_parser("meta", help="Generic inverse-variance meta-analysis")
    meta_cmd = meta.add_subparsers(dest="meta_command", required=True)
    analyze_cmd = meta_cmd.add_parser("analyze")
    analyze_cmd.add_argument("input_json", help="JSON array of study_id/effect/standard_error/outcome_id objects")
    analyze_cmd.add_argument("--model", choices=["fixed", "random"], default="random")
    analyze_cmd.add_argument("--output", help="Optional JSON output file")
    analyze_cmd.add_argument("--forest-svg", help="Optional forest plot SVG output path")

    response = commands.add_parser("review-response", help="Prepare a response-to-reviewers record")
    response.add_argument("comment")
    response.add_argument("--action")
    response.add_argument("--location")
    response.add_argument("--evidence-of-change")

    readiness = commands.add_parser("submission-check", help="Check gates; does not submit or transmit files")
    readiness.add_argument("--journal-url")
    readiness.add_argument("--journal-checked-at")
    readiness.add_argument("--journal-source-verified", action="store_true")
    readiness.add_argument("--finding", action="append", default=[])
    readiness.add_argument("--human-approval", choices=["not_reviewed", "reviewed", "approved", "rejected"], default="not_reviewed")
    readiness.add_argument("--allow-external-transfer", action="store_true")

    manuscript = commands.add_parser("manuscript", help="Create a manuscript workspace and preserve section revisions")
    manuscript_cmd = manuscript.add_subparsers(dest="manuscript_command", required=True)
    ms_create = manuscript_cmd.add_parser("create")
    ms_create.add_argument("title")
    ms_create.add_argument("manuscript_type", choices=["original_research", "narrative_review", "systematic_review", "scoping_review", "meta_analysis", "revision"])
    ms_create.add_argument("--journal")
    section_add = manuscript_cmd.add_parser("section-add")
    section_add.add_argument("manuscript_id")
    section_add.add_argument("name")
    section_add.add_argument("file")
    section_add.add_argument("--editor", required=True)
    section_add.add_argument("--editor-type", choices=["human", "ai"], default="human")
    section_add.add_argument("--change-type", default="initial")
    section_add.add_argument("--reason", required=True)
    section_add.add_argument("--scientific-impact", required=True)
    section_add.add_argument("--human-confirmed", action="store_true")
    section_update = manuscript_cmd.add_parser("section-update")
    section_update.add_argument("section_id")
    section_update.add_argument("file")
    section_update.add_argument("--editor", required=True)
    section_update.add_argument("--editor-type", choices=["human", "ai"], default="human")
    section_update.add_argument("--change-type", required=True)
    section_update.add_argument("--reason", required=True)
    section_update.add_argument("--scientific-impact", required=True)
    section_update.add_argument("--human-confirmed", action="store_true")
    section_list = manuscript_cmd.add_parser("section-list")
    section_list.add_argument("manuscript_id")
    return parser


def run(args: argparse.Namespace) -> object:
    if args.command == "init":
        store = _store(args)
        store.close()
        return {"status": "initialized", "database": str(Path(args.db).expanduser().resolve()), "privacy": "local-only"}
    if args.command == "guidelines":
        if args.guidelines_command == "list":
            return load_registry()
        if args.guidelines_command == "route":
            return route_guidelines(study_design=args.study_design, study_features=args.feature)
        status = json.loads(args.items_json)
        return reporting_audit(args.guideline_id, status, live_source_verified=args.source_verified)
    if args.command == "audit":
        text = Path(args.file).read_text(encoding="utf-8")
        findings = [to_dict(x) for x in audit_manuscript(text, study_design=args.study_design,
                                                        model_level=args.model_level, research_type=args.type)]
        if args.compare:
            other = Path(args.compare).read_text(encoding="utf-8")
            findings += [to_dict(x) for x in compare_numeric_tokens(text, other)]
        return {"status": "triage_only_human_review_required", "findings": findings}
    if args.command == "meta":
        payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        effects = [StudyEffect(**row) for row in payload]
        result = analyze(effects, model=args.model)
        if args.output:
            Path(args.output).write_text(_json(result) + "\n", encoding="utf-8")
        if args.forest_svg:
            Path(args.forest_svg).write_text(forest_plot_svg(result), encoding="utf-8")
        return result
    if args.command == "review-response":
        return draft_reviewer_response(reviewer_comment=args.comment, author_verified_action=args.action,
                                       manuscript_location=args.location, evidence_of_change=args.evidence_of_change)
    if args.command == "submission-check":
        return submission_readiness(journal_instructions_url=args.journal_url,
                                    journal_instructions_checked_at=args.journal_checked_at,
                                    journal_instructions_source_verified=args.journal_source_verified,
                                    unresolved_findings=args.finding, human_approval=args.human_approval,
                                    consent_to_external_transfer=args.allow_external_transfer)
    if args.command == "manuscript" and args.manuscript_command == "create":
        store = _store(args)
        try:
            obj = ManuscriptProject(title=args.title, manuscript_type=args.manuscript_type,
                                    target_journal=args.journal)
            manuscript_id = store.create_manuscript(obj)
            return {"manuscript_id": manuscript_id, "title": args.title,
                    "manuscript_type": args.manuscript_type, "local_only": True}
        finally:
            store.close()
    if args.command == "appraise":
        store = _store(args)
        try:
            if args.appraisal_command == "risk-of-bias":
                assessment = create_risk_of_bias(study_id=args.study_id, instrument=args.instrument,
                                                 domains=json.loads(Path(args.judgments_json).read_text(encoding="utf-8")),
                                                 rationale=json.loads(Path(args.rationale_json).read_text(encoding="utf-8")),
                                                 reviewer=args.reviewer, reviewer_type=args.reviewer_type,
                                                 human_review_status=args.human_review_status)
                store.add_appraisal(assessment, "risk_of_bias", args.study_id)
            else:
                assessment = create_certainty_assessment(outcome_id=args.outcome_id, framework=args.framework,
                                                         certainty=args.certainty,
                                                         domains=json.loads(Path(args.domains_json).read_text(encoding="utf-8")),
                                                         rationale=args.rationale, reviewer=args.reviewer)
                store.add_appraisal(assessment, "evidence_certainty", args.outcome_id)
            return to_dict(assessment)
        finally:
            store.close()

    store = _store(args)
    try:
        if args.command == "manuscript":
            if args.manuscript_command == "section-list":
                return store.list_manuscript_sections(args.manuscript_id)
            if args.manuscript_command == "section-add":
                text = Path(args.file).read_text(encoding="utf-8")
                section = ManuscriptSection(manuscript_id=args.manuscript_id, name=args.name, text=text)
                return store.add_manuscript_section(section, change_type=args.change_type, reason=args.reason,
                                                    scientific_impact=args.scientific_impact, edited_by=args.editor,
                                                    editor_type=args.editor_type, human_confirmed=args.human_confirmed)
            text = Path(args.file).read_text(encoding="utf-8")
            return store.update_manuscript_section(args.section_id, text, change_type=args.change_type,
                                                  reason=args.reason, scientific_impact=args.scientific_impact,
                                                  edited_by=args.editor, editor_type=args.editor_type,
                                                  human_confirmed=args.human_confirmed)
        if args.command == "search":
            provider = PROVIDERS[args.provider]()
            execution_id = f"search_{uuid4().hex}"
            executed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            try:
                refs = [normalize_reference(record) for record in provider.search(args.query, max_results=args.max_results)]
            except BiomedicalError as exc:
                store.add_failed_search(execution_id=execution_id, provider=args.provider, query=args.query,
                                        executed_at=executed_at, error_category=exc.category,
                                        error_message=str(exc), parameters={"max_results": args.max_results})
                raise
            ids = [store.add_reference(ref, event_type="search_result_imported") for ref in refs]
            unique_ids = list(dict.fromkeys(ids))
            execution = SearchExecution(provider=args.provider, query=args.query,
                                        executed_at=executed_at, result_ids=unique_ids,
                                        parameters={"max_results": args.max_results, "provider_returned_count": len(refs)},
                                        execution_id=execution_id)
            store.add_search(execution, unique_ids)
            return {"provider": args.provider, "provider_returned_count": len(refs),
                    "unique_reference_count": len(unique_ids), "reference_ids": unique_ids,
                    "execution_id": execution.execution_id, "verification": "search results are unverified metadata until checked"}
        if args.command == "references":
            if args.references_command == "list":
                return store.list_references()
            if args.references_command == "import":
                records = [normalize_reference(x) for x in import_references(args.file)]
                duplicates = find_duplicates(records)
                ids = [store.add_reference(x) for x in records]
                return {"imported_records": len(ids), "reference_ids": ids, "duplicate_candidates": duplicates}
            if args.references_command == "attest":
                store.attest_reference_verification(args.reference_id, level=args.level, reviewer=args.reviewer,
                                                    rationale=args.rationale, document_id=args.document_id,
                                                    locator=args.locator)
                return {"reference_id": args.reference_id, "verification_depth": args.level,
                        "human_attestation_recorded": True}
            ref = store.get_reference(args.reference_id)
            if not ref:
                raise ValueError(f"Unknown reference: {args.reference_id}")
            if not ref.get("doi"):
                if ref.get("pmid"):
                    result = verify_pmid(ref["pmid"], expected_title=ref["title"])
                    store.set_reference_verification(args.reference_id, result)
                    return result
                return {"verified": False, "reason": "reference_has_no_supported_identifier", "level": "L0_unverified"}
            result = verify_doi(ref["doi"], expected_title=ref["title"])
            store.set_reference_verification(args.reference_id, result)
            return result
        if args.command == "search-history":
            return store.search_history()
        if args.command == "ingest":
            document = ingest_document(args.file, args.reference_id)
            if not store.get_reference(args.reference_id):
                raise ValueError(f"Unknown reference: {args.reference_id}")
            store.add_document(document)
            return to_dict(document)
        if args.command == "evidence" and args.evidence_command == "add":
            if not store.get_reference(args.reference_id):
                raise ValueError(f"Unknown reference: {args.reference_id}")
            evidence_item = extract_evidence(args.reference_id, args.text, document_id=args.document_id,
                                             locator=args.locator, quote=args.quote,
                                             study_design=args.study_design, population=args.population,
                                             outcome=args.outcome, result=args.result, limitations=args.limitation)
            store.add_evidence(evidence_item)
            return to_dict(evidence_item)
        if args.command == "claim":
            if args.claim_command == "add":
                obj = EvidenceClaim(claim_text=args.text, claim_type=args.type,
                                    manuscript_section=args.section, study_context=args.study_context)
                store.add_claim(obj)
                return to_dict(obj)
            if args.claim_command == "matrix":
                claims = [json.loads(row[0]) for row in store.connection.execute("SELECT payload FROM claims ORDER BY rowid")]
                links = [json.loads(row[0]) for row in store.connection.execute("SELECT payload FROM claim_links ORDER BY rowid")]
                by_claim = {}
                for item in links:
                    by_claim.setdefault(item["claim_id"], []).append(item)
                return [{"claim_id": item["claim_id"], "claim": item["claim_text"],
                         "claim_type": item["claim_type"], "section": item["manuscript_section"],
                         "epistemic_status": item["epistemic_status"],
                         "sources": [{"source_id": link["source_id"], "support_direction": link["support_direction"],
                                      "verification_depth": link["verification_depth"],
                                      "directness": link["directness"],
                                      "evidence_location": (link.get("evidence_location") or {}).get("locator")}
                                     for link in by_claim.get(item["claim_id"], [])],
                         "status": "unlinked" if not by_claim.get(item["claim_id"]) else "linkage_recorded_not_semantically_verified"}
                        for item in claims]
            from .models import EvidenceLocation
            location = EvidenceLocation(args.document_id, "user_supplied", args.locator) if args.document_id and args.locator else None
            link = link_claim(args.claim_id, args.reference_id, args.support, verification_depth=args.verification,
                              directness=args.directness, locator=location, human_review_status=args.human_review)
            store.add_claim_link(link)
            return {**to_dict(link), "semantic_support_verified": False}
        if args.command == "screen":
            return record_decision(store, study_id=args.reference_id, stage=args.stage, reviewer=args.reviewer,
                                   decision=args.decision, rationale=args.rationale,
                                   exclusion_reason=args.exclusion_reason, reviewer_type=args.reviewer_type,
                                   round_id=args.round_id)
        if args.command == "systematic":
            if args.systematic_command == "protocol-list":
                return store.list_protocols()
            if args.systematic_command == "protocol-save":
                protocol_data = json.loads(Path(args.file).read_text(encoding="utf-8"))
                return save_protocol(store, protocol_data)
            if args.systematic_command == "study-create":
                study = StudyRecord(reference_id=args.reference_id, design=args.design)
                study_id = store.add_study_record(study, mapped_by=args.mapped_by, rationale=args.rationale)
                return {"study_id": study_id, "initial_report_id": args.reference_id,
                        "mapping_status": "human_recorded"}
            if args.systematic_command == "study-link":
                store.link_report_to_study(args.study_id, args.reference_id, mapped_by=args.mapped_by,
                                           rationale=args.rationale)
                return {"study_id": args.study_id, "report_id": args.reference_id,
                        "mapping_status": "human_recorded"}
            identified = json.loads(Path(args.identified_json).read_text(encoding="utf-8")) if args.identified_json else None
            return derive_flow(store, records_identified_by_source=identified, duplicates_removed=args.duplicates_removed)
    finally:
        store.close()
    return {}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except (BiomedicalError, ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(_json({"status": "error", "category": getattr(exc, "category", "input_or_io_error"), "message": str(exc)}), file=sys.stderr)
        return 2
    print(_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
