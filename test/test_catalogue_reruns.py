"""Exercise real CLI reruns with synthetic scans and a fake provider only."""
from copy import deepcopy
import csv
from io import StringIO
from unittest.mock import patch

from correspondence.cli import main
from correspondence.execution import Quota
from correspondence.prompt import known_correspondents
from correspondence.review import current_records, people
from correspondence.schema import empty_document
from correspondence.storage import atomic_json, read_json
from .helpers import Clock, FakeTransport, Workspace, jpeg, response


class CatalogueRerunTests(Workspace):
    def setUp(self):
        super().setUp()
        provider = patch("correspondence.cli.Gemini", side_effect=AssertionError("live provider forbidden"))
        provider.start()
        self.addCleanup(provider.stop)
        self.output = self.root / "exports"
        config = self.root / "config.json"
        atomic_json(config, self.config.public())
        self.prefix = ["--store", str(self.store.root), "--config", str(config)]
        self.clock = Clock()
        self.paths = [f"Percy/{sender}-Todd-18990807_{n:02}.jpg"
                      for n, sender in enumerate(["Shufeldt,P", "Shufeldtt,P", "Shufeldt,P", "Shufeldt,P"], 1)]
        for name in self.paths:
            jpeg(self.inputs / name)
        self.inventory_run()
        original = self.store.latest("inventory")
        first = next(l for l in original["letters"] if len(l["image_ids"]) == 3)
        override = self.root / "grouping.json"
        atomic_json(override, dict(version=1, groups=[dict(key="four-pages", letter_id=first["letter_id"],
            paths=self.paths, source="Synthetic grouping decision")]))
        self.inventory_run("--overrides", str(override))
        for name, aliases in [
            ("Percy Shufeldt", ["Shufeldt,P", "Shufeldtt,P"]),
            ("W.E. Clyde Todd", ["Todd", "W. E. Clyde Todd", "W. Clyde Todd"]),
            ("Robert W. Shufeldt", ["Shufeldt,RW", "Robert Wilson Shufeldt", "R. W. Shufeldt"]),
            ("George Miksch Sutton", ["Sutton", "Geo. M. Sutton"]),
        ]:
            self.review(kind="person", name=name, aliases=aliases, standardize_display=True,
                        review_status="approved")
        self.letter = next(l for l in self.store.latest("inventory")["letters"] if l["active"])
        self.doc = self.document(self.letter, "Percy Shufeldt", "W. E. Clyde Todd")

    def cli(self, *args):
        with patch("sys.stdout", new=StringIO()), patch("sys.stderr", new=StringIO()) as errors:
            self.assertEqual(main(self.prefix + list(args)), 0, errors.getvalue())

    def inventory_run(self, *extra):
        self.cli("inventory", "--input", str(self.inputs), "--output", str(self.output), *extra)

    def review(self, **data):
        path = self.root / "review.json"
        atomic_json(path, dict(source="Synthetic staff catalogue decision", **data))
        self.cli("review", "--file", str(path))

    def document(self, letter, sender, recipient):
        doc = empty_document(letter["image_ids"])
        for page in doc["pages"]:
            page["text"] = f"SYNTHETIC SOFTWARE FIXTURE. {sender} to {recipient}. Aug 7 - '99"
        for name, value in (("sender", sender), ("recipient", recipient)):
            doc["metadata"][name] = dict(value=value, normalized=value, certainty="inferred",
                evidence=[dict(image_id=letter["image_ids"][0], quote=value)])
        doc["metadata"]["date"] = dict(value="Aug 7 - '99", normalized="1899-08-07", precision="day",
            certainty="inferred", evidence=[dict(image_id=letter["image_ids"][0], quote="Aug 7 - '99")])
        return doc

    def fake_transcribe(self, doc, *selection):
        fake = FakeTransport([response(doc)])
        with patch("correspondence.cli.Gemini", return_value=fake), \
             patch("correspondence.cli.api_key", return_value="synthetic-unused-key"), \
             patch("correspondence.execution.Quota", return_value=Quota(self.config, self.clock.time, self.clock.sleep)):
            self.cli("transcribe", *selection, "--output", str(self.output), "--publish-text")
        self.assertEqual(len(fake.calls), 1)
        saved = self.store.results()[-1]["provenance"]
        self.assertEqual(saved["known_correspondents"], known_correspondents(people(self.store)))
        self.assertIn("George Miksch Sutton", fake.calls[0])
        self.assertIsNone(saved["handwriting_profile"])

    def active_export(self):
        return [l for l in read_json(self.output / "viewer.json")["letters"] if l["active"]]

    def test_inventory_pending_export_preserve_names_grouping_and_confirmed_date(self):
        scans = {p: (self.inputs / p).read_bytes() for p in self.paths}
        self.fake_transcribe(self.doc, "--pending")
        result = self.store.results()[-1]
        self.review(kind="letter", letter_id=self.letter["letter_id"], base_revision=result["revision_id"],
                    catalogue_date=dict(value="1899-08-07", precision="day"))
        journal = self.store.journal.read_bytes()
        quota = read_json(self.config.quota_file)
        for command in ("inventory", "pending", "cache", "export"):
            with self.subTest(command=command):
                if command == "inventory":
                    self.inventory_run()  # Saved grouping overrides are reused.
                elif command == "pending":
                    self.cli("transcribe", "--pending", "--output", str(self.output))
                    self.assertEqual(self.store.latest("run_end")["new_attempts"], 0)
                elif command == "cache":
                    self.cli("transcribe", "--all", "--output", str(self.output))
                    self.assertEqual(self.store.latest("run_end")["new_attempts"], 0)
                    self.assertEqual(self.store.latest("run_end")["reused_results"], 1)
                else:
                    self.cli("export", "--output", str(self.output))
                letters = self.active_export()
                self.assertEqual(len(letters), 1)
                letter = letters[0]
                self.assertEqual(letter["letter_id"], self.letter["letter_id"])
                self.assertEqual([s["image_id"] for s in letter["scans"]], self.letter["image_ids"])
                self.assertEqual(letter["pages"], self.doc["pages"])
                self.assertEqual(letter["catalogue_names"]["sender"]["name"], "Percy Shufeldt")
                self.assertEqual(letter["catalogue_names"]["recipient"]["name"], "W.E. Clyde Todd")
                self.assertEqual(letter["metadata"]["recipient"]["certainty"], "inferred")
                self.assertEqual(letter["catalogue_date"]["value"], "1899-08-07")
                self.assertFalse(any(r.startswith("filename/document conflict: recipient:") for r in letter["review_reasons"]))
                self.assertEqual((self.inputs / "Correspondence_viewer.json").read_bytes(), (self.output / "viewer.json").read_bytes())
                text = (self.inputs / "Correspondence_transcriptions.txt").read_text(encoding="utf-8")
                self.assertIn("Recipient: W.E. Clyde Todd (inferred)", text)
                self.assertNotIn("STATUS: retired", text)
                with (self.output / "catalogue.csv").open(encoding="utf-8-sig", newline="") as stream:
                    row = next(r for r in csv.DictReader(stream) if r["active"] == "True")
                self.assertEqual(row["recipient_display"], "W.E. Clyde Todd")
                self.assertEqual(row["recipient"], "W. E. Clyde Todd")
        self.assertEqual(sum(not l["active"] for l in self.store.latest("inventory")["letters"]), 1)
        self.assertTrue(self.store.journal.read_bytes().startswith(journal))
        self.assertEqual(self.store.results(), [result])
        self.assertEqual(read_json(self.config.quota_file), quota)
        self.assertEqual(scans, {p: (self.inputs / p).read_bytes() for p in self.paths})

    def test_fresh_results_and_new_letters_reuse_authorities_without_reusing_date_approval(self):
        self.fake_transcribe(self.doc, "--pending")
        original = deepcopy(self.store.results()[0])
        self.review(kind="letter", letter_id=self.letter["letter_id"], base_revision=original["revision_id"],
                    catalogue_date=dict(value="1899-08-07", precision="day"))
        authorities = people(self.store)
        fresh = self.document(self.letter, "Percy Shufeldt", "W. Clyde Todd")
        self.fake_transcribe(fresh, "--letter", self.letter["letter_id"], "--fresh")
        exported = self.active_export()[0]
        self.assertEqual(exported["catalogue_names"]["recipient"]["name"], "W.E. Clyde Todd")
        self.assertIsNone(exported["catalogue_date"])
        self.assertEqual(self.store.results()[0], original)
        self.assertEqual(self.store.results()[-1]["document"], fresh)
        jpeg(self.inputs / "RW/Shufeldt,RW-Sutton-19231209_01.jpg")
        self.inventory_run()
        new = next(l for l in self.store.latest("inventory")["letters"]
                   if l["active"] and l["letter_id"] != self.letter["letter_id"])
        self.fake_transcribe(self.document(new, "Robert Wilson Shufeldt", "Geo. M. Sutton"), "--pending")
        exported = next(l for l in self.active_export() if l["letter_id"] == new["letter_id"])
        self.assertEqual(exported["catalogue_names"]["sender"]["name"], "Robert W. Shufeldt")
        self.assertEqual(exported["catalogue_names"]["recipient"]["name"], "George Miksch Sutton")
        self.assertEqual(people(self.store), authorities)
        self.assertEqual(self.store.latest("run_end")["new_attempts"], 1)

    def test_genuine_and_ambiguous_name_conflicts_remain_reviewable(self):
        self.fake_transcribe(self.document(self.letter, "Robert Wilson Shufeldt", "W. E. Clyde Todd"), "--pending")
        def reasons():
            return next(r for r in current_records(self.store, self.store.latest("inventory")) if r["active"])["review_reasons"]
        self.assertTrue(any(r.startswith("filename/document conflict: sender:") for r in reasons()))
        self.assertFalse(any(r.startswith("filename/document conflict: recipient:") for r in reasons()))
        self.review(kind="person", name="Different Todd", aliases=["Todd"], standardize_display=True,
                    review_status="approved")
        self.assertTrue(any(r.startswith("filename/document conflict: recipient:") for r in reasons()))
        self.assertTrue(any(r.startswith("filename/document conflict: recipient:")
                            for r in self.store.results()[0]["review_reasons"]))
