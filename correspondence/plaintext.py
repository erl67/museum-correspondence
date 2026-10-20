"""Staff-facing text, kept separate from archival JSON and diagnostic reports."""
from collections import Counter
from pathlib import PurePosixPath
import re


def safe_name(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip().rstrip(". ")
    if not value or value in {".", ".."}:
        value = "Letter"
    if re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", value):
        value = "_" + value
    return value[:160].rstrip(". ")


def title(record, images):
    # A display name is a filename hint, never a corrected historical attribution.
    name = (record.get("override") or {}).get("title")
    if not name:
        name = PurePosixPath(images[record["image_ids"][0]]["path"]).stem
        name = re.sub(r"(?:\s*\((?:[A-Za-z]+|\d+)\))+$", "", name)
    return safe_name(name)


def text_paths(records, images):
    """Keep folder context and disambiguate collisions without changing archival IDs."""
    paths = {}
    for record in records:
        folder = PurePosixPath(images[record["image_ids"][0]]["path"]).parent
        paths[record["letter_id"]] = folder / (title(record, images) + ".txt")
    counts = Counter(str(p).casefold() for p in paths.values())
    used = set()
    for lid, path in paths.items():
        if counts[str(path).casefold()] > 1:
            path = path.with_name(path.stem + "--" + lid + ".txt")
        if str(path).casefold() in used:
            raise ValueError("Conflicting text report names; review grouping titles")
        used.add(str(path).casefold())
        paths[lid] = path
    return paths


def reading(record, images):
    name = title(record, images)
    lines = ["=" * 72, name, "=" * 72,
             "STATUS: " + (record["execution"] if record["active"] else "retired"),
             "HUMAN TRANSCRIPTION REVIEW: " + record["transcription_review"],
             "FILES: " + "; ".join(images[i]["path"] for i in record["image_ids"]), ""]
    doc = record["document"]
    if doc:
        if record["execution"] == "stale" or not record["active"]:
            lines += ["EARLIER READING: source membership/content has changed or this record is retired.", ""]
        lines += ["TRANSCRIPTION", ""]
        for number, page in enumerate(doc["pages"], 1):
            scan = images.get(page["image_id"], {})
            lines += [f"--- PAGE {number}: {scan.get('path', page['image_id'])} [{page['status']}] ---",
                      page["text"] or "[No text recorded for this page.]", ""]
            for annotation in page["annotations"]:
                lines += [f"ANNOTATION ({annotation['kind']}): {annotation['text']}", ""]
        if doc["notes"]:
            lines += ["TRANSCRIPTION NOTES"] + doc["notes"] + [""]
        for translation in doc["translations"]:
            lines += [f"OPTIONAL TRANSLATION ({translation['language']}; {images.get(translation['image_id'], {}).get('path', translation['image_id'])})",
                      translation["text"], ""]
        lines += ["CATALOGUE DETAILS (separate from the letter)"]
        for field in ("sender", "recipient", "date", "place_written"):
            detail = doc["metadata"].get(field, {})
            lines.append(f"{field.replace('_', ' ').title()}: {detail.get('value') or 'Unknown'} ({detail.get('certainty', 'unknown')})")
        if doc["summary"]:
            lines += ["", "INTERPRETIVE SUMMARY", doc["summary"]]
    else:
        lines += ["No complete transcription is available for this letter."]
        if record.get("result") and record["result"].get("text"):
            lines += ["A failed/partial response is preserved in the local diagnostic report and history."]
    if record["review_reasons"]:
        lines += ["", "REVIEW NOTES"] + ["- " + r for r in record["review_reasons"]]
    lines += ["", "Record: " + record["letter_id"],
              "A complete AI response is not a human-verified transcription."]
    return "\n".join(lines) + "\n"
