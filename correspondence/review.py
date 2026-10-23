"""Append-only human corrections, separate from service responses."""
from copy import deepcopy
from .catalogue import catalogue_names
from .schema import FIELDS, RELATIONS, date_interval, validate_document
from .storage import identity


def current_records(store, inventory):
    results = store.current_results()
    images = {i["image_id"]: i for i in inventory["images"]}
    reviews = [e for e in store.events() if e["kind"] == "review"]
    registered = people(store)
    records = []
    for letter in inventory["letters"]:
        result = results.get(letter["letter_id"])
        record = deepcopy(letter)
        record.update(execution="blocked" if letter["grouping"] == "needs_review" else "unprocessed", metadata_review="unreviewed",
                      transcription_review="unreviewed", relationship_review="unreviewed",
                      document=None, result=result, review_history=[], stale_reviews=[], catalogue_date=None)
        if result:
            manifest = result["provenance"]["images"]
            stale = ([i["image_id"] for i in manifest] != letter["image_ids"] or any(
                i["image_id"] not in images or images[i["image_id"]]["sha256"] != i["original_sha256"]
                or images[i["image_id"]]["status"] != "ready" for i in manifest))
            record["execution"] = "stale" if stale else result["execution"]
            if result["execution"] == "complete":
                record["document"] = deepcopy(result["document"])
            record["review_reasons"] += result.get("review_reasons", []) + result.get("errors", [])
            if stale:
                record["review_reasons"].append("Source manifest changed/unavailable; earlier reading retained as stale")
        for event in reviews:
            correction = event["data"]
            if correction.get("kind") != "letter" or correction["letter_id"] != letter["letter_id"]:
                continue
            record["review_history"].append(event)
            if (not result or correction["base_revision"] != result["revision_id"]
                    or record["execution"] == "stale"):
                record["stale_reviews"].append(event["event_id"])
                continue
            doc = record["document"]
            if doc is None:
                continue
            if correction.get("pages"):
                record["catalogue_date"] = None
                record["transcription_review"] = "in_progress"
                record["metadata_review"] = "in_progress"
                record["relationship_review"] = "in_progress"
            elif correction.get("metadata"):
                record["metadata_review"] = "in_progress"
                record["relationship_review"] = "in_progress"
            doc["metadata"].update(deepcopy(correction.get("metadata", {})))
            if "date" in correction.get("metadata", {}):
                record["catalogue_date"] = None
            confirmed = correction.get("catalogue_date")
            if confirmed and confirmed.get("date_basis") == doc["metadata"]["date"]:
                record["catalogue_date"] = dict(deepcopy(confirmed), source=correction["source"],
                                                review_event=event["event_id"])
            for page in doc["pages"]:
                page.update(deepcopy(correction.get("pages", {}).get(page["image_id"], {})))
            if "summary" in correction:
                doc["summary"] = correction["summary"]
            for field in ("metadata_review", "transcription_review", "relationship_review"):
                if field in correction:
                    record[field] = correction[field]
        if record["stale_reviews"]:
            record["review_reasons"].append("Earlier human corrections need rebasing; preserved in review history")
        if record["document"]:
            # Filename hints can change after an explicit path reconciliation. Keep
            # historical validation in the saved result; display current conflicts.
            prefix = "filename/document conflict: "
            _, reasons = validate_document(record["document"], record["image_ids"], record["hints"])
            record["review_reasons"] = [r for r in record["review_reasons"] if not r.startswith(prefix)]
            record["review_reasons"] += [r for r in reasons if r.startswith(prefix)]
        record["catalogue_names"] = catalogue_names(
            record["document"]["metadata"] if record["document"] else {}, record["hints"], registered)
        if record["catalogue_date"]:
            record["review_reasons"] = [
                "date: abbreviated/ambiguous source date; separate confirmed date used for catalogue sorting"
                if r == "date: normalization unsupported or ambiguous; excluded from chronology" else r
                for r in record["review_reasons"]]
        records.append(record)
    return records


