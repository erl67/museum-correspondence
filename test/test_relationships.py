from copy import deepcopy
import unittest
from correspondence.relationships import match, graph_warnings, relationship_id, relationship_view
from correspondence.review import apply_review
from .helpers import document, Workspace


def letter(lid, sender, recipient, date, reference=None, topic=None, specimen=None):
    doc = document(["img_" + lid])
    for name, value in (("sender", sender), ("recipient", recipient), ("date", date)):
        doc["metadata"][name].update(value=value, normalized=value, certainty="explicit",
                                    evidence=[{"image_id": "img_" + lid, "quote": value}])
    doc["metadata"]["date"]["precision"] = "day"
    if reference:
        doc["references"] = [dict(kind="reply_to", description="Synthetic explicit reply",
            date_as_written=reference, date_normalized=reference, date_precision="day", certainty="explicit",
            evidence=[{"image_id": "img_" + lid, "quote": "Your letter of " + reference}])]
    for kind, value in (("subject", topic), ("specimen", specimen)):
        if value:
            doc["entities"].append(dict(kind=kind, value=value, normalized=value, role="mentioned",
                certainty="explicit", evidence=[{"image_id": "img_" + lid, "quote": value}]))
    return dict(letter_id=lid, active=True, execution="complete", document=doc, result={"revision_id": "rev_" + lid})


