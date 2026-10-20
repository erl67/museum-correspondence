from copy import deepcopy
import csv
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from correspondence.cli import main
from correspondence.discovery import discover
from correspondence.execution import Quota, transcribe
from correspondence.exports import cell, export_all
from correspondence.images import prepare_request
from correspondence.profiles import load_profile, register_profile
from correspondence.review import apply_review, current_records, people
from correspondence.storage import atomic_json, read_json
from .helpers import Workspace, FakeTransport, Clock, jpeg, response


class ReviewExportTests(Workspace):
    def setUp(self):
        super().setUp()
        self.setup_letter()
        clock = Clock()
        self.result, _ = transcribe(self.store, self.letter, self.request, self.config,
                                   lambda: FakeTransport([response(self.doc)]),
                                   quota=Quota(self.config, clock.time, clock.sleep))

    def review(self, **kwargs):
        return apply_review(self.store, self.inventory, dict(kind="letter", letter_id=self.letter["letter_id"],
                            base_revision=self.result["revision_id"], source="synthetic staff check", **kwargs))

    def test_review_layers_do_not_modify_original(self):
        iid = self.letter["image_ids"][0]
        original = deepcopy(self.store.results())
        self.review(pages={iid: {"text": "Human correction: café\n00012"}}, transcription_review="approved")
        export_all(self.store, self.inventory, self.root / "exports")
        record = current_records(self.store, self.inventory)[0]
        self.assertEqual(record["document"]["pages"][0]["text"], "Human correction: café\n00012")
        self.assertEqual(record["transcription_review"], "approved")
        self.assertEqual(record["metadata_review"], "in_progress")
        self.assertEqual(self.store.results(), original)
        export_all(self.store, self.inventory, self.root / "exports")
        self.assertEqual(current_records(self.store, self.inventory)[0]["transcription_review"], "approved")

    def test_metadata_approval_not_transcription_approval(self):
        self.review(metadata_review="approved")
        record = current_records(self.store, self.inventory)[0]
        self.assertEqual(record["metadata_review"], "approved")
        self.assertEqual(record["transcription_review"], "unreviewed")

    def test_later_changes_do_not_inherit_prior_approval(self):
        self.review(metadata_review="approved", transcription_review="approved", relationship_review="approved")
        self.review(pages={self.letter["image_ids"][0]: {"text": "Another synthetic correction"}})
        record = current_records(self.store, self.inventory)[0]
        self.assertEqual(record["transcription_review"], "in_progress")
        self.assertEqual(record["metadata_review"], "in_progress")
        self.assertEqual(record["relationship_review"], "in_progress")
        self.review(metadata_review="approved", transcription_review="approved", relationship_review="approved")
        self.review(metadata={"sender": self.doc["metadata"]["sender"]})
        record = current_records(self.store, self.inventory)[0]
        self.assertEqual(record["transcription_review"], "approved")
        self.assertEqual(record["metadata_review"], "in_progress")
        self.assertEqual(record["relationship_review"], "in_progress")

    def test_new_revision_preserves_but_does_not_misapply_review(self):
        self.review(metadata_review="approved")
        newer = deepcopy(self.result)
        newer["revision_id"] = "rev_later"
        self.store.append("result", newer)
        record = current_records(self.store, self.inventory)[0]
        self.assertEqual(record["metadata_review"], "unreviewed")
        self.assertEqual(len(record["stale_reviews"]), 1)

    def test_replaced_scan_marks_old_reading_and_review_stale(self):
        self.review(transcription_review="approved")
        jpeg(self.inputs / self.inventory["images"][0]["path"], "red")
        updated = discover(self.inputs, self.inventory)
        record = current_records(self.store, updated)[0]
        self.assertEqual(record["execution"], "stale")
        self.assertEqual(record["transcription_review"], "unreviewed")

    def test_review_requires_current_revision_and_source(self):
        with self.assertRaises(ValueError):
            apply_review(self.store, self.inventory, {"kind": "letter", "source": "x",
                          "letter_id": self.letter["letter_id"], "base_revision": "old"})
        with self.assertRaises(ValueError):
            apply_review(self.store, self.inventory, {"kind": "person"})

    def test_approved_people_and_aliases_remain_distinct(self):
        a = apply_review(self.store, self.inventory, dict(kind="person", name="Person Alpha", aliases=["A."],
                        review_status="approved", source="synthetic authority file"))["data"]
        b = apply_review(self.store, self.inventory, dict(kind="person", name="Person Beta", aliases=["A."],
                        review_status="approved", source="synthetic authority file"))["data"]
        self.assertNotEqual(a["person_id"], b["person_id"])
        self.assertEqual(len(people(self.store)), 2)
        field = deepcopy(self.doc["metadata"]["sender"])
        field["person_id"] = a["person_id"]
        self.review(metadata={"sender": field})
        self.assertEqual(current_records(self.store, self.inventory)[0]["document"]["metadata"]["sender"]["person_id"], a["person_id"])

    def test_spreadsheet_formula_safety_and_unicode(self):
        for dangerous in ("=1+1", "+123", "-12", "@x", "\ttext", "  =HYPERLINK()"):
            self.assertTrue(cell(dangerous).startswith("'"))
        self.assertEqual(cell("00123"), "00123")
        self.assertEqual(cell("café\ncontinuation"), "café\ncontinuation")
        self.review(summary="=SYNTHETIC()\ncafé 00123")
        export_all(self.store, self.inventory, self.root / "exports")
        with (self.root / "exports" / "catalogue.csv").open(encoding="utf-8-sig", newline="") as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(row["summary"], "'=SYNTHETIC()\ncafé 00123")
        canonical = read_json(self.root / "exports" / "records.json")
        self.assertEqual(canonical["records"][0]["document"]["summary"], "=SYNTHETIC()\ncafé 00123")

    def test_reports_page_boundaries_and_offline_exports(self):
        before = self.store.journal.read_bytes()
        with patch("correspondence.provider.Gemini.send", side_effect=AssertionError("network forbidden")):
            export_all(self.store, self.inventory, self.root / "exports")
        self.assertEqual(before, self.store.journal.read_bytes())
        report = (self.root / "exports" / "letters" / (self.letter["letter_id"] + ".txt")).read_text(encoding="utf-8")
        for iid in self.letter["image_ids"]:
            self.assertIn(f"=== PAGE {iid}", report)
        self.assertIn("TECHNICAL PROVENANCE", report)
        bundle = read_json(self.root / "exports" / "viewer.json")
        self.assertTrue(all(s["mapping_status"] == "missing_mapping" for s in bundle["letters"][0]["scans"]))

    def test_export_rejects_source_directory(self):
        with self.assertRaises(ValueError):
            export_all(self.store, self.inventory, self.inputs / "reports")

    def test_drive_mapping_requires_real_format_and_hash(self):
        iid = self.letter["image_ids"][0]
        with self.assertRaises(ValueError):
            export_all(self.store, self.inventory, self.root / "exports",
                       {"version": 1, "images": {iid: {"file_id": "synthetic-id-123", "original_sha256": "wrong"}}})
        mapping = {"version": 1, "images": {iid: {"file_id": "synthetic-id-123",
                    "original_sha256": self.inventory["images"][0]["sha256"]}}}
        export_all(self.store, self.inventory, self.root / "exports", mapping)
        scan = read_json(self.root / "exports" / "viewer.json")["letters"][0]["scans"][0]
        self.assertEqual(scan["drive_file_id"], "synthetic-id-123")

    def test_unprocessed_and_failed_in_catalogue(self):
        from correspondence.storage import Store
        store = Store(self.root / "empty")
        store.append("inventory", self.inventory)
        export_all(store, self.inventory, self.root / "exports")
        bundle = read_json(self.root / "exports" / "viewer.json")
        self.assertEqual(bundle["letters"][0]["execution"], "unprocessed")
        failed = dict(self.result, execution="failed", text="partial original", document=None)
        store.append("result", failed)
        export_all(store, self.inventory, self.root / "exports")
        self.assertEqual(read_json(self.root / "exports" / "viewer.json")["letters"][0]["partial_response"], "partial original")


