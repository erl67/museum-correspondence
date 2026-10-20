from copy import deepcopy
from dataclasses import replace
from io import StringIO
from unittest.mock import patch
from correspondence.cli import main
from correspondence.discovery import discover
from correspondence.images import prepare_image, prepare_request
from correspondence.storage import digest
from .helpers import ROOT, Workspace, jpeg


class DiscoveryTests(Workspace):
    def test_actual_six_images_and_order(self):
        inventory = discover(ROOT / "test" / "inputs")
        self.assertEqual([len(l["image_ids"]) for l in inventory["letters"]], [2, 4])
        images = {i["image_id"]: i for i in inventory["images"]}
        for letter, labels in zip(inventory["letters"], ["AB", "ABCD"]):
            self.assertEqual([images[i]["filename"][-6] for i in letter["image_ids"]], list(labels))
        self.assertTrue(all(i["status"] == "ready" for i in inventory["images"]))
        expected = {
            "Shufeld,P-Todd-1899-04-18(A).jpg": "ceed9b03e240221a2eb618e17d5676c792e07af1f747e4adabcedd1cb4043a4d",
            "Shufeld,P-Todd-1899-04-18(B).jpg": "9ec5cb8bbb2cc9717129bb121b08f603583460024607401c1d13ef60c8949cae",
            "Shufeld,P-Todd-1899-08-07(A).jpg": "7c0ed9e1740153250986c9a84382ba7b2867c00a9893d5281136c3d571630492",
            "Shufeld,P-Todd-1899-08-07(B).jpg": "d05620bbbab228c335bafcd93a284d57109680bfcf144bd81fcee8531f7264b8",
            "Shufeld,P-Todd-1899-08-07(C).jpg": "58f3ea37a85ea8a99ab2410371f389c76f0cf38c97bfdc92ab104188969dc570",
            "Shufeld,P-Todd-1899-08-07(D).jpg": "03687d4b6e68f21af427956d3864768b35057fc8c20d62f18ce80e702295c637"}
        self.assertEqual({i["filename"]: i["sha256"] for i in inventory["images"]}, expected)

    def test_missing_intermediate_pages(self):
        self.setup_letter(("A-B-1899(A).jpg", "A-B-1899(C).jpg"), prepare=False)
        self.assertEqual(self.letter["grouping"], "needs_review")
        self.assertIn("missing initial or intermediate page", self.letter["review_reasons"])

    def test_duplicate_labels_across_extensions(self):
        self.setup_letter(("A-B-1899(A).jpg", "A-B-1899(A).JPEG"), prepare=False)
        self.assertTrue(any("duplicate" in r for r in self.letter["review_reasons"]))

    def test_identical_filename_different_folders_not_merged(self):
        self.setup_letter(("one/A-B-1899.jpg", "two/A-B-1899.jpg"), prepare=False)
        self.assertEqual(len(self.inventory["letters"]), 2)
        self.assertTrue(all(l["grouping"] == "needs_review" for l in self.inventory["letters"]))

    def test_mixed_order_is_ambiguous(self):
        self.setup_letter(("A-B-1899(A).jpg", "A-B-1899(2).jpg"), prepare=False)
        self.assertIn("mixed page label systems", self.letter["review_reasons"])

    def test_unknown_filename_visible(self):
        self.setup_letter(("misc.jpg",), prepare=False)
        self.assertEqual(self.letter["grouping"], "needs_review")

    def test_corrupt_unsupported_missing_remain_visible(self):
        jpeg(self.inputs / "A-B-1899.jpg")
        (self.inputs / "bad.JPG").write_bytes(b"not a jpeg")
        (self.inputs / "notes.txt").write_text("not a scan")
        inventory = discover(self.inputs)
        self.assertEqual({i["status"] for i in inventory["images"]}, {"ready", "unreadable", "unsupported"})
        (self.inputs / "A-B-1899.jpg").unlink()
        updated = discover(self.inputs, inventory)
        self.assertIn("missing", [i["status"] for i in updated["images"]])

    def test_add_and_replace_preserve_archival_ids(self):
        self.setup_letter(("A-B-1899(A).jpg",))
        jpeg(self.inputs / "A-B-1899(B).jpg")
        jpeg(self.inputs / "A-B-1899(A).jpg", "blue")
        updated = discover(self.inputs, self.inventory)
        self.assertEqual(updated["letters"][0]["letter_id"], self.letter["letter_id"])
        self.assertEqual(updated["images"][0]["image_id"], self.inventory["images"][0]["image_id"])
        self.assertNotEqual(updated["images"][0]["sha256"], self.inventory["images"][0]["sha256"])
        self.assertEqual(updated["letters"][0]["grouping"], "needs_review")
        repeated = discover(self.inputs, updated)
        self.assertEqual(repeated["letters"][0]["grouping"], "needs_review")

    def test_override_order_and_explicit_regroup_history(self):
        self.setup_letter()
        paths = [i["path"] for i in self.inventory["images"]]
        override = {"version": 1, "groups": [{"key": "reading", "letter_id": self.letter["letter_id"],
                    "paths": paths[::-1], "source": "staff checked order"}]}
        updated = discover(self.inputs, self.inventory, override)
        self.assertEqual(updated["letters"][0]["letter_id"], self.letter["letter_id"])
        self.assertEqual(updated["letters"][0]["image_ids"], self.letter["image_ids"][::-1])
        self.assertEqual(updated["letters"][0]["grouping"], "reviewed")
        del override["groups"][0]["letter_id"]
        regrouped = discover(self.inputs, self.inventory, override)
        self.assertTrue(any(not l["active"] for l in regrouped["letters"]))

    def test_override_double_claim_rejected(self):
        self.setup_letter()
        group = {"key": "one", "paths": [self.inventory["images"][0]["path"]], "source": "check"}
        with self.assertRaises(ValueError):
            discover(self.inputs, self.inventory, {"version": 1, "groups": [group, dict(group, key="two")]})

    def test_source_bytes_preserved_and_changes_detected(self):
        self.setup_letter()
        path = self.inputs / self.inventory["images"][0]["path"]
        raw = path.read_bytes()
        self.assertEqual(prepare_image(raw)[0], raw)
        prepared, operations = prepare_image(raw, 16)
        self.assertNotEqual(digest(raw), digest(prepared))
        self.assertEqual(path.read_bytes(), raw)
        jpeg(path, "red")
        with self.assertRaisesRegex(ValueError, "changed"):
            prepare_request(self.inventory, self.letter, self.config)

    def test_exif_orientation_recorded(self):
        from PIL import Image
        from io import BytesIO
        image = Image.new("RGB", (10, 20))
        exif = image.getexif()
        exif[274] = 6
        stream = BytesIO()
        image.save(stream, "JPEG", exif=exif)
        data, operations = prepare_image(stream.getvalue())
        self.assertIn("EXIF orientation 6 applied", operations)
        self.assertEqual(Image.open(BytesIO(data)).size, (20, 10))

    def test_oversize_never_omits_pages(self):
        self.setup_letter()
        with self.assertRaisesRegex(ValueError, "No pages omitted"):
            prepare_request(self.inventory, self.letter, replace(self.config, max_request_bytes=1000))
        with self.assertRaisesRegex(ValueError, "no pages were omitted"):
            prepare_request(self.inventory, self.letter, replace(self.config, max_pages=1))

    def test_dry_run_read_only_without_credentials(self):
        jpeg(self.inputs / "A-B-1899.jpg")
        destination = self.root / "never-created"
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch("correspondence.cli.Gemini", side_effect=AssertionError("network forbidden")), patch("sys.stdout", new=StringIO()):
            result = main(["--store", str(destination), "dry-run", "--input", str(self.inputs)])
        self.assertEqual(result, 0)
        self.assertFalse(destination.exists())
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_fingerprint_inputs_and_operational_exclusions(self):
        self.setup_letter()
        base = self.request["fingerprint"]
        self.assertEqual(prepare_request(self.inventory, self.letter, replace(self.config, rpm=1))["fingerprint"], base)
        for config in (replace(self.config, model="gemini-explicit-other"), replace(self.config, temperature=.5),
                       replace(self.config, thinking_level="low"), replace(self.config, max_edge=16)):
            self.assertNotEqual(prepare_request(self.inventory, self.letter, config)["fingerprint"], base)
        changed = deepcopy(self.letter)
        changed["hints"]["sender"] = "corrected hint"
        self.assertNotEqual(prepare_request(self.inventory, changed, self.config)["fingerprint"], base)
        changed = deepcopy(self.letter)
        changed["image_ids"].reverse()
        self.assertNotEqual(prepare_request(self.inventory, changed, self.config)["fingerprint"], base)
        with patch("correspondence.prompt.POLICY", "Different complete prompt"):
            self.assertNotEqual(prepare_request(self.inventory, self.letter, self.config)["fingerprint"], base)
