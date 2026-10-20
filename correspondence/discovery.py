"""Conservative folder-scoped grouping. Filenames are hints, never authority."""
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import re
import uuid
from PIL import Image
from .storage import digest

LABEL = re.compile(r"^(.*?)[ ]*\(([A-Za-z]+|\d+)\)$")
HINT = re.compile(r"^(?P<sender>[^-]+)-(?P<recipient>[^-]+)-(?P<date>\d{4}(?:-\d{1,2}){0,2})$")


def stable(prefix, collection, key):
    return prefix + uuid.uuid5(uuid.UUID(collection), key).hex


def inspect_file(path, root, collection, previous):
    rel = path.relative_to(root).as_posix()
    old = previous.get(rel, {})
    row = dict(image_id=old.get("image_id", stable("img_", collection, rel)),
               path=rel, filename=path.name, folder=path.parent.relative_to(root).as_posix(),
               status="ready", sha256=None, size=None)
    if path.is_symlink() or path.is_junction():
        row["status"] = "symlink"
        return row
    try:
        raw = path.read_bytes()
        row.update(sha256=digest(raw), size=len(raw))
        if path.suffix.lower() not in {".jpg", ".jpeg"}:
            row["status"] = "unsupported"
        else:
            with Image.open(path) as image:
                if image.format != "JPEG":
                    raise ValueError("Extension says JPEG but content is not JPEG")
                image.load()
                row["dimensions"] = list(image.size)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        row.update(status="unreadable", error=str(exc))
    return row


