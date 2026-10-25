"""Image preparation adapted from museum-transcription, build 2026-10-19.1."""
from io import BytesIO
from copy import deepcopy
from pathlib import Path
from PIL import Image, ImageOps
from . import SCHEMA_VERSION, __version__
from .prompt import PROMPT_VERSION, build_prompt
from .storage import digest, encoded


def prepare_image(raw, max_edge=0):
    with Image.open(BytesIO(raw)) as source:
        if source.format != "JPEG":
            raise ValueError("Only JPEG content is supported")
        source.load()
        orientation = source.getexif().get(274, 1)
        resize = bool(max_edge and max(source.size) > max_edge)
        operations = []
        if orientation not in (None, 1):
            operations.append(f"EXIF orientation {orientation} applied")
        if resize:
            operations.append(f"longest edge <= {max_edge}; Lanczos")
        if source.mode not in {"RGB", "L"}:
            operations.append(f"{source.mode} to RGB")
        if not operations:
            return raw, ["original JPEG bytes"]
        image = ImageOps.exif_transpose(source).convert("RGB")
        if resize:
            image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, "JPEG", quality=95, subsampling=0)
        return output.getvalue(), operations + ["JPEG quality 95; subsampling 0"]


def prepare_request(inventory, letter, config, profile=None, *, correspondents=None):
    if not letter["active"] or letter["grouping"] not in {"provisional", "reviewed"}:
        raise ValueError("Grouping needs a reviewed override before transcription")
    images = {i["image_id"]: i for i in inventory["images"]}
    if len(letter["image_ids"]) > config.max_pages:
        raise ValueError("Letter exceeds max_pages; no pages were omitted")
    correspondents = deepcopy(correspondents or [])
    prompt = build_prompt(letter, profile, correspondents)
    manifest, data = [], []
    size = len(encoded(config.generation())) + len(prompt.encode("utf-8")) * 6 + 8192
    for iid in letter["image_ids"]:
        item = images[iid]
        if item["status"] != "ready":
            raise ValueError(f"Image unavailable ({item['status']}): {item['path']}")
        path = Path(inventory["input_root"]) / item["path"]
        raw = path.read_bytes()
        if digest(raw) != item["sha256"]:
            raise ValueError(f"Scan changed since inventory: {item['path']}; rerun inventory")
        submitted, operations = prepare_image(raw, config.max_edge)
        label = f"PAGE image_id={iid}; original relative path={item['path']}"
        manifest.append(dict(image_id=iid, path=item["path"], label=label,
                             original_sha256=item["sha256"], submitted_sha256=digest(submitted),
                             submitted_bytes=len(submitted), transformations=operations))
        data.append(submitted)
        size += 4 * ((len(submitted) + 2) // 3) + len(label.encode("utf-8")) * 6 + 1024
    if size > config.max_request_bytes:
        raise ValueError(f"Whole letter needs approximately {size:,} request bytes; local limit "
                         f"{config.max_request_bytes:,}. No pages omitted. Consider explicit max_edge.")
    provenance = dict(schema_version=SCHEMA_VERSION, application_version=__version__,
                      provider="gemini", model=config.model, generation=config.generation(),
                      prompt_version=PROMPT_VERSION, prompt=prompt, prompt_sha256=digest(prompt.encode()),
                      hints=deepcopy(letter["hints"]), handwriting_profile=deepcopy(profile),
                      known_correspondents=correspondents, images=manifest,
                      max_edge=config.max_edge)
    return dict(fingerprint=digest(encoded(provenance)), provenance=provenance,
                image_data=data, estimated_bytes=size)
