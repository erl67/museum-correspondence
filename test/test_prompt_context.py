"""Name context is evidence to consider, independent of approved handwriting."""
from copy import deepcopy
from io import StringIO
import json
from unittest.mock import patch

from correspondence.cli import main
from correspondence.images import prepare_request
from correspondence.prompt import known_correspondents
from correspondence.review import apply_review, people
from correspondence.storage import atomic_json
from .helpers import Workspace, FakeTransport, response


class PromptContextTests(Workspace):
    def setUp(self):
        super().setUp()
        self.setup_letter()
        self.person = dict(kind="person", person_id="per_synthetic", name="Alice Example",
                           aliases=["A. Example", "Example"], review_status="approved",
                           source="Private staff note", standardize_display=True)
        apply_review(self.store, self.inventory, self.person)

    def test_only_approved_names_and_aliases_sent_without_resolving_ambiguity(self):
        registered = people(self.store)
        registered["per_other"] = dict(self.person, name="Andrew Example")
        registered["per_unreviewed"] = dict(self.person, name="Unreviewed", review_status="unreviewed")
        context = known_correspondents(registered)
        self.assertEqual(len(context), 2)
        self.assertEqual({c["name"] for c in context}, {"Alice Example", "Andrew Example"})
        for candidate in context:
            self.assertEqual(set(candidate), {"name", "aliases"})
            self.assertIn("A. Example", candidate["aliases"])
        self.assertNotIn("Private staff note", json.dumps(context))

    def test_name_changes_invalidate_request_but_context_is_frozen_and_ids_unchanged(self):
        registered = people(self.store)
        context = known_correspondents(registered)
        before = deepcopy(self.letter)
        first = prepare_request(self.inventory, self.letter, self.config, correspondents=context)
        context[0]["aliases"].append("A.E.")
        second = prepare_request(self.inventory, self.letter, self.config, correspondents=context)
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertNotIn("A.E.", first["provenance"]["known_correspondents"][0]["aliases"])
        self.assertEqual(first["image_data"], second["image_data"])
        self.assertEqual(first["provenance"]["images"], second["provenance"]["images"])
        self.assertIsNone(first["provenance"]["handwriting_profile"])
        self.assertEqual(self.letter, before)
        registered["per_synthetic"]["source"] = "Changed internal note"
        registered["per_synthetic"]["aliases"].reverse()
        reordered = prepare_request(self.inventory, self.letter, self.config,
                                    correspondents=known_correspondents(registered))
        self.assertEqual(first["fingerprint"], reordered["fingerprint"])

    def test_cli_dry_run_and_transcription_use_same_frozen_names(self):
        config = self.root / "config.json"
        atomic_json(config, self.config.public())
        prefix = ["--store", str(self.store.root), "--config", str(config)]
        journal = self.store.journal.read_bytes()
        prepared = []

        def capture(*args, **kwargs):
            result = prepare_request(*args, **kwargs)
            prepared.append(result)
            return result

        with patch("correspondence.cli.prepare_request", side_effect=capture), \
             patch("correspondence.cli.Gemini", side_effect=AssertionError("No service in dry-run")), \
             patch("sys.stdout", new=StringIO()):
            self.assertEqual(main(prefix + ["dry-run", "--input", str(self.inputs)]), 0)
        self.assertEqual(self.store.journal.read_bytes(), journal)
        fake = FakeTransport([response(self.doc)])
        with patch("correspondence.cli.Gemini", return_value=fake), \
             patch("correspondence.cli.api_key", return_value="synthetic-unused-key"), \
             patch("sys.stdout", new=StringIO()):
            self.assertEqual(main(prefix + ["transcribe", "--all", "--output", str(self.root / "exports")]), 0)
        result = self.store.results()[-1]
        self.assertEqual(result["fingerprint"], prepared[0]["fingerprint"])
        self.assertEqual(fake.calls, [prepared[0]["provenance"]["prompt"]])
        self.assertEqual(result["document"], self.doc)
        self.assertEqual(result["letter_id"], self.letter["letter_id"])
        self.assertIn("Alice Example", fake.calls[0])
        self.assertNotIn("Private staff note", fake.calls[0])
