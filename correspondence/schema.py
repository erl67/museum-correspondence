"""Response contract and conservative semantic checks; never rewrite source text."""
import calendar
from datetime import date
import json
import re

FIELDS = ("sender", "recipient", "date", "place_written", "addresses", "affiliations",
          "language", "document_type", "attributed_author", "physical_hand")
CERTAINTY = {"explicit", "inferred", "uncertain", "unknown"}
RELATIONS = {"reply_to", "mentions", "encloses", "related_subject"}


def unknown():
    return dict(value=None, normalized=None, certainty="unknown", evidence=[])


def empty_document(image_ids):
    metadata = {key: unknown() for key in FIELDS}
    metadata["date"]["precision"] = "unknown"
    return dict(schema_version=1,
                pages=[dict(image_id=i, status="text", text="", annotations=[]) for i in image_ids],
                metadata=metadata, summary="", entities=[], references=[], notes=[], translations=[])


def date_interval(value, precision):
    """No implicit Jan 1 values. Bounds are solely for chronology comparisons."""
    if not isinstance(value, str):
        return None
    patterns = {"year": r"\d{4}", "month": r"\d{4}-\d{2}", "day": r"\d{4}-\d{2}-\d{2}"}
    if precision not in patterns or not re.fullmatch(patterns[precision], value):
        return None
    try:
        parts = [int(n) for n in value.split("-")]
        year = parts[0]
        if precision == "year":
            return date(year, 1, 1), date(year, 12, 31)
        month = parts[1]
        if precision == "month":
            return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
        day = date(*parts)
        return day, day
    except (ValueError, OverflowError):
        return None


def usable_date(field):
    if field.get("certainty") not in {"explicit", "inferred"}:
        return None
    # Expansion of an ambiguous two-digit year is not accepted for local matching.
    if not isinstance(field.get("value"), str) or not re.search(r"\b\d{4}\b", field["value"]):
        return None
    if not isinstance(field.get("normalized"), str) or field["normalized"][:4] not in re.findall(r"\b\d{4}\b", field["value"]):
        return None
    return date_interval(field.get("normalized"), field.get("precision"))


