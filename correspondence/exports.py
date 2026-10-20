"""Offline UTF-8 reports, normalized CSV tables, and a read-only viewer bundle."""
import csv
from io import StringIO
import json
from pathlib import Path
import re
from .relationships import relationship_view
from .review import current_records, people
from .schema import usable_date
from .storage import atomic_bytes, atomic_json, now
from .usage import aggregate
from .plaintext import reading, text_paths


def cell(value):
    if value is None:
        return ""
    value = str(value)
    # Canonical JSON/text stays untouched. Prefix dangerous spreadsheet cells only.
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def write_csv(path, fields, rows):
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: cell(v) for k, v in row.items()})
    atomic_bytes(path, b"\xef\xbb\xbf" + output.getvalue().encode("utf-8"))


def report(record, images, attempts):
    lines = [f"LETTER {record['letter_id']}", f"Transcription: {record['execution']}",
             f"Grouping: {record['grouping']}", f"Metadata review: {record['metadata_review']}",
             f"Human transcription review: {record['transcription_review']}",
             f"Relationship review: {record['relationship_review']}", "", "ORDERED SOURCE FILES"]
    for iid in record["image_ids"]:
        image = images[iid]
        lines.append(f"{iid} | {image['path']} | {image['status']}")
    lines += ["", "REVIEW REASONS"] + (record["review_reasons"] or ["None recorded; structural completion is not verification."])
    lines += ["", "FILENAME/FOLDER HINTS", json.dumps(record["hints"], ensure_ascii=False, indent=2)]
    document = record["document"]
    if document:
        lines += ["", "METADATA (readings, search values, evidence)",
                  json.dumps(document["metadata"], ensure_ascii=False, indent=2),
                  "", "INTERPRETIVE SUMMARY", document["summary"], "", "SOURCE-LANGUAGE TRANSCRIPTION"]
        for page in document["pages"]:
            lines += ["", f"=== PAGE {page['image_id']} | {images[page['image_id']]['path']} | {page['status']} ===",
                      page["text"]]
            for annotation in page["annotations"]:
                lines += [f"[Annotation: {annotation['kind']}]", annotation["text"]]
        lines += ["", "SEPARATE NOTES"] + document["notes"]
        for translation in document["translations"]:
            lines += ["", f"OPTIONAL TRANSLATION | {translation['image_id']} | {translation['language']}",
                      translation["text"]]
        lines += ["", "ENTITIES AND CORRESPONDENCE REFERENCES",
                  json.dumps({k: document[k] for k in ("entities", "references")}, ensure_ascii=False, indent=2)]
    else:
        lines += ["", "No complete transcription is available."]
        if record["result"] and record["result"].get("text"):
            lines += ["", "UNACCEPTED/PARTIAL RESPONSE (not verified)", record["result"]["text"]]
    if record["result"]:
        result = record["result"]
        calls = [attempts[aid] for aid in result["attempt_ids"] if aid in attempts]
        lines += ["", "TECHNICAL PROVENANCE — separate from historical text",
                  f"Revision: {result['revision_id']} | saved: {result['saved_at']}",
                  f"Returned model version: {result.get('returned_model') or 'unknown'}",
                  f"Request fingerprint: {result['fingerprint']}",
                  "Historical usage for this saved revision (export made zero requests): " +
                  json.dumps(aggregate(calls)),
                  "Historical attempt costs (null = unknown): " +
                  json.dumps([call.get("cost") for call in calls], ensure_ascii=False),
                  json.dumps(result["provenance"], ensure_ascii=False, indent=2)]
    return "\n".join(lines) + "\n"


