"""Explicit, managed reader copies beside scans; never overwrite source/user files."""
from collections import defaultdict
from pathlib import Path, PurePosixPath
from .plaintext import reading, safe_name, text_paths
from .review import current_records
from .storage import atomic_bytes, digest


def source_destination(root, relative):
    part = PurePosixPath(relative)
    if part.is_absolute() or not part.parts or any(p in {"..", "."} or ":" in p or "\\" in p for p in part.parts):
        raise ValueError("Publication paths must stay within the input folder")
    path = root.joinpath(*part.parts)
    for item in (path, *path.parents):
        if item == root:
            break
        if item.is_symlink() or item.is_junction():
            raise ValueError(f"Publication cannot follow a link: {relative}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Publication path escapes the input folder")
    return path


def publication_state(store, inventory):
    state = store.latest("text_publication", {})
    if state and state["input_root"] != inventory["input_root"]:
        raise ValueError("Text publication belongs to another input root")
    return state


def publish_text(store, inventory, output):
    """Caller holds store lock. Persist ownership before writes for crash recovery."""
    root = Path(inventory["input_root"])
    if not root.is_dir():
        raise ValueError("Source folder is unavailable; local exports are saved, retry export when Drive is available")
    records = [r for r in current_records(store, inventory) if r["active"]]
    images = {i["image_id"]: i for i in inventory["images"]}
    paths = text_paths(records, images)
    files, folders = {}, defaultdict(list)
    combined = []

    def add(path, content):
        path = str(path)
        if path.casefold() in {p.casefold() for p in files}:
            raise ValueError(f"Conflicting publication names: {path}")
        files[path] = content.encode("utf-8") if isinstance(content, str) else content

    for record in records:
        path = paths[record["letter_id"]]
        text = reading(record, images)
        add(path, text)
        folders[path.parent].append(text)
        combined.append(text)
    for folder, texts in folders.items():
        if folder != PurePosixPath("."):
            add(folder / (safe_name(folder.name) + "_transcriptions.txt"), "\n\n".join(texts))
    add("Correspondence_transcriptions.txt", "\n\n".join(combined))
    # The existing viewer consumes structured data; people read the TXT files.
    add("Correspondence_viewer.json", (Path(output) / "viewer.json").read_bytes())
    state = publication_state(store, inventory)
    owned = state.get("files", {})
    for old in owned.keys() - files.keys():
        add(old, "SUPERSEDED GENERATED REPORT\nSee Correspondence_transcriptions.txt for current letters.\n")
    sources = {i["path"].casefold() for i in inventory["images"]}
    pending = {}
    # Preflight the complete set before changing any file.
    for relative, content in files.items():
        path = source_destination(root, relative)
        if relative.casefold() in sources or path.suffix.lower() not in {".txt", ".json"}:
            raise ValueError(f"Refusing to overwrite an inventoried source: {relative}")
        prior = owned.get(relative, [])
        new_hash = digest(content)
        if path.exists() and (not path.is_file() or digest(path.read_bytes()) not in prior):
            raise ValueError(f"Refusing to overwrite an unowned or edited file: {relative}")
        pending[relative] = sorted(set(prior + [new_hash]))
    store.append("text_publication", dict(input_root=inventory["input_root"], files=pending, status="pending"))
    for relative, content in files.items():
        path = source_destination(root, relative)
        # Recheck against edits made after preflight, before each replacement.
        if path.exists() and digest(path.read_bytes()) not in owned.get(relative, []):
            raise ValueError(f"File changed during publication: {relative}")
        atomic_bytes(path, content)
    store.append("text_publication", dict(input_root=inventory["input_root"],
                 files={p: [digest(b)] for p, b in files.items()}, status="complete"))
    return len(files)