class MatchingTests(Workspace):
    def test_strong_reply_is_candidate_not_confirmed(self):
        records = [letter("earlier", "A", "B", "1899-05-01"),
                   letter("reply", "B", "A", "1899-05-03", reference="1899-05-01")]
        result = match(records)
        self.assertEqual(len(result["candidates"]), 1)
        link = result["candidates"][0]
        self.assertEqual((link["from_letter"], link["to_letter"], link["relation"], link["status"]),
                         ("reply", "earlier", "reply_to", "candidate"))
        self.assertFalse(result["unresolved"])
        self.assertTrue(link["evidence"])

    def test_ambiguous_alternatives_retained(self):
        records = [letter("one", "A", "B", "1899-05-01"), letter("two", "A", "B", "1899-05-01"),
                   letter("reply", "B", "A", "1899-05-03", reference="1899-05-01")]
        self.assertEqual(len(match(records)["candidates"]), 2)

    def test_shared_topics_do_not_establish_reply(self):
        records = [letter("one", "A", "B", "1899-05-01", topic="swallows"),
                   letter("two", "B", "A", "1899-05-03", topic="swallows")]
        self.assertTrue(all(c["relation"] == "related_subject" for c in match(records)["candidates"]))
        records[1] = letter("two", "C", "D", "1899-05-03", topic="swallows")
        self.assertEqual(match(records)["candidates"], [])

    def test_missing_reference_unresolved_no_fabrication(self):
        result = match([letter("reply", "B", "A", "1899-05-03", reference="1899-04-01")])
        self.assertEqual(len(result["unresolved"]), 1)
        self.assertFalse(result["candidates"])

    def test_chronology_conflict_kept_as_evidence(self):
        records = [letter("future", "A", "B", "1900-05-01"),
                   letter("reply", "B", "A", "1899-05-03", reference="1900-05-01")]
        link = match(records)["candidates"][0]
        self.assertTrue(any("contradictory chronology" in c for c in link["contradictions"]))

    def test_mentioned_or_enclosed_not_relabeled_reply(self):
        records = [letter("one", "A", "B", "1899-05-01"),
                   letter("two", "B", "A", "1899-05-03", reference="1899-05-01")]
        for kind in ("mentions", "encloses"):
            records[1]["document"]["references"][0]["kind"] = kind
            self.assertEqual(match(records)["candidates"][0]["relation"], kind)

    def test_branching_and_multiple_replies(self):
        records = [letter("one", "A", "B", "1899-05-01"),
                   letter("two", "B", "A", "1899-05-03", reference="1899-05-01"),
                   letter("three", "B", "A", "1899-05-04", reference="1899-05-01")]
        self.assertEqual(len(match(records)["candidates"]), 2)
        records[2]["document"]["references"].append(dict(records[2]["document"]["references"][0],
                                                       kind="mentions", date_as_written="1899-05-03",
                                                       date_normalized="1899-05-03"))
        # Shared exact specimen permits an independently evidenced reference to the other letter.
        for record in records[1:]:
            record["document"]["entities"] = [{"kind": "specimen", "value": "001", "normalized": "001",
                "certainty": "explicit", "role": "mentioned", "evidence": [{"image_id": "img_" + record["letter_id"], "quote": "001"}]}]
        self.assertTrue(any(c["to_letter"] == "two" for c in match(records)["candidates"]))

    def test_partial_dates_allow_uncertainty(self):
        records = [letter("one", "A", "B", "1899-05-01"),
                   letter("two", "B", "A", "1899-05-03", reference="1899-05-01")]
        records[1]["document"]["metadata"]["date"].update(value="May 1899", normalized="1899-05", precision="month")
        self.assertIn("chronology overlaps; order uncertain", match(records)["candidates"][0]["contradictions"])

    def test_rejected_decisions_survive_rematching(self):
        records = [letter("one", "A", "B", "1899-05-01"),
                   letter("two", "B", "A", "1899-05-03", reference="1899-05-01")]
        result = match(records)
        self.store.append("matching", result)
        link = result["candidates"][0]
        self.store.append("review", dict(kind="relationship", relationship_id=link["relationship_id"],
                          from_letter="two", to_letter="one", relation="reply_to", decision="rejected", source="test"))
        self.store.append("matching", match(records))
        self.assertEqual(relationship_view(self.store, records)["links"][0]["status"], "rejected")

    def test_metadata_correction_invalidates_matching_basis_without_new_transcription(self):
        records = [letter("one", "A", "B", "1899-05-01"),
                   letter("two", "B", "A", "1899-05-03", reference="1899-05-01")]
        self.store.append("matching", match(records))
        records[0]["document"]["metadata"]["date"]["normalized"] = "1899-05-02"
        self.assertTrue(relationship_view(self.store, records)["links"][0]["needs_rematch"])

    def test_confirm_and_reject_link_commands_and_chronology_validation(self):
        # Use real canonical records to exercise the staff update path.
        from correspondence.execution import Quota, transcribe
        from .helpers import Clock, FakeTransport, response
        from correspondence.review import current_records
        self.setup_letter(("A-B-1899-05-01.jpg", "B-A-1899-05-03.jpg"))
        from correspondence.images import prepare_request
        clock = Clock()
        for i, item in enumerate(self.inventory["letters"]):
            request = prepare_request(self.inventory, item, self.config)
            doc = document(item["image_ids"])
            doc["metadata"]["date"].update(value=f"1899-05-0{1 + i * 2}", normalized=f"1899-05-0{1 + i * 2}",
                                          certainty="explicit", precision="day")
            transcribe(self.store, item, request, self.config, lambda d=doc: FakeTransport([response(d)]),
                       quota=Quota(self.config, clock.time, clock.sleep))
        first, second = [l["letter_id"] for l in self.inventory["letters"]]
        patch = dict(kind="relationship", from_letter=second, to_letter=first,
                     relation="reply_to", decision="confirmed", source="synthetic explicit staff review")
        apply_review(self.store, self.inventory, patch)
        self.assertEqual(relationship_view(self.store, current_records(self.store, self.inventory))["links"][0]["status"], "confirmed")
        with self.assertRaisesRegex(ValueError, "contradictory"):
            apply_review(self.store, self.inventory, dict(patch, from_letter=first, to_letter=second))
        apply_review(self.store, self.inventory, dict(patch, decision="rejected"))
        self.assertEqual(relationship_view(self.store, current_records(self.store, self.inventory))["links"][0]["status"], "rejected")

    def test_cycles_identified_self_links_rejected(self):
        records = [letter("one", "A", "B", "1899-05-01"), letter("two", "B", "A", "1899-05-01")]
        for source, target in (("one", "two"), ("two", "one")):
            self.store.append("review", dict(kind="relationship", relationship_id=relationship_id(source, target, "reply_to"),
                              from_letter=source, to_letter=target, relation="reply_to", decision="confirmed", source="test"))
        self.assertIn("cycle in confirmed reply links", graph_warnings(self.store, records))
        with self.assertRaises(ValueError):
            apply_review(self.store, {"letters": [{"letter_id": "one"}]},
                         dict(kind="relationship", source="test", from_letter="one", to_letter="one",
                              relation="reply_to", decision="confirmed"))

    def test_approved_different_identities_not_merged_by_initials(self):
        records = [letter("one", "A.", "B.", "1899-05-01"),
                   letter("two", "B.", "A.", "1899-05-03", reference="1899-05-01")]
        records[0]["document"]["metadata"]["sender"]["person_id"] = "per_A"
        records[1]["document"]["metadata"]["recipient"]["person_id"] = "per_other_A"
        self.assertFalse(match(records)["candidates"])