class ProfileTests(Workspace):
    def setUp(self):
        super().setUp()
        self.setup_letter()
        self.profile = dict(schema_version=1, profile_id="hand_synthetic", version="1",
                            hand_description="Synthetic example hand, period unknown", reviewer="Test",
                            review_status="approved", notes=["Read the loop carefully."],
                            examples=[dict(image_id=self.letter["image_ids"][0], source_sha256="a" * 64,
                                           region="top-left address", transcription="SYNTHETIC",
                                           reviewer="Test", review_status="verified")])
        self.path = self.root / "profile.json"

    def test_optional_profile_and_fingerprint_versioning(self):
        atomic_json(self.path, self.profile)
        profile = load_profile(self.path)
        first = prepare_request(self.inventory, self.letter, self.config, profile)
        first_snapshot = deepcopy(first["provenance"])
        self.assertNotEqual(first["fingerprint"], self.request["fingerprint"])
        profile["version"] = "2"
        second = prepare_request(self.inventory, self.letter, self.config, profile)
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(first["provenance"], first_snapshot)
        self.assertIn("SYNTHETIC", second["provenance"]["prompt"])
        self.assertIsNone(load_profile(None))

    def test_unreviewed_or_oversize_profiles_rejected(self):
        for field in ("review_status",):
            invalid = dict(self.profile, **{field: "unreviewed"})
            atomic_json(self.path, invalid)
            with self.assertRaises(ValueError):
                load_profile(self.path)
        invalid = deepcopy(self.profile)
        invalid["examples"][0]["review_status"] = "model_generated"
        atomic_json(self.path, invalid)
        with self.assertRaises(ValueError):
            load_profile(self.path)
        atomic_json(self.path, dict(self.profile, examples=self.profile["examples"] * 6))
        with self.assertRaises(ValueError):
            load_profile(self.path)

    def test_same_version_cannot_change_and_batches_are_isolated(self):
        atomic_json(self.path, self.profile)
        frozen = load_profile(self.path)
        register_profile(self.store, frozen)
        changed = dict(self.profile, notes=["Changed later"])
        atomic_json(self.path, changed)
        self.assertEqual(frozen["notes"], ["Read the loop carefully."])
        with self.assertRaises(ValueError):
            register_profile(self.store, load_profile(self.path))
        self.assertIsNone(prepare_request(self.inventory, self.letter, self.config)["provenance"]["handwriting_profile"])


