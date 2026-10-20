"""Thin Gemini transport. No retry loops, catalogue rules, or secret persistence."""
import os
from pathlib import Path


def api_key(env_file=None):
    if env_file:
        path = Path(env_file)
        if not path.is_file():
            raise ValueError(f"Credential file not found: {path}")
        values = {}
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if not sep or key.strip() not in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}:
                raise ValueError("Credential file accepts only GEMINI_API_KEY or GOOGLE_API_KEY assignments")
            values[key.strip()] = value.strip().strip("'\"")
        secret = values.get("GEMINI_API_KEY") or values.get("GOOGLE_API_KEY")
    else:
        secret = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not secret:
        raise ValueError("No Gemini key; set GEMINI_API_KEY or pass --env-file .env")
    return secret


class Gemini:
    def __init__(self, config, secret, http_client=None):
        from google import genai
        self.config, self.secret = config, secret
        options = dict(base_url="https://generativelanguage.googleapis.com/", api_version="v1beta",
                       timeout=int(config.timeout * 1000), retry_options={"attempts": 1})
        if http_client is not None:
            options["httpx_client"] = http_client
        self.client = genai.Client(vertexai=False, api_key=secret, http_options=options)

    def send(self, request, prompt):
        parts = [{"text": prompt}]
        for page, data in zip(request["provenance"]["images"], request["image_data"], strict=True):
            parts.extend([{"text": page["label"]},
                          {"inline_data": {"mime_type": "image/jpeg", "data": data}}])
        response = self.client.models.generate_content(
            model=self.config.model, contents=[{"role": "user", "parts": parts}],
            config=self.config.generation())
        return response.model_dump(mode="json")

    def clean_error(self, exc):
        return str(exc).replace(self.secret, "[REDACTED]")

    def close(self):
        self.client.close()


def completion(response):
    candidates = response.get("candidates") or []
    candidate = candidates[0] if candidates else {}
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(p.get("text") or "" for p in parts if not p.get("thought"))
    finish = candidate.get("finish_reason")
    block = (response.get("prompt_feedback") or {}).get("block_reason")
    if block and block != "BLOCK_REASON_UNSPECIFIED":
        return text, [f"Provider blocked output: {block}"], False
    if finish and finish != "STOP":
        return text, [f"Provider incomplete/refused output: {finish}"], False
    if len(candidates) != 1 or not finish or not text.strip():
        return text, ["Empty response, absent completion reason, or unexpected candidate count"], True
    if any(not p.get("thought") and not p.get("text") for p in parts):
        return text, ["Unexpected non-text output"], False
    return text, [], False
