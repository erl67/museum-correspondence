from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from correspondence.config import Config
from correspondence.discovery import discover
from correspondence.images import prepare_request
from correspondence.schema import empty_document
from correspondence.storage import Store, encoded

ROOT = Path(__file__).resolve().parents[1]


def jpeg(path, color="white"):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 48), color).save(path, "JPEG")


def document(ids):
    doc = empty_document(ids)
    for page in doc["pages"]:
        page["text"] = "SYNTHETIC SOFTWARE FIXTURE. Dear B. May 2, 1899. Yours, A."
    return doc


def response(doc, finish="STOP", usage=True):
    return dict(candidates=[dict(finish_reason=finish, content={"parts": [{"text": encoded(doc).decode()}]})],
                model_version="synthetic-test-model",
                usage_metadata=dict(prompt_token_count=100, candidates_token_count=50, thoughts_token_count=10,
                                    cached_content_token_count=20, total_token_count=160) if usage else None)


class FakeTransport:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []
        self.closed = False

    def send(self, request, prompt):
        self.calls.append(prompt)
        item = self.answers.pop(0)
        if isinstance(item, BaseException):
            raise item
        return deepcopy(item)

    def clean_error(self, exc):
        return str(exc)

    def close(self):
        self.closed = True


class Clock:
    def __init__(self):
        self.value = 1792440000.0
        self.waits = []

    def time(self):
        return self.value

    def sleep(self, duration):
        self.waits.append(duration)
        self.value += duration


class ServiceError(Exception):
    def __init__(self, code, message="synthetic service failure", payload=None, headers=None):
        super().__init__(message)
        from types import SimpleNamespace
        self.code, self.response_json = code, payload
        self.response = SimpleNamespace(headers=headers or {})


class Workspace(unittest.TestCase):
    def setUp(self):
        tmp = ROOT / "local" / "test-tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=tmp)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.store = Store(self.root / "store")
        self.config = replace(Config(), quota_file=str(self.root / "quota.json"))

    def setup_letter(self, names=("A-B-1899-05-02(A).jpg", "A-B-1899-05-02(B).jpg"), prepare=True):
        for name in names:
            jpeg(self.inputs / name)
        self.inventory = discover(self.inputs)
        self.store.append("inventory", self.inventory)
        self.letter = self.inventory["letters"][0]
        self.request = prepare_request(self.inventory, self.letter, self.config) if prepare else None
        self.doc = document(self.letter["image_ids"])
        return self.letter
