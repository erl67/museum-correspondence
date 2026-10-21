from copy import deepcopy
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from correspondence.cli import main
from correspondence.discovery import discover
from correspondence.execution import Quota, transcribe
from correspondence.exports import export_all
from correspondence.plaintext import reading, text_paths
from correspondence.publication import publish_text, source_destination
from correspondence.relocation import reconcile_paths
from correspondence.review import current_records
from correspondence.storage import atomic_json
from .helpers import Clock, FakeTransport, Workspace, jpeg, response


class PublicationTests(Workspace):
    def setUp(self):
        super().setUp()
        self.setup_letter(("Correspondent/A-B-1899-05-02(1).jpg", "Correspondent/A-B-1899-05-02(2).jpg"))
        self.doc["pages"][0]["text"] = "Dear B,\nThis is the first page. Café."
        self.doc["pages"][1]["text"] = "Second page.\nYours, A."
        clock = Clock()
        transcribe(self.store, self.letter, self.request, self.config,
                   lambda: FakeTransport([response(self.doc)]),
                   quota=Quota(self.config, clock.time, clock.sleep))
        self.output = self.root / "exports"
        export_all(self.store, self.inventory, self.output)

    def test_reading_has_ordered_text_before_metadata_without_json(self):
        text = (self.output / "readable/Correspondent/A-B-18990502.txt").read_text(encoding="utf-8")
        self.assertLess(text.index("Dear B,"), text.index("Second page."))
        self.assertLess(text.index("Second page."), text.index("CATALOGUE DETAILS"))
        self.assertIn("Café", text)
        self.assertNotIn('"metadata":', text)
        self.assertIn("Dear B,", (self.output / "combined.txt").read_text(encoding="utf-8"))

    def test_publish_then_discover_excludes_only_owned_reports(self):
        before = {p: p.read_bytes() for p in self.inputs.rglob("*.jpg")}
        with patch("correspondence.provider.Gemini.send", side_effect=AssertionError("network forbidden")):
            publish_text(self.store, self.inventory, self.output)
            publish_text(self.store, self.inventory, self.output)
        for relative in ("Correspondent/A-B-18990502.txt", "Correspondent/Correspondent_transcriptions.txt",
                         "Correspondence_transcriptions.txt", "Correspondence_viewer.json"):
            self.assertTrue((self.inputs / relative).is_file())
        (self.inputs / "staff-notes.txt").write_text("Independent staff notes")
        updated = discover(self.inputs, self.inventory, generated_paths=self.store.latest("text_publication")["files"])
        self.assertEqual(len(updated["images"]), 3)
        self.assertEqual(next(i for i in updated["images"] if i["filename"] == "staff-notes.txt")["status"], "unsupported")
        self.assertEqual(before, {p: p.read_bytes() for p in self.inputs.rglob("*.jpg")})

    def test_unowned_existing_text_is_not_overwritten(self):
        destination = self.inputs / "Correspondent/A-B-18990502.txt"
        destination.write_text("Staff reading", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unowned or edited"):
            publish_text(self.store, self.inventory, self.output)
        self.assertEqual(destination.read_text(), "Staff reading")
        self.assertFalse((self.inputs / "Correspondence_transcriptions.txt").exists())

    def test_obsolete_reports_are_archived_and_removed_with_retry(self):
        from correspondence.storage import digest
        publish_text(self.store, self.inventory, self.output)
        old = self.inputs / "Correspondent/A-B-18990502.txt"
        original = old.read_bytes()
        updated = deepcopy(self.inventory)
        updated['letters'][0]['override'] = {'title': 'New report title'}
        export_all(self.store, updated, self.output)
        unlink = Path.unlink
        def interrupted(path, *args, **kwargs):
            if path == old:
                raise OSError('interrupted cleanup')
            return unlink(path, *args, **kwargs)
        with patch('pathlib.Path.unlink', interrupted):
            with self.assertRaises(OSError):
                publish_text(self.store, updated, self.output)
        self.assertTrue((self.inputs / 'Correspondent/New report title.txt').exists())
        self.assertEqual(self.store.latest('text_publication')['status'], 'pending')
        publish_text(self.store, updated, self.output)
        self.assertFalse(old.exists())
        self.assertTrue((self.inputs / 'Correspondent/New report title.txt').exists())
        self.assertEqual((self.store.root / 'blobs' / (digest(original) + '.txt')).read_bytes(), original)
        self.assertNotIn('Correspondent/A-B-18990502.txt', self.store.latest('text_publication')['files'])

    def test_edited_obsolete_report_blocks_publication(self):
        publish_text(self.store, self.inventory, self.output)
        old = self.inputs / 'Correspondent/A-B-18990502.txt'
        old.write_text('Staff edits', encoding='utf-8')
        updated = deepcopy(self.inventory)
        updated['letters'][0]['override'] = {'title': 'New report title'}
        with self.assertRaisesRegex(ValueError, 'edited'):
            publish_text(self.store, updated, self.output)
        self.assertFalse((self.inputs / 'Correspondent/New report title.txt').exists())
        self.assertEqual(old.read_text(encoding='utf-8'), 'Staff edits')

    def test_edited_published_text_is_not_overwritten(self):
        publish_text(self.store, self.inventory, self.output)
        destination = self.inputs / "Correspondent/A-B-18990502.txt"
        destination.write_text("Staff correction", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unowned or edited"):
            publish_text(self.store, self.inventory, self.output)
        self.assertEqual(destination.read_text(), "Staff correction")

    def test_partial_publication_can_resume(self):
        from correspondence.storage import atomic_bytes
        calls = 0
        def interrupted(path, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("interrupted publication")
            atomic_bytes(path, data)
        with patch("correspondence.publication.atomic_bytes", side_effect=interrupted):
            with self.assertRaises(OSError):
                publish_text(self.store, self.inventory, self.output)
        self.assertEqual(self.store.latest("text_publication")["status"], "pending")
        publish_text(self.store, self.inventory, self.output)
        self.assertEqual(self.store.latest("text_publication")["status"], "complete")

    def test_path_escape_and_scan_collision_rejected(self):
        for relative in ("../outside.txt", "/outside.txt", "C:/outside.txt", "folder\\outside.txt"):
            with self.assertRaises(ValueError):
                source_destination(self.inputs, relative)
        inv = deepcopy(self.inventory)
        inv["images"].append(dict(path="Correspondent/A-B-18990502.txt", image_id="extra"))
        with self.assertRaisesRegex(ValueError, "inventoried source"):
            publish_text(self.store, inv, self.output)

    def test_colliding_names_keep_both_records(self):
        records = current_records(self.store, self.inventory)
        other = deepcopy(records[0])
        other["letter_id"] = "ltr_other"
        records.append(other)
        paths = text_paths(records, {i["image_id"]: i for i in self.inventory["images"]})
        self.assertEqual(len(set(paths.values())), 2)
        self.assertTrue(all("A-B-18990502" in p.name for p in paths.values()))

    def test_unprocessed_and_stale_text_are_labelled(self):
        record = current_records(self.store, self.inventory)[0]
        images = {i["image_id"]: i for i in self.inventory["images"]}
        record["execution"] = "stale"
        self.assertIn("EARLIER READING", reading(record, images))
        record.update(execution="blocked", document=None, result=None)
        self.assertIn("No complete transcription", reading(record, images))

    def test_pending_skips_completed_beyond_cache_age_and_refreshes_drive(self):
        result = deepcopy(self.store.results()[-1])
        result["saved_at"] = "2000-01-01T00:00:00+00:00"
        result["revision_id"] = "rev_older"
        self.store.append("result", result)
        args = ["--store", str(self.store.root), "transcribe", "--pending", "--publish-text", "--output", str(self.output)]
        with patch("correspondence.cli.Gemini", side_effect=AssertionError("no service call")), patch("sys.stdout", new=StringIO()):
            self.assertEqual(main(args), 0)
        self.assertEqual(self.store.latest("run_end")["new_attempts"], 0)
        self.assertIn("Dear B,", (self.inputs / "Correspondence_transcriptions.txt").read_text(encoding="utf-8"))
        # Ordinary subsequent exports retain the explicit publication choice.
        with patch("sys.stdout", new=StringIO()):
            self.assertEqual(main(["--store", str(self.store.root), "export", "--output", str(self.output)]), 0)


class RelocationTests(Workspace):
    def setUp(self):
        super().setUp()
        self.setup_letter(("Old-B-1899(1).jpg", "Old-B-1899(2).jpg"))
        self.mapping = dict(version=1, source="Explicit synthetic filename correction",
                            paths={i["path"]: i["path"].replace("Old-", "New-") for i in self.inventory["images"]})
        for old, new in self.mapping["paths"].items():
            (self.inputs / old).rename(self.inputs / new)

    def test_reconcile_preserves_identity_and_result_without_rewriting_history(self):
        clock = Clock()
        transcribe(self.store, self.letter, self.request, self.config,
                   lambda: FakeTransport([response(self.doc)]), quota=Quota(self.config, clock.time, clock.sleep))
        before = self.store.journal.read_bytes()
        updated = reconcile_paths(self.inventory, self.mapping)
        self.store.append("inventory", updated)
        refreshed = discover(self.inputs, updated)
        self.assertTrue(self.store.journal.read_bytes().startswith(before))
        self.assertEqual(refreshed["letters"][0]["letter_id"], self.letter["letter_id"])
        self.assertEqual(refreshed["letters"][0]["image_ids"], self.letter["image_ids"])
        self.assertEqual(current_records(self.store, refreshed)[0]["execution"], "complete")
        self.assertEqual(self.store.results()[0]["provenance"]["images"][0]["path"], "Old-B-1899(1).jpg")

    def test_changed_bytes_rejected(self):
        jpeg(self.inputs / "New-B-1899(1).jpg", "blue")
        with self.assertRaisesRegex(ValueError, "bytes differ"):
            reconcile_paths(self.inventory, self.mapping)

    def test_corrected_filename_clears_only_resolved_current_conflicts(self):
        for old, new in list(self.mapping["paths"].items()):
            corrected = new.replace("1899", "1900")
            (self.inputs / new).rename(self.inputs / corrected)
            self.mapping["paths"][old] = corrected
        self.doc["pages"][0]["text"] = "SYNTHETIC FIXTURE. May 2, 1900. Dear Other."
        evidence = [dict(image_id=self.letter["image_ids"][0], quote="May 2, 1900")]
        self.doc["metadata"]["date"].update(value="May 2, 1900", normalized="1900",
                                             precision="year", certainty="explicit", evidence=evidence)
        self.doc["metadata"]["recipient"].update(value="Other", normalized="Other",
                                                  certainty="explicit", evidence=evidence)
        clock = Clock()
        transcribe(self.store, self.letter, self.request, self.config,
                   lambda: FakeTransport([response(self.doc)]), quota=Quota(self.config, clock.time, clock.sleep))
        original = deepcopy(self.store.results()[0])
        self.assertTrue(any(r.startswith("filename/document conflict: date:") for r in original["review_reasons"]))
        updated = reconcile_paths(self.inventory, self.mapping)
        self.store.append("inventory", updated)
        output = self.root / "exports"
        export_all(self.store, updated, output)
        record = current_records(self.store, updated)[0]
        self.assertFalse(any(r.startswith("filename/document conflict: date:") for r in record["review_reasons"]))
        self.assertTrue(any(r.startswith("filename/document conflict: recipient:") for r in record["review_reasons"]))
        self.assertNotIn("filename/document conflict: date:", (output / "combined.txt").read_text(encoding="utf-8"))
        self.assertEqual(record["execution"], "complete")
        self.assertEqual(record["document"], original["document"])
        self.assertEqual(self.store.results()[0], original)

    def test_existing_old_path_duplicate_target_and_escape_rejected(self):
        invalid = deepcopy(self.mapping)
        invalid["paths"]["Old-B-1899(2).jpg"] = "New-B-1899(1).jpg"
        with self.assertRaises(ValueError):
            reconcile_paths(self.inventory, invalid)
        invalid["paths"]["Old-B-1899(2).jpg"] = "../outside.jpg"
        with self.assertRaises(ValueError):
            reconcile_paths(self.inventory, invalid)
        jpeg(self.inputs / "Old-B-1899(1).jpg")
        with self.assertRaisesRegex(ValueError, "still exists"):
            reconcile_paths(self.inventory, self.mapping)
