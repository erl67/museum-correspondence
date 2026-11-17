from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
from unittest.mock import patch
import httpx
from correspondence.execution import Quota, QuotaReached, error_policy, transcribe
from correspondence.cli import main
from correspondence.config import Config, load_config
from correspondence.images import prepare_request
from correspondence.exports import export_all
from correspondence.provider import Gemini, api_key
from correspondence.storage import atomic_json, encoded, lock, read_json
from .helpers import Workspace, Clock, FakeTransport, ServiceError, response


class ExecutionTests(Workspace):
    def setUp(self):
        super().setUp()
        self.setup_letter()
        self.clock = Clock()
        self.quota = Quota(self.config, self.clock.time, self.clock.sleep)

    def execute(self, answers, **kwargs):
        fake = FakeTransport(answers)
        result, reused = transcribe(self.store, self.letter, self.request, self.config, lambda: fake,
                                    quota=self.quota, sleep=self.clock.sleep, **kwargs)
        return result, reused, fake

    def test_success_raw_response_provenance_and_unknown_prices(self):
        result, reused, fake = self.execute([response(self.doc)])
        self.assertEqual(result["execution"], "complete")
        self.assertFalse(reused)
        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(fake.closed)
        end = self.store.latest("attempt_end")
        self.assertEqual(read_json(self.store.root / end["response"]), response(self.doc))
        self.assertIsNone(end["cost"])
        self.assertEqual(result["provenance"]["model"], "gemini-3.5-flash-lite")
        self.assertEqual(result["returned_model"], "synthetic-test-model")
        for image in self.request["provenance"]["images"]:
            self.assertTrue((self.store.root / "blobs" / (image["submitted_sha256"] + ".jpg")).is_file())

    def test_service_retries_all_counted_and_paced(self):
        result, _, fake = self.execute([ServiceError(503), response(self.doc)])
        self.assertEqual(result["execution"], "complete")
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(read_json(self.config.quota_file)["models"]["gemini/" + self.config.model]["attempts"], 2)
        ends = [e["data"] for e in self.store.events() if e["kind"] == "attempt_end"]
        self.assertIsNone(ends[0]["usage"]["total"])
        self.assertGreater(sum(self.clock.waits), 29)

    def test_cli_explains_saved_service_failure_and_stopped_batch(self):
        message = '503 UNAVAILABLE: This model is currently experiencing high demand.'
        fake = FakeTransport([ServiceError(503, message) for _ in range(3)])

        def execute(*args, **kwargs):
            return transcribe(*args, **kwargs, quota=self.quota, sleep=self.clock.sleep)

        with patch('correspondence.cli.load_config', return_value=self.config), \
                patch('correspondence.cli.api_key', return_value='synthetic'), \
                patch('correspondence.cli.Gemini', return_value=fake), \
                patch('correspondence.cli.transcribe', side_effect=execute), \
                patch('sys.stdout', new_callable=StringIO) as output:
            code = main(['--store', str(self.store.root), 'transcribe', '--pending',
                         '--output', str(self.root / 'exports')])
        self.assertEqual(code, 1)
        self.assertIn('ERROR: ' + message, output.getvalue())
        self.assertIn('Batch stopped; remaining letters were not attempted.', output.getvalue())
        self.assertEqual(len(fake.calls), 3)
        self.assertEqual(self.store.latest('result')['errors'], [message])
        self.assertTrue(self.store.latest('result')['stop_batch'])
        self.assertEqual(self.store.latest('run_end')['new_attempts'], 3)
        self.assertIsNone(self.store.latest('run_end')['usage']['total'])

    def test_format_correction_bounded_and_preserves_all_responses(self):
        bad = response(self.doc)
        bad["candidates"][0]["content"]["parts"][0]["text"] = "substantive malformed reading"
        result, _, fake = self.execute([bad, bad, response(self.doc)])
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(result["execution"], "failed")
        self.assertEqual(result["text"], "substantive malformed reading")
        self.assertIn("FORMAT CORRECTION", fake.calls[1])
        self.assertEqual(len([e for e in self.store.events() if e["kind"] == "attempt_end"]), 2)

    def test_honest_uncertainty_no_extra_attempt(self):
        self.doc["pages"][0]["text"] += " [uncertain: 0012]"
        result, _, fake = self.execute([response(self.doc)])
        self.assertEqual(result["execution"], "complete")
        self.assertTrue(result["review_reasons"])
        self.assertEqual(len(fake.calls), 1)

    def test_truncation_is_not_retried_or_reused(self):
        result, _, fake = self.execute([response(self.doc, "MAX_TOKENS")])
        self.assertEqual(result["execution"], "failed")
        self.assertEqual(len(fake.calls), 1)
        self.assertIsNone(self.store.reusable(self.letter["letter_id"], self.request["fingerprint"]))
        self.assertTrue(result["text"])

    def test_latest_empty_failure_does_not_erase_partial(self):
        bad = response(self.doc)
        bad["candidates"][0]["content"]["parts"][0]["text"] = "earlier substantial text"
        result, _, _ = self.execute([bad, {}])
        self.assertEqual(result["text"], "earlier substantial text")

    def test_cache_reuse_without_client_or_quota(self):
        first, _, _ = self.execute([response(self.doc)])
        before = Path(self.config.quota_file).read_bytes()
        result, reused = transcribe(self.store, self.letter, self.request, self.config,
                                   lambda: self.fail("Cache must not look up credentials"))
        self.assertTrue(reused)
        self.assertEqual(result, first)
        self.assertEqual(Path(self.config.quota_file).read_bytes(), before)

    def test_cache_48_hours_and_future_timestamps(self):
        result, _, _ = self.execute([response(self.doc)])
        saved = datetime.fromisoformat(result["saved_at"])
        self.assertIsNotNone(self.store.reusable(self.letter["letter_id"], self.request["fingerprint"], saved + timedelta(hours=48)))
        self.assertIsNone(self.store.reusable(self.letter["letter_id"], self.request["fingerprint"], saved + timedelta(hours=49)))
        self.assertIsNone(self.store.reusable(self.letter["letter_id"], self.request["fingerprint"], saved - timedelta(seconds=1)))

    def test_fresh_retains_earlier_revision(self):
        first, _, _ = self.execute([response(self.doc)])
        second, reused, _ = self.execute([response(self.doc)], fresh=True)
        self.assertFalse(reused)
        self.assertNotEqual(first["revision_id"], second["revision_id"])
        self.assertEqual(len(self.store.results()), 2)

    def test_reusing_older_matching_revision_selects_it_for_exports(self):
        from correspondence.images import prepare_request
        from correspondence.review import current_records
        first, _, _ = self.execute([response(self.doc)])
        changed = replace(self.config, temperature=0.5)
        alternate_request = prepare_request(self.inventory, self.letter, changed)
        alternate_document = deepcopy(self.doc)
        alternate_document["pages"][0]["text"] = "Synthetic alternate revision"
        transcribe(self.store, self.letter, alternate_request, changed,
                   lambda: FakeTransport([response(alternate_document)]), quota=self.quota)
        selected, reused, fake = self.execute([])
        self.assertTrue(reused)
        self.assertEqual(fake.calls, [])
        self.assertEqual(selected["revision_id"], first["revision_id"])
        self.assertEqual(current_records(self.store, self.inventory)[0]["result"]["revision_id"], first["revision_id"])
        self.assertEqual(len(self.store.results()), 2)
        self.assertEqual(self.store.latest("selection")["revision_id"], first["revision_id"])
        self.assertEqual(selected["saved_at"], first["saved_at"])

    def test_checkpoint_survives_report_failure(self):
        self.execute([response(self.doc)])
        with patch("correspondence.exports.atomic_bytes", side_effect=OSError("synthetic disk error")):
            with self.assertRaises(OSError):
                export_all(self.store, self.inventory, self.root / "exports")
        result, reused, fake = self.execute([])
        self.assertTrue(reused)
        self.assertEqual(fake.calls, [])
        export_all(self.store, self.inventory, self.root / "exports")
        self.assertTrue((self.root / "exports" / "catalogue.csv").is_file())

    def test_quota_survives_restarts_cap_and_day_reset(self):
        limited = replace(self.config, daily_limit=1)
        Quota(limited, self.clock.time, self.clock.sleep).update()
        with self.assertRaises(QuotaReached):
            Quota(limited, self.clock.time, self.clock.sleep).update()
        self.clock.value += 86400
        self.assertEqual(Quota(limited, self.clock.time, self.clock.sleep).update(), 1)

    def test_corrupt_or_old_quota_fails_closed(self):
        for state in ({"version": 1, "models": {}}, {"schema": "correspondence-quota-1", "models": {"x": {}}}):
            atomic_json(self.config.quota_file, state)
            with self.assertRaises(ValueError):
                self.quota.update()
            self.assertEqual(read_json(self.config.quota_file), state)

    def test_flash_38_cap_persists_across_retries_and_keeps_lite_counter(self):
        self.quota.update()
        lite_before = deepcopy(read_json(self.config.quota_file)['models']['gemini/' + self.config.model])
        config = replace(self.config, model='gemini-3.8-flash', attempts=1, daily_limit=20)
        request = prepare_request(self.inventory, self.letter, config)
        for _ in range(19):
            Quota(config, self.clock.time, self.clock.sleep).update()
        fake = FakeTransport([ServiceError(503)])
        result, _ = transcribe(self.store, self.letter, request, config, lambda: fake,
                              quota=Quota(config, self.clock.time, self.clock.sleep), sleep=self.clock.sleep)
        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(result['stop_batch'])
        self.assertEqual(result['execution'], 'failed')
        blocked = FakeTransport([])
        result, _ = transcribe(self.store, self.letter, request, config, lambda: blocked,
                              quota=Quota(config, self.clock.time, self.clock.sleep), sleep=self.clock.sleep)
        self.assertEqual(result['execution'], 'paused')
        self.assertEqual(blocked.calls, [])
        counters = read_json(self.config.quota_file)['models']
        self.assertEqual(counters['gemini/gemini-3.8-flash']['attempts'], 20)
        self.assertEqual(counters['gemini/' + self.config.model], lite_before)

    def test_flash_38_config_cli_selects_model_without_repeating_complete_letters(self):
        example = Path(__file__).resolve().parents[1] / 'docs/config-gemini-3.8-flash.example.json'
        config = replace(load_config(example), quota_file=self.config.quota_file)
        self.assertEqual((config.model, config.daily_limit, config.attempts), ('gemini-3.8-flash', 20, 1))
        path = self.root / 'flash.json'
        atomic_json(path, config.public())
        fake = FakeTransport([response(self.doc)])

        def execute(*args, **kwargs):
            return transcribe(*args, **kwargs, quota=Quota(config, self.clock.time, self.clock.sleep), sleep=self.clock.sleep)

        argv = ['--store', str(self.store.root), '--config', str(path), 'transcribe',
                '--pending', '--output', str(self.root / 'exports')]
        with patch('correspondence.cli.api_key', return_value='synthetic'), \
                patch('correspondence.cli.Gemini', return_value=fake), \
                patch('correspondence.cli.transcribe', side_effect=execute), \
                patch('sys.stdout', new_callable=StringIO):
            self.assertEqual(main(argv), 0)
            self.assertEqual(main(argv), 0)
        self.assertEqual(len(fake.calls), 1)
        result = self.store.latest('result')
        self.assertEqual(result['provenance']['model'], 'gemini-3.8-flash')
        self.assertNotIn('temperature', result['provenance']['generation'])
        self.assertNotEqual(result['fingerprint'], self.request['fingerprint'])
        self.assertEqual(Config().model, 'gemini-3.5-flash-lite')
        for change in ({'thinking_level': 'minimal'}, {'temperature': 0.5}):
            with self.assertRaises(ValueError):
                replace(config, **change)

    def test_flash_38_sdk_payload_omits_sampling_and_disables_hidden_retries(self):
        config = replace(self.config, model='gemini-3.8-flash', attempts=1, daily_limit=20)
        request = prepare_request(self.inventory, self.letter, config)
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(503, json={'error': {'code': 503, 'message': 'synthetic'}})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        gemini = Gemini(config, 'dummy-offline-key', http_client=client)
        try:
            with self.assertRaises(Exception):
                gemini.send(request, request['provenance']['prompt'])
        finally:
            gemini.close()
        self.assertEqual(len(requests), 1)
        self.assertIn('gemini-3.8-flash', requests[0].url.path)
        generation = json.loads(requests[0].content)['generationConfig']
        for parameter in ('temperature', 'topP', 'topK', 'candidateCount'):
            self.assertNotIn(parameter, generation)
        self.assertEqual(generation['thinkingConfig']['thinking_level'], 'HIGH')
        self.assertEqual(generation['responseMimeType'], 'application/json')

    def test_quota_write_failure_prevents_transport(self):
        fake = FakeTransport([response(self.doc)])
        with patch("correspondence.execution.atomic_json", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                transcribe(self.store, self.letter, self.request, self.config, lambda: fake, quota=self.quota)
        self.assertFalse(fake.calls)

    def test_daily_billing_and_auth_stop_batch(self):
        for code, message in ((401, "authentication"), (404, "model unavailable"), (429, "billing quota")):
            result, _, fake = self.execute([ServiceError(code, message)], fresh=True)
            self.assertTrue(result["stop_batch"])
            self.assertEqual(len(fake.calls), 1)
        result, _, _ = self.execute([ServiceError(429, "requests per day")], fresh=True)
        self.assertEqual(result["execution"], "paused")
        with self.assertRaises(QuotaReached):
            self.quota.update()

    def test_retry_after_is_not_shortened(self):
        result, _, fake = self.execute([ServiceError(503, headers={"Retry-After": "3600"})])
        self.assertEqual(result["execution"], "paused")
        self.assertEqual(fake.calls.__len__(), 1)
        self.assertFalse(self.clock.waits)

    def test_retry_hints_and_connection_failures(self):
        kind, delay = error_policy(ServiceError(429, payload={"error": {"details": [{"retryDelay": "75s"}]}}))
        self.assertEqual((kind, delay), ("retry", 75))
        self.assertEqual(error_policy(TimeoutError())[0], "retry")
        self.assertEqual(error_policy(ServiceError(503))[0], "retry")

    def test_unsuccessful_structured_service_response_is_saved(self):
        payload = {"error": {"code": 403, "message": "synthetic permission failure"}}
        self.execute([ServiceError(403, payload=payload)])
        end = self.store.latest("attempt_end")
        self.assertEqual(read_json(self.store.root / end["error_response"]), payload)

    def test_correction_request_size_checked_before_second_reservation(self):
        # Reserve enough for the initial request, but not the corrective prompt.
        self.config = replace(self.config, max_request_bytes=self.request["estimated_bytes"])
        bad = response(self.doc)
        bad["candidates"][0]["content"]["parts"][0]["text"] = "malformed original text"
        result, _, fake = self.execute([bad])
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("size limit", result["errors"][0])
        self.assertEqual(len(result["attempt_ids"]), 1)

    def test_keyboard_interrupt_preserves_unknown_usage(self):
        with self.assertRaises(KeyboardInterrupt):
            self.execute([KeyboardInterrupt()])
        self.assertEqual(self.store.results()[-1]["execution"], "interrupted")
        self.assertIsNone(self.store.latest("attempt_end")["usage"]["total"])
        with self.assertRaisesRegex(ValueError, "Interrupted"):
            self.execute([response(self.doc)])
        result, _, _ = self.execute([response(self.doc)], retry_interrupted=True)
        self.assertEqual(result["execution"], "complete")

    def test_response_recovered_after_result_checkpoint_failure(self):
        original = self.store.append
        def interrupted(kind, data):
            if kind == "result":
                raise OSError("synthetic crash at result checkpoint")
            return original(kind, data)
        with patch.object(self.store, "append", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.execute([response(self.doc)])
        result, reused = transcribe(self.store, self.letter, self.request, self.config,
                                   lambda: self.fail("Recovery must not send"))
        self.assertTrue(reused)
        self.assertEqual(result["execution"], "complete")

    def test_pending_start_blocks_unacknowledged_paid_retry(self):
        self.store.append("attempt_start", dict(attempt_id="att_unknown", letter_id=self.letter["letter_id"],
                          fingerprint=self.request["fingerprint"], run_id="run_unknown"))
        with self.assertRaisesRegex(ValueError, "unknown outcome"):
            self.execute([response(self.doc)])

    def test_damaged_journal_fails_closed_preserves_bytes(self):
        with self.store.journal.open("ab") as stream:
            stream.write(b'{"partial')
        before = self.store.journal.read_bytes()
        with self.assertRaisesRegex(ValueError, "Damaged journal"):
            self.store.append("review", {})
        self.assertEqual(before, self.store.journal.read_bytes())

    def test_lock_excludes_other_writer_and_releases(self):
        with lock(self.root / "write.lock"):
            with self.assertRaises(RuntimeError):
                with lock(self.root / "write.lock"):
                    self.fail("Concurrent lock acquired")
        with lock(self.root / "write.lock"):
            pass

    def test_real_sdk_serialization_and_hidden_retries_disabled(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(503, json={"error": {"code": 503, "message": "synthetic"}})
        client = httpx.Client(transport=httpx.MockTransport(handler))
        gemini = Gemini(self.config, "dummy-offline-key", http_client=client)
        try:
            with self.assertRaises(Exception):
                gemini.send(self.request, self.request["provenance"]["prompt"])
        finally:
            gemini.close()
        self.assertEqual(len(requests), 1)
        payload = json.loads(requests[0].content)
        self.assertEqual(requests[0].url.host, "generativelanguage.googleapis.com")
        self.assertIn("gemini-3.5-flash-lite", requests[0].url.path)
        self.assertEqual(payload["generationConfig"]["temperature"], 1.0)
        # This pinned SDK preserves the nested protobuf snake_case spelling.
        self.assertEqual(payload["generationConfig"]["thinkingConfig"]["thinking_level"], "HIGH")
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(len(payload["contents"][0]["parts"]), 5)

    def test_real_sdk_success_response_normalization_offline(self):
        wire = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": encoded(self.doc).decode()}]}}],
                "modelVersion": "synthetic-returned-version",
                "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20,
                                  "thoughtsTokenCount": 5, "cachedContentTokenCount": 0, "totalTokenCount": 125}}
        client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=wire)))
        gemini = Gemini(self.config, "dummy-offline-key", http_client=client)
        result, _ = transcribe(self.store, self.letter, self.request, self.config, lambda: gemini, quota=self.quota)
        self.assertEqual(result["execution"], "complete")
        self.assertEqual(result["returned_model"], "synthetic-returned-version")
        self.assertEqual(self.store.latest("attempt_end")["usage"]["total"], 125)

    def test_old_recovered_response_does_not_reset_cache_age(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()
        self.store.append("attempt_start", dict(attempt_id="att_old", letter_id=self.letter["letter_id"],
                          fingerprint=self.request["fingerprint"], run_id="run_old"))
        raw = self.store.blob(encoded(response(self.doc)), ".json")
        self.store.append("attempt_end", dict(attempt_id="att_old", ended_at=old, response=raw))
        result, reused, fake = self.execute([response(self.doc)])
        self.assertFalse(reused)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(self.store.results()[0]["saved_at"], old)

    def test_credentials_explicit_and_empty(self):
        path = self.root / ".env"
        path.write_text("GEMINI_API_KEY=\n")
        with self.assertRaises(ValueError):
            api_key(path)
        path.write_text("GEMINI_API_KEY=dummy\n")
        self.assertEqual(api_key(path), "dummy")