def discover(root, previous=None, overrides=None):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"Input root is not an accessible directory: {root}")
    previous = previous or {}
    if previous and previous["input_root"] != str(root):
        raise ValueError("This store belongs to another input root; use a separate --store.")
    collection = previous.get("collection_id", str(uuid.uuid5(uuid.NAMESPACE_URL, str(root))))
    old_images = {i["path"]: i for i in previous.get("images", [])}
    images = []
    # walk raises on inaccessible directories instead of silently dropping their contents.
    def walk_error(error):
        raise error
    for folder, dirs, files in root.walk(on_error=walk_error, follow_symlinks=False):
        for directory in list(dirs):
            if (folder / directory).is_symlink() or (folder / directory).is_junction():
                files.append(directory)
                dirs.remove(directory)
        for name in sorted(files):
            images.append(inspect_file(folder / name, root, collection, old_images))
    present = {i["path"] for i in images}
    images += [dict(i, status="missing") for p, i in old_images.items() if p not in present]
    images.sort(key=lambda i: i["path"])
    by_path = {i["path"]: i for i in images}
    names = Counter(i["filename"].casefold() for i in images if i["status"] != "missing")
    old_letters = {l["letter_id"]: l for l in previous.get("letters", [])}
    old_keys = {l["group_key"]: l["letter_id"] for l in old_letters.values()}
    groups, claimed = [], set()
    overrides = overrides or {"version": 1, "groups": []}
    if overrides.get("version") != 1:
        raise ValueError("Unsupported grouping override version")
    keys, ids = set(), set()
    for group in overrides["groups"]:
        key = "override:" + group["key"]
        paths = group["paths"]
        lid = group.get("letter_id") or old_keys.get(key) or stable("ltr_", collection, key)
        if key in keys or lid in ids or not paths or len(paths) != len(set(paths)):
            raise ValueError("Duplicate override key, letter ID, page, or empty override")
        if group.get("letter_id") and lid not in old_letters:
            raise ValueError("Override letter_id must already exist; omit it for a new record")
        if any(p not in by_path or p in claimed for p in paths):
            raise ValueError("Override paths must exist in inventory and belong to only one group")
        if not group.get("source"):
            raise ValueError("Grouping overrides require a source/reason")
        claimed.update(paths)
        keys.add(key)
        ids.add(lid)
        groups.append((key, lid, paths, [], "reviewed", deepcopy(group)))
    automatic = defaultdict(list)
    for row in images:
        if row["path"] in claimed:
            continue
        match = LABEL.match(Path(row["filename"]).stem)
        base = match[1] if match else Path(row["filename"]).stem
        label = match[2].upper() if match else None
        # Folder is part of grouping identity. No punctuation/name normalization merges.
        key = row["folder"] + "/" + base
        automatic[key].append((label, row["path"]))
    for key, pages in sorted(automatic.items()):
        labels = [label for label, _ in pages]
        reasons = []
        if len(labels) > 1 and (None in labels or len(set(labels)) != len(labels)):
            reasons.append("duplicate page label or unlabelled/page-labelled collision")
        if labels != [None]:
            if any(label is None or not re.fullmatch(r"[A-Z]|\d+", label) for label in labels):
                reasons.append("ambiguous page labels")
            elif all(label.isdigit() for label in labels):
                numbers = [int(label) for label in labels]
                if len(set(numbers)) != len(numbers):
                    reasons.append("duplicate numeric page label")
                if sorted(set(numbers)) != list(range(1, max(numbers) + 1)):
                    reasons.append("missing initial or intermediate page")
            elif all(len(label) == 1 and label.isalpha() for label in labels):
                numbers = [ord(label) - 64 for label in labels]
                if sorted(set(numbers)) != list(range(1, max(numbers) + 1)):
                    reasons.append("missing initial or intermediate page")
            else:
                reasons.append("mixed page label systems")
        def order(item):
            label, path = item
            return (int(label) if label and label.isdigit() else ord(label) - 64
                    if label and len(label) == 1 else 999, path)
        paths = [p for _, p in sorted(pages, key=order)]
        lid = old_keys.get(key, stable("ltr_", collection, key))
        if lid in ids:  # An override retained the old ID but left pages behind.
            lid = stable("ltr_", collection, "remainder:" + key)
            reasons.append("pages left outside explicit regrouping")
        groups.append((key, lid, paths, reasons, "provisional", None))
    letters = []
    hint_groups = defaultdict(list)
    for key, lid, paths, reasons, grouping, override in groups:
        for p in paths:
            row = by_path[p]
            if row["status"] != "ready":
                reasons.append(f"{row['status']}: {p}")
            if names[row["filename"].casefold()] > 1:
                reasons.append(f"identical filename in different locations: {row['filename']}")
        stem = Path(paths[0]).stem
        base = LABEL.sub(r"\1", stem)
        match = HINT.fullmatch(base)
        hints = dict(match.groupdict()) if match else {}
        hints.update(folder=by_path[paths[0]]["folder"], filenames=[by_path[p]["filename"] for p in paths])
        if not match and grouping != "reviewed":
            reasons.append("filename cannot confidently identify a letter; review grouping")
        old = old_letters.get(lid)
        membership = [by_path[p]["image_id"] for p in paths]
        membership_warning = "page membership/order changed; recheck grouping and earlier reviews"
        if old and (old["image_ids"] != membership or
                    (grouping != "reviewed" and membership_warning in old["review_reasons"])):
            reasons.append(membership_warning)
        letters.append(dict(letter_id=lid, group_key=key, image_ids=membership, hints=hints,
                            grouping=grouping if not reasons or grouping == "reviewed" else "needs_review",
                            review_reasons=sorted(set(reasons)), override=override, active=True))
        if match:
            hint_groups[tuple(match.groupdict().values())].append(letters[-1])
    for same in hint_groups.values():
        if len(same) > 1:
            for letter in same:
                letter["review_reasons"].append("same filename hints in distinct groups; not merged")
                if letter["grouping"] != "reviewed":
                    letter["grouping"] = "needs_review"
    active_ids = {l["letter_id"] for l in letters}
    letters += [dict(l, active=False, grouping="retired") for lid, l in old_letters.items() if lid not in active_ids]
    return dict(schema_version=1, collection_id=collection, input_root=str(root), images=images,
                letters=letters, overrides=deepcopy(overrides))