def people(store):
    return {e["data"]["person_id"]: e["data"] for e in store.events()
            if e["kind"] == "review" and e["data"].get("kind") == "person"}


def apply_review(store, inventory, patch):
    patch = deepcopy(patch)
    if not patch.get("source"):
        raise ValueError("Every review needs a source/reason; reviewer is optional")
    kind = patch.get("kind")
    if kind == "person":
        patch.setdefault("person_id", identity("per_"))
        if (not isinstance(patch.get("name"), str) or not patch["name"].strip()
                or not isinstance(patch.get("aliases"), list)
                or not all(isinstance(a, str) for a in patch["aliases"])
                or patch.get("review_status") != "approved"):
            raise ValueError("A person needs name, aliases array and approved review_status")
        if not patch["person_id"].startswith("per_"):
            raise ValueError("Person IDs must start per_")
        if "standardize_display" in patch and not isinstance(patch["standardize_display"], bool):
            raise ValueError("standardize_display must be true or false")
    elif kind == "letter":
        record = next((r for r in current_records(store, inventory) if r["letter_id"] == patch.get("letter_id")), None)
        if (not record or not record["document"] or record["execution"] != "complete"
                or patch.get("base_revision") != record["result"]["revision_id"]):
            raise ValueError("Letter correction must cite the current complete base_revision")
        if set(patch.get("metadata", {})) - set(FIELDS):
            raise ValueError("Unknown metadata field")
        registered = people(store)
        for field in patch.get("metadata", {}).values():
            if field.get("person_id") and field["person_id"] not in registered:
                raise ValueError("Unknown approved person_id; register it first")
        document = deepcopy(record["document"])
        document["metadata"].update(patch.get("metadata", {}))
        if "catalogue_date" in patch:
            confirmed = patch["catalogue_date"]
            date = document["metadata"]["date"]
            if (not isinstance(confirmed, dict)
                    or not date_interval(confirmed.get("value"), confirmed.get("precision"))
                    or confirmed.get("value") != date.get("normalized")
                    or confirmed.get("precision") != date.get("precision")):
                raise ValueError("Catalogue date must confirm the current normalized date and precision")
            patch["catalogue_date"] = dict(value=confirmed["value"], precision=confirmed["precision"],
                                           date_basis=deepcopy(date))
        pages = {p["image_id"]: p for p in document["pages"]}
        for iid, changes in patch.get("pages", {}).items():
            if iid not in pages or set(changes) - {"text", "status", "annotations"}:
                raise ValueError("Page correction must target a supplied image and reading fields only")
            pages[iid].update(changes)
        if "summary" in patch:
            document["summary"] = patch["summary"]
        errors, _ = validate_document(document, record["image_ids"], record["hints"])
        if errors:
            raise ValueError("; ".join(errors))
        for field in ("metadata_review", "transcription_review", "relationship_review"):
            if field in patch and patch[field] not in {"unreviewed", "in_progress", "approved"}:
                raise ValueError("Review states: unreviewed, in_progress, approved")
    elif kind == "relationship":
        from .relationships import graph_warnings, relationship_id, record_basis
        ids = {l["letter_id"] for l in inventory["letters"]}
        source, target = patch.get("from_letter"), patch.get("to_letter")
        if source not in ids or target not in ids or source == target or patch.get("relation") not in RELATIONS:
            raise ValueError("Relationships require two existing distinct letters and a known relation")
        if patch.get("decision") not in {"confirmed", "rejected"}:
            raise ValueError("Relationship decision must be confirmed or rejected")
        patch["relationship_id"] = relationship_id(source, target, patch["relation"])
        records = current_records(store, inventory)
        basis = {r["letter_id"]: record_basis(r) for r in records}
        patch["source_basis"] = [basis[source], basis[target]]
        warnings = graph_warnings(store, records, patch)
        if warnings and patch["decision"] == "confirmed":
            raise ValueError("Cannot confirm contradictory link: " + "; ".join(warnings))
    else:
        raise ValueError("Review kind must be letter, person, or relationship")
    return store.append("review", patch)
