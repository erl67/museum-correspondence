"""Explicit, approved reference notes only. No model-output promotion."""
from copy import deepcopy
import re
from .storage import digest, encoded, read_json


def load_profile(path):
    if path is None:
        return None
    profile = read_json(path)
    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        raise ValueError("Invalid handwriting profile")
    if not all(isinstance(profile.get(k), str) and profile[k].strip()
               for k in ("profile_id", "version", "hand_description", "reviewer")):
        raise ValueError("Profile needs ID, immutable version, hand description and reviewer")
    if profile.get("review_status") != "approved":
        raise ValueError("Only approved handwriting profiles may be supplied")
    if not isinstance(profile.get("notes"), list) or not all(isinstance(n, str) for n in profile["notes"]):
        raise ValueError("Profile notes must be strings")
    examples = profile.get("examples")
    if not isinstance(examples, list) or len(examples) > 5:
        raise ValueError("At most five handwriting examples")
    for example in examples:
        if (not isinstance(example, dict) or example.get("review_status") != "verified"
                or not all(isinstance(example.get(k), str) and example[k].strip()
                           for k in ("image_id", "source_sha256", "transcription", "reviewer"))
                or not re.fullmatch(r"[0-9a-fA-F]{64}", example["source_sha256"])):
            raise ValueError("Examples need verified text, source image ID/hash and reviewer")
    if len(encoded(profile)) > 16_000:
        raise ValueError("Handwriting profile exceeds 16,000-byte context bound")
    return deepcopy(profile)


def register_profile(store, profile):
    if profile is None:
        return
    fingerprint = digest(encoded(profile))
    for event in store.events():
        if event["kind"] == "profile" and (event["data"]["profile_id"], event["data"]["version"]) == (
                profile["profile_id"], profile["version"]):
            if event["data"]["sha256"] != fingerprint:
                raise ValueError("Profile bytes changed without a new version; increment its version")
            return
    store.append("profile", dict(profile_id=profile["profile_id"], version=profile["version"],
                                 sha256=fingerprint, content=profile))