def export_all(store, inventory, output, mapping=None):
    output = Path(output)
    # Refuse any destination beneath source scans, including path aliases.
    if output.resolve().is_relative_to(Path(inventory["input_root"]).resolve()):
        raise ValueError("Export directory must be outside the source input root")
    records = current_records(store, inventory)
    images = {i["image_id"]: i for i in inventory["images"]}
    attempts = {e["data"]["attempt_id"]: e["data"] for e in store.events() if e["kind"] == "attempt_end"}
    relationships = relationship_view(store, records)
    mapping = mapping or {"version": 1, "images": {}}
    if mapping.get("version") != 1 or not isinstance(mapping.get("images"), dict):
        raise ValueError("Invalid Drive mapping")
    for iid, entry in mapping["images"].items():
        if iid not in images or not isinstance(entry, dict) or not re.fullmatch(r"[A-Za-z0-9_-]{10,}", entry.get("file_id", "")):
            raise ValueError("Drive mapping needs known image IDs and explicit file_id values")
        if entry.get("original_sha256") != images[iid]["sha256"]:
            raise ValueError("Drive mapping hash differs from inventoried source; review the mapping")
    catalogue, image_rows, evidence_rows, entity_rows, texts, bundle = [], [], [], [], [], []
    named_paths = text_paths(records, images)
    for record in records:
        text = report(record, images, attempts)
        atomic_bytes(output / "letters" / (record["letter_id"] + ".txt"), text.encode("utf-8"))
        plain = reading(record, images)
        named_path = "readable/" + named_paths[record["letter_id"]].as_posix()
        atomic_bytes(output / named_path, plain.encode("utf-8"))
        if record["active"]:
            texts.append(plain)
        doc = record["document"]
        meta = doc["metadata"] if doc else {}
        catalogue.append(dict(letter_id=record["letter_id"], active=record["active"],
                         grouping=record["grouping"], execution=record["execution"],
                         metadata_review=record["metadata_review"], transcription_review=record["transcription_review"],
                         relationship_review=record["relationship_review"], page_count=len(record["image_ids"]),
                         filename_sender_hint=record["hints"].get("sender"),
                         filename_recipient_hint=record["hints"].get("recipient"),
                         filename_date_hint=record["hints"].get("date"), folder_hint=record["hints"].get("folder"),
                         sender=meta.get("sender", {}).get("value"), recipient=meta.get("recipient", {}).get("value"),
                         sender_search=meta.get("sender", {}).get("normalized"),
                         recipient_search=meta.get("recipient", {}).get("normalized"),
                         date_as_written=meta.get("date", {}).get("value"),
                         date_normalized=meta["date"]["normalized"] if usable_date(meta.get("date", {})) else None,
                         date_precision=meta.get("date", {}).get("precision"),
                         summary=doc["summary"] if doc else None,
                         review_reasons_json=json.dumps(record["review_reasons"], ensure_ascii=False),
                         report_path=named_path))
        scans = []
        for order, iid in enumerate(record["image_ids"], 1):
            image = images[iid]
            drive = mapping["images"].get(iid, {})
            image_rows.append(dict(letter_id=record["letter_id"], image_id=iid, order=order,
                                   path=image["path"], filename=image["filename"], folder=image["folder"],
                                   status=image["status"], original_sha256=image["sha256"],
                                   drive_file_id=drive.get("file_id")))
            scans.append(dict(image, order=order, drive_file_id=drive.get("file_id"),
                              mapping_status="mapped" if drive else "missing_mapping"))
        if doc:
            for field, value in meta.items():
                for evidence in value["evidence"]:
                    evidence_rows.append(dict(letter_id=record["letter_id"], field=field,
                                              certainty=value["certainty"], **evidence))
            for entity in doc["entities"]:
                entity_rows.append(dict(letter_id=record["letter_id"], kind=entity["kind"],
                                        value=entity["value"], normalized=entity.get("normalized"),
                                        role=entity["role"], certainty=entity["certainty"],
                                        evidence_json=json.dumps(entity["evidence"], ensure_ascii=False)))
        bundle.append(dict(letter_id=record["letter_id"], active=record["active"],
                           execution=record["execution"], grouping=record["grouping"],
                           metadata_review=record["metadata_review"], transcription_review=record["transcription_review"],
                           relationship_review=record["relationship_review"], review_reasons=record["review_reasons"],
                           hints=record["hints"], metadata=meta, summary=doc["summary"] if doc else "", pages=doc["pages"] if doc else [],
                           notes=doc["notes"] if doc else [], translations=doc["translations"] if doc else [], scans=scans,
                           partial_response=record["result"].get("text", "") if record["result"] and not doc else "",
                           provenance=record["result"]["provenance"] if record["result"] else None))
    catalogue_fields = ["letter_id", "active", "grouping", "execution", "metadata_review", "transcription_review",
                        "relationship_review", "page_count", "filename_sender_hint", "filename_recipient_hint",
                        "filename_date_hint", "folder_hint", "sender", "recipient", "sender_search", "recipient_search",
                        "date_as_written", "date_normalized", "date_precision", "summary", "review_reasons_json", "report_path"]
    write_csv(output / "catalogue.csv", catalogue_fields, catalogue)
    write_csv(output / "images.csv", ["letter_id", "image_id", "order", "path", "filename", "folder", "status",
                                    "original_sha256", "drive_file_id"], image_rows)
    write_csv(output / "evidence.csv", ["letter_id", "field", "certainty", "image_id", "quote"], evidence_rows)
    write_csv(output / "entities.csv", ["letter_id", "kind", "value", "normalized", "role", "certainty", "evidence_json"], entity_rows)
    write_csv(output / "relationships.csv", ["relationship_id", "from_letter", "to_letter", "relation", "status",
                                           "score", "evidence_json", "contradictions_json"],
              [dict(**{k: link.get(k) for k in ("relationship_id", "from_letter", "to_letter", "relation", "status", "score")},
                    evidence_json=json.dumps(link.get("evidence", []), ensure_ascii=False),
                    contradictions_json=json.dumps(link.get("contradictions", []), ensure_ascii=False))
               for link in relationships["links"]])
    write_csv(output / "unresolved.csv", ["reference_id", "from_letter", "status", "reference_json"],
              [dict(**{k: ref[k] for k in ("reference_id", "from_letter", "status")},
                    reference_json=json.dumps(ref["reference"], ensure_ascii=False)) for ref in relationships["unresolved"]])
    atomic_bytes(output / "combined.txt", "\n\n".join(texts).encode("utf-8"))
    atomic_json(output / "records.json", dict(schema_version=1, records=records, relationships=relationships,
                                            people=list(people(store).values())))
    atomic_json(output / "viewer.json", dict(schema_version=1, exported_at=now(), letters=bundle, **relationships))
    return len(records)