class CliTests(Workspace):
    def test_transcribe_export_failure_then_resume_reuses_checkpoint(self):
        self.setup_letter()
        config_path = self.root / "config.json"
        atomic_json(config_path, self.config.public())
        args = ["--store", str(self.store.root), "--config", str(config_path),
                "transcribe", "--all", "--output", str(self.root / "exports")]
        fake = FakeTransport([response(self.doc)])
        with patch("correspondence.cli.Gemini", return_value=fake), patch("correspondence.cli.api_key", return_value="dummy"), \
             patch("correspondence.cli.export_all", side_effect=OSError("export destination failed")), \
             patch("sys.stdout", new=StringIO()), patch("sys.stderr", new=StringIO()):
            self.assertEqual(main(args), 1)
        self.assertEqual(len(fake.calls), 1)
        with patch("correspondence.cli.Gemini", side_effect=AssertionError("must reuse")), patch("sys.stdout", new=StringIO()):
            self.assertEqual(main(args), 0)
        self.assertEqual(self.store.latest("run_end")["new_attempts"], 0)
        self.assertEqual(self.store.latest("run_end")["reused_results"], 1)

    def test_inventory_export_match_and_show_no_provider(self):
        jpeg(self.inputs / "A-B-1899.jpg")
        prefix = ["--store", str(self.store.root)]
        with patch("correspondence.cli.Gemini", side_effect=AssertionError("network forbidden")), patch("sys.stdout", new=StringIO()):
            self.assertEqual(main(prefix + ["inventory", "--input", str(self.inputs), "--output", str(self.root / "exports")]), 0)
            self.assertEqual(main(prefix + ["show"]), 0)
            self.assertEqual(main(prefix + ["match"]), 0)
            self.assertEqual(main(prefix + ["export", "--output", str(self.root / "exports")]), 0)
        self.assertFalse(Path(self.config.quota_file).exists())
