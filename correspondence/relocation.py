"""Explicit byte-verified source path reconciliation; never rename a scan."""
from copy import deepcopy
from pathlib import Path
from .naming import filename_hints, split_page
from .publication import source_destination
from .storage import digest


def reconcile_paths(inventory, mapping):
    if not isinstance(mapping, dict) or mapping.get("version") != 1 or not mapping.get("source"):
        raise ValueError("Path reconciliation needs version 1, a source/reason and explicit paths")
    paths = mapping.get("paths")
    if not isinstance(paths, dict) or not paths or not all(isinstance(k, str) and isinstance(v, str) for k, v in paths.items()):
        raise ValueError("Path reconciliation needs an old-path to new-path object")
    updated = deepcopy(inventory)
    root = Path(inventory["input_root"])
    images = {i["path"]: i for i in updated["images"]}
    if set(paths) - images.keys() or len({p.casefold() for p in paths.values()}) != len(paths):
        raise ValueError("Unknown old path or duplicate new path")
    for old, new in paths.items():
        old_path = source_destination(root, old)
        new_path = source_destination(root, new)
        if old == new or old_path.exists() or new in images:
            raise ValueError(f"Old path still exists or new path already inventoried: {old}")
        if new_path.suffix.lower() not in {".jpg", ".jpeg"} or not new_path.is_file():
            raise ValueError(f"New path must be an existing JPEG: {new}")
        image = images[old]
        if not image["sha256"] or digest(new_path.read_bytes()) != image["sha256"]:
            raise ValueError(f"Renamed scan bytes differ from saved evidence: {new}")
        image.setdefault("previous_paths", []).append(old)
        image.update(path=new, filename=new_path.name,
                     folder=Path(new).parent.as_posix(), status="ready")
    by_id = {i["image_id"]: i for i in updated["images"]}
    for letter in updated["letters"]:
        if not letter["active"]:
            continue
        pages = [by_id[i] for i in letter["image_ids"]]
        first = pages[0]
        base, _ = split_page(Path(first["filename"]).stem)
        if not letter.get("override"):
            letter["group_key"] = first["folder"] + "/" + base
        letter["hints"] = filename_hints(base)
        letter["hints"].update(folder=first["folder"], filenames=[p["filename"] for p in pages])
        if letter.get("override"):
            letter["override"]["paths"] = [paths.get(p, p) for p in letter["override"]["paths"]]
    for group in updated["overrides"]["groups"]:
        group["paths"] = [paths.get(p, p) for p in group["paths"]]
    updated["path_reconciliation"] = deepcopy(mapping)
    return updated
