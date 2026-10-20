"""Explainable local candidates; no model calls or automatic confirmations."""
from .schema import date_interval, usable_date
from .storage import digest, encoded


def relationship_id(source, target, kind):
    return "rel_" + digest(encoded([source, target, kind]))[:24]


def record_basis(record):
    return digest(encoded({"document": record.get("document"), "active": record["active"],
                           "execution": record["execution"]}))


def decisions(store):
    return {e["data"]["relationship_id"]: e["data"] for e in store.events()
            if e["kind"] == "review" and e["data"].get("kind") == "relationship"}


def person_key(field):
    if field.get("certainty") not in {"explicit", "inferred"} or not field.get("value") or not field.get("evidence"):
        return None
    return ("person:" + field["person_id"] if field.get("person_id")
            else "unreviewed:" + (field.get("normalized") or field.get("value") or "").strip().casefold()) or None


def reversed_pair(a, b):
    keys = [person_key(m.get(k, {})) for m, k in ((a, "sender"), (a, "recipient"), (b, "sender"), (b, "recipient"))]
    return all(k and k != "unreviewed:" for k in keys) and keys[0] == keys[3] and keys[1] == keys[2]


def date_overlap(ref, target):
    interval = date_interval(ref.get("date_normalized"), ref.get("date_precision"))
    if ref.get("certainty") not in {"explicit", "inferred"} or not interval:
        return False
    # Do not trust automatic expansions of short years in correspondence references.
    import re
    if not re.search(r"\b\d{4}\b", ref.get("date_as_written") or ""):
        return False
    if ref["date_normalized"][:4] not in re.findall(r"\b\d{4}\b", ref["date_as_written"]):
        return False
    return bool(target and interval[0] <= target[1] and target[0] <= interval[1])


def chronology(source, target):
    a, b = usable_date(source["metadata"]["date"]), usable_date(target["metadata"]["date"])
    if not a or not b:
        return ["chronology unknown/partial"]
    if a[1] < b[0]:
        return ["contradictory chronology: purported reply predates target"]
    if a[0] <= b[1]:
        return ["chronology overlaps; order uncertain"]
    return []


def match(records):
    available = [r for r in records if r["active"] and r["execution"] == "complete" and r["document"]]
    candidates, unresolved = {}, []
    for source in available:
        a = source["document"]
        refs = a["references"]
        matched_refs = set()
        for target in available:
            if target["letter_id"] == source["letter_id"]:
                continue
            b = target["document"]
            reverse = reversed_pair(a["metadata"], b["metadata"])
            specific = {e["value"] for e in a["entities"] if e["kind"] in {"specimen", "catalogue"}
                        and e["certainty"] == "explicit"} & {
                            e["value"] for e in b["entities"] if e["kind"] in {"specimen", "catalogue"}
                            and e["certainty"] == "explicit"}
            topics = {e["normalized"] or e["value"] for e in a["entities"] if e["kind"] == "subject"} & {
                e["normalized"] or e["value"] for e in b["entities"] if e["kind"] == "subject"}
            found = []
            for index, ref in enumerate(refs):
                if ref["evidence"] and date_overlap(ref, usable_date(b["metadata"]["date"])) and (reverse or specific):
                    found.append((ref["kind"], 8 + 3 * bool(reverse) + 2 * bool(specific),
                                  ["explicit referenced date overlaps target",
                                   "reversed correspondent readings" if reverse else "shared specimen identifiers"],
                                  ref["evidence"], index))
                    matched_refs.add(index)
            if not found and (specific or (reverse and topics)):
                found.append(("related_subject", 2 + 2 * bool(specific),
                              ["shared specimen identifiers" if specific else "pair and topic only; no reply evidence"],
                              [ev for e in a["entities"] if e["kind"] in {"specimen", "catalogue", "subject"}
                               for ev in e["evidence"]], None))
            for kind, score, support, evidence, index in found:
                rid = relationship_id(source["letter_id"], target["letter_id"], kind)
                contradictions = chronology(a, b) if kind == "reply_to" else []
                item = candidates.setdefault(rid, dict(relationship_id=rid, from_letter=source["letter_id"],
                         to_letter=target["letter_id"], relation=kind, status="candidate", score=score,
                         support=support, evidence=[], contradictions=contradictions,
                         shared_identifiers=sorted(specific), source_revisions=[
                             source["result"]["revision_id"], target["result"]["revision_id"]],
                         source_basis=[record_basis(source), record_basis(target)]))
                item["evidence"].extend(evidence)
        for index, ref in enumerate(refs):
            if index not in matched_refs:
                unresolved.append(dict(reference_id="ref_" + digest(encoded([source["letter_id"], ref]))[:24],
                                       from_letter=source["letter_id"], status="unresolved", reference=ref))
    return dict(candidates=sorted(candidates.values(), key=lambda c: (-c["score"], c["relationship_id"])),
                unresolved=unresolved)


def graph_warnings(store, records, proposed=None):
    links = decisions(store)
    if proposed:
        links[proposed["relationship_id"]] = proposed
    confirmed = [l for l in links.values() if l["decision"] == "confirmed" and l["relation"] == "reply_to"]
    by_id = {r["letter_id"]: r for r in records}
    graph, warnings = {}, []
    for link in confirmed:
        a, b = link["from_letter"], link["to_letter"]
        graph.setdefault(a, []).append(b)
        if a == b:
            warnings.append("self-link")
        if a in by_id and b in by_id and by_id[a]["document"] and by_id[b]["document"]:
            warnings += [w for w in chronology(by_id[a]["document"], by_id[b]["document"])
                         if w.startswith("contradictory")]
    def walk(node, visiting, done):
        if node in visiting:
            return True
        if node in done:
            return False
        visiting.add(node)
        if any(walk(other, visiting, done) for other in graph.get(node, [])):
            return True
        visiting.remove(node)
        done.add(node)
        return False
    done = set()
    if any(walk(node, set(), done) for node in graph):
        warnings.append("cycle in confirmed reply links")
    return sorted(set(warnings))


def relationship_view(store, records):
    saved = store.latest("matching", {"candidates": [], "unresolved": []})
    by_id = {r["letter_id"]: r for r in records}
    links = {c["relationship_id"]: dict(c) for c in saved["candidates"]}
    for rid, decision in decisions(store).items():
        if rid not in links:
            links[rid] = dict(relationship_id=rid, from_letter=decision["from_letter"],
                             to_letter=decision["to_letter"], relation=decision["relation"],
                             support=[], evidence=[], contradictions=[], score=None)
        links[rid].update(status=decision["decision"], decision=decision)
    for link in links.values():
        expected = link.get("source_revisions")
        current = [(by_id.get(lid, {}).get("result") or {}).get("revision_id")
                   for lid in (link["from_letter"], link["to_letter"])]
        current_basis = [record_basis(by_id[lid]) if lid in by_id else None
                         for lid in (link["from_letter"], link["to_letter"])]
        decision_basis = link.get("decision", {}).get("source_basis")
        link["needs_rematch"] = bool((expected and expected != current)
                                     or (link.get("source_basis") and link["source_basis"] != current_basis))
        link["decision_needs_review"] = bool(decision_basis and decision_basis != current_basis)
    return dict(links=list(links.values()), unresolved=saved["unresolved"],
                warnings=graph_warnings(store, records))
