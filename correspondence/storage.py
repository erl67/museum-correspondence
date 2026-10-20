"""Durable storage primitives. No collection or provider assumptions."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identity(prefix):
    return prefix + uuid.uuid4().hex


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_json(path, value):
    atomic_bytes(path, encoded(value) + b"\n")


@contextmanager
def lock(path):
    """OS lock releases after process death; never remove a shared lock inode."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f"Another process holds {path}") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


class Store:
    """One append-only journal is authoritative; exports are disposable."""
    def __init__(self, root):
        self.root = Path(root)
        self.journal = self.root / "journal.jsonl"

    def events(self):
        if not self.journal.exists():
            return []
        events = []
        for number, line in enumerate(self.journal.read_bytes().splitlines(), 1):
            try:
                event = json.loads(line)
                if event["schema_version"] != 1 or not isinstance(event["data"], dict):
                    raise ValueError("Unsupported event")
                events.append(event)
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"Damaged journal line {number}; stop and restore from backup. "
                                 "No automatic deletion or paid retry.") from exc
        return events

    def append(self, kind, data):
        # Validate the existing tail before any append. A truncated tail fails closed.
        self.events()
        self.root.mkdir(parents=True, exist_ok=True)
        event = dict(schema_version=1, event_id=identity("evt_"), at=now(), kind=kind, data=data)
        with self.journal.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell():
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    handle.write(b"\n")
            handle.write(encoded(event) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def latest(self, kind, default=None):
        return next((e["data"] for e in reversed(self.events()) if e["kind"] == kind), default)

    def blob(self, data, suffix):
        key = digest(data)
        path = self.root / "blobs" / (key + suffix)
        if path.exists():
            if digest(path.read_bytes()) != key:
                raise ValueError(f"Damaged stored blob: {path}")
        else:
            atomic_bytes(path, data)
        return path.relative_to(self.root).as_posix()

    def results(self):
        return [e["data"] for e in self.events() if e["kind"] == "result"]

    def reusable(self, letter_id, fingerprint, clock=None):
        clock = clock or datetime.now(timezone.utc)
        # A later failed attempt for this fingerprint supersedes an earlier success.
        result = next((r for r in reversed(self.results()) if r["letter_id"] == letter_id
                       and r["fingerprint"] == fingerprint), None)
        if result and result["execution"] == "complete":
            age = (clock - datetime.fromisoformat(result["saved_at"])).total_seconds()
            if 0 <= age <= 48 * 3600:
                return result
        return None