def validate_document(document, image_ids, hints=None):
    """Structural errors permit one format retry; semantic uncertainty only flags review."""
    errors, reasons = [], []
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return ["Expected schema_version 1 object"], []
    pages = document.get("pages")
    if not isinstance(pages, list) or any(not isinstance(p, dict) for p in pages):
        return ["pages must be an ordered array"], []
    if [p.get("image_id") for p in pages] != list(image_ids):
        errors.append("Page coverage/order must exactly match supplied image IDs, without duplicates")
    texts = {}
    for page in pages:
        text, annotations = page.get("text"), page.get("annotations")
        if (not isinstance(page.get("image_id"), str) or not isinstance(text, str)
                or not isinstance(annotations, list)):
            errors.append("Each page needs text and annotations")
            continue
        if page.get("status") not in {"text", "blank", "unrelated", "illegible"}:
            errors.append("Invalid page status")
        if not text.strip():
            errors.append("Every page needs text or an explicit [blank]/[illegible] marker")
        annotation_text = []
        for annotation in annotations:
            if (not isinstance(annotation, dict) or not isinstance(annotation.get("text"), str)
                    or annotation.get("kind") not in {"later", "marginal", "stamp", "unknown"}):
                errors.append("Annotations need kind and text")
            else:
                annotation_text.append(annotation["text"])
        texts[page.get("image_id")] = text + "\n" + "\n".join(annotation_text)
        if page.get("status") in {"unrelated", "illegible"}:
            reasons.append(f"{page.get('image_id')}: {page['status']}")
        if re.search(r"\[(?:uncertain:|illegible)", texts[page.get("image_id")], re.I):
            reasons.append(f"{page.get('image_id')}: uncertain/illegible reading")

    def evidence(items, label):
        if not isinstance(items, list):
            errors.append(f"{label}: evidence must be an array")
            return
        for item in items:
            if (not isinstance(item, dict) or not isinstance(item.get("image_id"), str)
                    or item.get("image_id") not in texts
                    or not isinstance(item.get("quote"), str) or not item["quote"].strip()):
                errors.append(f"{label}: evidence needs a supplied page and quotation")
            elif item["quote"] not in texts[item["image_id"]]:
                reasons.append(f"{label}: evidence quotation not found verbatim in transcribed page")

    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata must be an object")
        metadata = {}
    for name in FIELDS:
        field = metadata.get(name)
        if not isinstance(field, dict):
            errors.append(f"Missing metadata field: {name}")
            continue
        if field.get("certainty") not in CERTAINTY:
            errors.append(f"{name}: invalid certainty")
        for key in ("value", "normalized"):
            if key not in field or (field[key] is not None and not isinstance(field[key], str)):
                errors.append(f"{name}.{key} must be string or null")
        evidence(field.get("evidence"), name)
        if (field.get("value") or field.get("normalized")) and not field.get("evidence"):
            reasons.append(f"{name}: value lacks evidence")
        if field.get("normalized") and not field.get("value"):
            reasons.append(f"{name}: normalized value lacks a source reading")
        if field.get("certainty") in {"uncertain", "unknown", "inferred"}:
            reasons.append(f"{name}: {field['certainty']}")
    dt = metadata.get("date", {})
    dt = dt if isinstance(dt, dict) else {}
    if dt.get("precision") not in {"day", "month", "year", "partial", "ambiguous", "unknown"}:
        errors.append("Date precision missing or invalid")
    if dt.get("normalized") and not usable_date(dt):
        reasons.append("date: normalization unsupported or ambiguous; excluded from chronology")
    if hints:
        for name in ("sender", "recipient", "date"):
            field = metadata.get(name, {})
            field = field if isinstance(field, dict) else {}
            hint = hints.get(name)
            value = field.get("normalized") or field.get("value")
            if isinstance(hint, str) and isinstance(value, str) and hint and value and hint.casefold() != value.casefold():
                reasons.append(f"filename/document conflict: {name}: {hint!r} versus {value!r}")
    for key in ("entities", "references", "notes", "translations"):
        if not isinstance(document.get(key), list):
            errors.append(f"{key} must be an array")
    if any(not isinstance(document.get(k), list) for k in ("entities", "references", "notes", "translations")):
        return errors, sorted(set(reasons))
    if not isinstance(document.get("summary"), str):
        errors.append("summary must be a separate string")
    for entity in document.get("entities", []) if isinstance(document.get("entities"), list) else []:
        if (not isinstance(entity, dict) or entity.get("kind") not in
                {"person", "organization", "place", "bird", "specimen", "catalogue", "subject"}
                or not isinstance(entity.get("value"), str)
                or "normalized" not in entity
                or (entity["normalized"] is not None and not isinstance(entity["normalized"], str))
                or entity.get("certainty") not in CERTAINTY
                or not isinstance(entity.get("role"), str)):
            errors.append("Invalid entity")
        else:
            evidence(entity.get("evidence"), "entity")
    for ref in document.get("references", []) if isinstance(document.get("references"), list) else []:
        if (not isinstance(ref, dict) or ref.get("kind") not in RELATIONS
                or not isinstance(ref.get("description"), str)
                or ref.get("certainty") not in CERTAINTY):
            errors.append("Invalid correspondence reference")
        else:
            evidence(ref.get("evidence"), "reference")
            if not ref.get("evidence"):
                reasons.append("reference lacks evidence")
            if ref.get("date_normalized") and not date_interval(ref["date_normalized"], ref.get("date_precision")):
                reasons.append("reference date is ambiguous or invalid")
    if any(not isinstance(n, str) for n in document.get("notes", [])):
        errors.append("notes must contain strings")
    for translation in document.get("translations", []):
        if (not isinstance(translation, dict) or translation.get("image_id") not in texts
                or not isinstance(translation.get("text"), str)
                or not isinstance(translation.get("language"), str)):
            errors.append("Translations need image_id, language and text")
    return errors, sorted(set(reasons))


def parse_response(text, image_ids, hints):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    try:
        document = json.loads(text, object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        return None, ["Malformed JSON; raw response preserved"], []
    try:
        errors, reasons = validate_document(document, image_ids, hints)
    except (ValueError, TypeError, KeyError, AttributeError):
        return document, ["Malformed nested field structure; raw response preserved"], []
    return document, errors, reasons
