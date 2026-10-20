from copy import deepcopy
import unittest
from correspondence.provider import completion
from correspondence.schema import date_interval, usable_date, validate_document, parse_response
from correspondence.usage import read_usage, estimate, aggregate
from .helpers import ROOT, document, response


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.doc = document(["img_one", "img_two"])

    def test_valid_unreviewed_output_is_not_verified(self):
        errors, reasons = validate_document(self.doc, ["img_one", "img_two"])
        self.assertEqual(errors, [])
        self.assertIn("sender: unknown", reasons)

    def test_page_coverage_duplicate_order_and_empty(self):
        for pages in ([self.doc["pages"][0]], [self.doc["pages"][0]] * 2, self.doc["pages"][::-1]):
            doc = dict(self.doc, pages=pages)
            self.assertTrue(validate_document(doc, ["img_one", "img_two"])[0])
        self.doc["pages"][0]["text"] = ""
        self.assertTrue(validate_document(self.doc, ["img_one", "img_two"])[0])

    def test_blank_unrelated_and_uncertainty(self):
        self.doc["pages"][0].update(text="[blank]", status="blank")
        self.doc["pages"][1].update(text="[uncertain: specimen] [illegible]", status="unrelated")
        errors, reasons = validate_document(self.doc, ["img_one", "img_two"])
        self.assertFalse(errors)
        self.assertTrue(any("uncertain/illegible" in r for r in reasons))

    def test_evidence_and_filename_conflicts(self):
        self.doc["metadata"]["sender"] = dict(value="A", normalized="Alice", certainty="explicit",
                                              evidence=[{"image_id": "img_one", "quote": "Yours, A."}])
        errors, reasons = validate_document(self.doc, ["img_one", "img_two"], {"sender": "Wrong"})
        self.assertFalse(errors)
        self.assertTrue(any("filename/document conflict" in r for r in reasons))
        self.doc["metadata"]["sender"]["evidence"][0]["quote"] = "not in source"
        self.assertTrue(any("not found" in r for r in validate_document(self.doc, ["img_one", "img_two"])[1]))

    def test_partial_dates_and_two_digit_year_not_expanded(self):
        self.assertIsNotNone(date_interval("1899", "year"))
        self.assertIsNotNone(date_interval("1899-02", "month"))
        for value in ("99", "1899-02-30", "1899-13-01"):
            self.assertIsNone(date_interval(value, "day"))
        self.assertIsNone(usable_date(dict(value="May 2, 99", normalized="1899-05-02", certainty="explicit", precision="day")))
        self.doc["metadata"]["date"].update(value="May 2, 99", normalized="1899-05-02", precision="day")
        errors, reasons = validate_document(self.doc, ["img_one", "img_two"])
        self.assertFalse(errors)
        self.assertTrue(any("normalization unsupported" in r for r in reasons))

    def test_truncation_refusal_empty_and_missing_reason(self):
        for finish in ("MAX_TOKENS", "SAFETY", "RECITATION"):
            text, errors, retry = completion(response(self.doc, finish))
            self.assertTrue(text)
            self.assertTrue(errors)
            self.assertFalse(retry)
        self.assertTrue(completion({})[1])
        answer = response(self.doc)
        answer["prompt_feedback"] = {"block_reason": "SAFETY"}
        self.assertFalse(completion(answer)[2])
        answer = response(self.doc)
        answer["candidates"][0]["finish_reason"] = None
        self.assertTrue(completion(answer)[1])

    def test_thought_text_excluded(self):
        answer = response(self.doc)
        answer["candidates"][0]["content"]["parts"].insert(0, {"thought": True, "text": "private thought"})
        self.assertNotIn("private thought", completion(answer)[0])

    def test_malformed_structures_preserved(self):
        self.assertTrue(parse_response("{truncated", ["img_one"], {})[1])
        for key in ("metadata", "notes", "entities", "translations", "references", "pages"):
            doc = dict(self.doc, **{key: None})
            self.assertTrue(validate_document(doc, ["img_one", "img_two"])[0], key)
        for value in ([], None, 12):
            doc = deepcopy(self.doc)
            doc["metadata"]["date"] = value
            self.assertTrue(validate_document(doc, ["img_one", "img_two"])[0])

    def test_nested_bad_types_and_duplicate_json_keys_fail_without_deleting_text(self):
        import json
        doc = deepcopy(self.doc)
        doc["metadata"]["sender"]["certainty"] = ["explicit"]
        self.assertTrue(parse_response(json.dumps(doc), ["img_one", "img_two"], {})[1])
        self.assertTrue(parse_response('{"pages": [], "pages": ["substantive"]}', [], {})[1])

    def test_saved_partial_response_offline_replay(self):
        from correspondence.storage import read_json
        saved = read_json(ROOT / "test" / "fixtures" / "truncated-response.json")
        text, errors, retry = completion(saved)
        self.assertIn("00012", text)
        self.assertTrue(errors)
        self.assertFalse(retry)

    def test_unknown_usage_and_non_double_counted_reasoning(self):
        usage = read_usage(response(self.doc))
        self.assertEqual(usage["billed_output"], 60)
        self.assertEqual(usage["total"], 160)
        unknown = read_usage({})
        self.assertTrue(all(v is None for v in unknown.values()))
        self.assertIsNone(aggregate([{"usage": usage}, {"usage": unknown}])["total"])
        self.assertEqual(aggregate([])["total"], 0)

    def test_cost_requires_explicit_rates_and_known_counters(self):
        usage = read_usage(response(self.doc))
        self.assertIsNone(estimate(usage, "m", None))
        rates = dict(model="m", currency="TEST", source="synthetic rates", as_of="2000-01-01",
                     input=1, cached=.1, output=2)
        self.assertAlmostEqual(estimate(usage, "m", rates)["amount"], .000202)
        usage["cached"] = None
        self.assertIsNone(estimate(usage, "m", rates))
