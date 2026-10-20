"""All operational defaults; no credentials in configuration records."""
from dataclasses import asdict, dataclass
import math
from pathlib import Path
import re
from .storage import read_json


@dataclass(frozen=True)
class Config:
    model: str = "gemini-3.5-flash-lite"
    temperature: float = 1.0
    thinking_level: str = "high"
    max_output_tokens: int = 16384
    max_edge: int = 0
    max_request_bytes: int = 19_000_000
    max_pages: int = 40
    timeout: float = 180
    attempts: int = 3
    rpm: float = 2
    daily_limit: int = 20
    quota_timezone: str = "America/Los_Angeles"
    quota_file: str = "local/quota.json"
    max_retry_wait: float = 120
    rates: dict | None = None

    def __post_init__(self):
        if not re.fullmatch(r"gemini-[A-Za-z0-9._-]+", self.model):
            raise ValueError("Use an explicit Gemini model ID; no automatic provider fallback.")
        if self.thinking_level not in {"minimal", "low", "medium", "high"}:
            raise ValueError("Unsupported thinking level")
        if not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        for name in ("max_output_tokens", "max_request_bytes", "max_pages", "attempts", "daily_limit"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.max_edge) is not int or self.max_edge < 0:
            raise ValueError("max_edge must be a nonnegative integer")
        for name in ("timeout", "rpm", "max_retry_wait"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive and finite")
        if self.max_retry_wait < 60:
            raise ValueError("max_retry_wait must be at least 60 seconds")
        if self.rates is not None:
            if not all(self.rates.get(k) for k in ("currency", "as_of", "source", "model")):
                raise ValueError("Rates need currency, as_of, source and model")
            for key in ("input", "cached", "output"):
                value = self.rates.get(key)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError("Rates must be nonnegative prices per million tokens")

    def generation(self):
        return dict(temperature=self.temperature, max_output_tokens=self.max_output_tokens,
                    thinking_config={"thinking_level": self.thinking_level.upper()},
                    response_mime_type="application/json",
                    automatic_function_calling={"disable": True})

    def public(self):
        return asdict(self)


def load_config(path=None):
    if path and not Path(path).is_file():
        raise ValueError(f"Configuration not found: {path}")
    return Config(**(read_json(path, {}) if path else {}))
