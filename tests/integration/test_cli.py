import tempfile
import subprocess
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from biomedical_manuscript.cli import build_parser, run
from biomedical_manuscript.errors import NetworkError
from biomedical_manuscript.providers import EuropePMCProvider
from biomedical_manuscript.store import ProjectStore


class CliIntegrationTests(TestCase):
    def test_synthetic_end_to_end_examples_run_offline(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[2] / "examples" / "run_examples.py"),
                                     "--output-dir", folder], check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(folder) / "original-research-audit.json").exists())
            self.assertTrue((Path(folder) / "narrative-review-matrix.json").exists())
            self.assertTrue((Path(folder) / "systematic-review-flow.json").exists())
            self.assertTrue((Path(folder) / "meta-analysis-forest.svg").exists())

    def test_manuscript_cli_persists_section_and_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "p.sqlite"
            created = run(build_parser().parse_args([
                "--db", str(db), "manuscript", "create", "Synthetic study", "original_research"]))
            draft = Path(folder) / "results.md"
            draft.write_text("Estimate: 1.2", encoding="utf-8")
            saved = run(build_parser().parse_args([
                "--db", str(db), "manuscript", "section-add", created["manuscript_id"], "Results", str(draft),
                "--editor", "author", "--reason", "Initial author draft", "--scientific-impact", "Not yet assessed"]))
            draft.write_text("Estimate: 1.3", encoding="utf-8")
            updated = run(build_parser().parse_args([
                "--db", str(db), "manuscript", "section-update", saved["section_id"], str(draft),
                "--editor", "author", "--change-type", "numerical_correction", "--reason", "Checked against analysis",
                "--scientific-impact", "Changes estimate", "--human-confirmed"]))
            self.assertEqual(updated["version"], 2)
            self.assertIn("-Estimate: 1.2", updated["diff_from_previous"])

    def test_zero_results_is_a_completed_execution(self):
        class EmptyProvider:
            def search(self, query, *, max_results=20):
                return []
        with tempfile.TemporaryDirectory() as folder, patch.dict("biomedical_manuscript.cli.PROVIDERS", {"test": EmptyProvider}):
            args = build_parser().parse_args(["--db", str(Path(folder) / "p.sqlite"), "search", "test", "topic"])
            result = run(args)
            store = ProjectStore(Path(folder) / "p.sqlite")
            history = store.search_history()
            store.close()
        self.assertEqual(result["provider_returned_count"], 0)
        self.assertEqual(history[0]["status"], "completed")
        self.assertEqual(history[0]["result_count"], 0)

    def test_network_failure_is_stored_as_failure_and_not_zero(self):
        class BrokenProvider:
            def search(self, query, *, max_results=20):
                raise NetworkError("offline")
        with tempfile.TemporaryDirectory() as folder, patch.dict("biomedical_manuscript.cli.PROVIDERS", {"test": BrokenProvider}):
            db = Path(folder) / "p.sqlite"
            args = build_parser().parse_args(["--db", str(db), "search", "test", "topic"])
            with self.assertRaises(NetworkError):
                run(args)
            store = ProjectStore(db)
            history = store.search_history()
            store.close()
        self.assertEqual(history[0]["status"], "failed")
        self.assertIsNone(history[0]["result_count"])

    def test_trial_identifier_deduplicates_trial_registry_records(self):
        from biomedical_manuscript.models import ReferenceRecord
        with tempfile.TemporaryDirectory() as folder:
            store = ProjectStore(Path(folder) / "p.sqlite")
            first = store.add_reference(ReferenceRecord("Trial title", trial_id="NCT00000001"))
            second = store.add_reference(ReferenceRecord("Same trial, updated registry title", trial_id="NCT00000001"))
            self.assertEqual(first, second)
            store.close()
