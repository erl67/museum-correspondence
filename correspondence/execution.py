"""One explicit attempt loop: persistence, quota, pacing, transport, validation."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
from pathlib import Path
import time
from zoneinfo import ZoneInfo
from . import __version__
from .prompt import correction
from .provider import completion
from .schema import parse_response
from .storage import atomic_json, digest, encoded, identity, lock, now, read_json
from .usage import estimate, read_usage


class QuotaReached(RuntimeError):
    pass


class Quota:
    """Separate conservative allocation; never imports or resets the old app's state."""
    def __init__(self, config, clock=time.time, sleep=time.sleep):
        self.config, self.clock, self.sleep = config, clock, sleep
        self.path = Path(config.quota_file)

    def update(self, exhaust=False):
        while True:
            wait = 0
            with lock(self.path.with_suffix(self.path.suffix + ".lock")):
                state = read_json(self.path, {"schema": "correspondence-quota-1", "models": {}})
                if state.get("schema") != "correspondence-quota-1" or not isinstance(state.get("models"), dict):
                    raise ValueError("Unknown/damaged quota state; do not reset or point at egg-slip counters")
                for entry in state["models"].values():
                    if (not isinstance(entry, dict) or type(entry.get("attempts")) is not int
                            or entry["attempts"] < 0 or type(entry.get("exhausted")) is not bool
                            or not isinstance(entry.get("next_start"), (int, float))
                            or not math.isfinite(entry["next_start"])):
                        raise ValueError("Damaged quota state; restore counters before requests")
                    datetime.strptime(entry["day"], "%Y-%m-%d")
                day = datetime.fromtimestamp(self.clock(), ZoneInfo(self.config.quota_timezone)).date().isoformat()
                key = "gemini/" + self.config.model
                entry = state["models"].get(key, dict(day=day, attempts=0, exhausted=False, next_start=0))
                if entry["day"] != day:
                    entry = dict(day=day, attempts=0, exhausted=False, next_start=entry["next_start"])
                if exhaust:
                    entry["exhausted"] = True
                else:
                    if entry["exhausted"] or entry["attempts"] >= self.config.daily_limit:
                        raise QuotaReached("Daily local allocation exhausted; provider quota may also include other apps")
                    wait = max(0, entry["next_start"] - self.clock())
                    if not wait:
                        entry["attempts"] += 1
                        entry["next_start"] = self.clock() + 60 / self.config.rpm + 0.1
                if not wait:
                    state["models"][key] = entry
                    atomic_json(self.path, state)
                    return entry["attempts"]
            self.sleep(min(wait, 60))


def error_policy(exc, current_time=None):
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = None
    payload = getattr(exc, "response_json", None) or {}
    description = (json.dumps(payload, default=str) + str(exc)).lower()
    if code in {400, 401, 402, 403, 404} or isinstance(exc, (TypeError, ValueError)):
        return "configuration", 0
    if code == 429 and any(s in description for s in ("perday", "per_day", "per day", "daily", "requests/day")):
        return "daily", 0
    if code == 429 and any(s in description for s in ("billing", "insufficient_quota", "credit")):
        return "billing", 0
    import httpx
    retry = code in {408, 429, 500, 502, 503, 504} or isinstance(exc, (ConnectionError, TimeoutError, httpx.TransportError))
    if not retry:
        return "failed", 0
    delays = [60.0 if code == 429 else 0.0]
    headers = getattr(getattr(exc, "response", None), "headers", {}) or {}
    after = headers.get("retry-after") or headers.get("Retry-After")
    if after:
        try:
            delays.append(float(after))
        except ValueError:
            try:
                delays.append(parsedate_to_datetime(after).timestamp() - (current_time or time.time()))
            except (ValueError, TypeError):
                pass
    body = payload.get("error", payload) if isinstance(payload, dict) else {}
    for detail in body.get("details", []) if isinstance(body, dict) else []:
        try:
            delay = detail.get("retryDelay", 0)
            delays.append(float(delay.get("seconds", 0)) + float(delay.get("nanos", 0)) / 1e9
                          if isinstance(delay, dict) else float(str(delay).removesuffix("s")))
        except (TypeError, ValueError):
            pass
    return "retry", max(d for d in delays if math.isfinite(d))


def interpret(response, letter):
    text, errors, retryable = completion(response)
    document, reasons = None, []
    if not errors:
        document, errors, reasons = parse_response(text, letter["image_ids"], letter["hints"])
        retryable = bool(errors)
    return dict(text=text, document=document, errors=errors, review_reasons=reasons,
                retryable=retryable, execution="failed" if errors else "complete",
                returned_model=response.get("model_version"))


def checkpoint_result(store, letter, request, outcome, attempt_ids, run_id, saved_at=None):
    result = dict(outcome, revision_id=identity("rev_"), letter_id=letter["letter_id"],
                  fingerprint=request["fingerprint"], provenance=request["provenance"],
                  attempt_ids=list(attempt_ids), saved_at=saved_at or now(), run_id=run_id,
                  application_version=__version__)
    store.append("result", result)  # Paid work is durable BEFORE any derived export.
    return result


def transcribe(store, letter, request, config, transport_factory, *, fresh=False,
               retry_interrupted=False, run_id=None, sleep=time.sleep, quota=None):
    run_id = run_id or identity("run_")
    events = store.events()
    starts = [e["data"] for e in events if e["kind"] == "attempt_start"
              and e["data"]["letter_id"] == letter["letter_id"]]
    ended = {e["data"]["attempt_id"]: e["data"] for e in events if e["kind"] == "attempt_end"}
    finished = {aid for r in store.results() for aid in r["attempt_ids"]}
    pending = [s for s in starts if s["attempt_id"] not in finished]
    if pending:
        latest = pending[-1]
        end = ended.get(latest["attempt_id"])
        if end and end.get("response") and latest["fingerprint"] == request["fingerprint"]:
            response = read_json(store.root / end["response"])
            outcome = interpret(response, letter)
            recovered = checkpoint_result(store, letter, request, outcome,
                                          [s["attempt_id"] for s in pending], latest["run_id"], end["ended_at"])
            if not fresh and store.reusable(letter["letter_id"], request["fingerprint"]):
                return recovered, True
        elif not retry_interrupted:
            raise ValueError("Interrupted attempt has unknown outcome; inspect journal/raw files and "
                             "use --retry-interrupted only if accepting another possible charge")
    latest_result = next((r for r in reversed(store.results()) if r["letter_id"] == letter["letter_id"]), None)
    if latest_result and latest_result["execution"] == "interrupted" and not retry_interrupted:
        raise ValueError("Interrupted request: inspect saved work, then explicitly use --retry-interrupted")
    cached = None if fresh else store.reusable(letter["letter_id"], request["fingerprint"])
    if cached:
        store.select(cached, run_id)
        return cached, True
    # Freeze submitted bytes and the complete request before looking up credentials.
    for page, data in zip(request["provenance"]["images"], request["image_data"], strict=True):
        store.blob(data, ".jpg")
    request_ref = store.blob(encoded(request["provenance"]), ".json")
    quota = quota or Quota(config, sleep=sleep)
    transport = transport_factory()
    ids, corrections = [], 0
    prompt = request["provenance"]["prompt"]
    outcome = dict(execution="failed", text="", document=None, errors=[], review_reasons=[])
    try:
        for index in range(config.attempts):
            corrected_size = request["estimated_bytes"] + max(
                0, len(prompt.encode("utf-8")) - len(request["provenance"]["prompt"].encode("utf-8"))) * 6
            if corrected_size > config.max_request_bytes:
                outcome.update(execution="failed", errors=["Format correction exceeds whole-request size limit"])
                break
            try:
                quota.update()
            except QuotaReached as exc:
                outcome.update(execution="paused", errors=[str(exc)], stop_batch=True)
                break
            aid = identity("att_")
            ids.append(aid)
            store.append("attempt_start", dict(attempt_id=aid, letter_id=letter["letter_id"],
                         fingerprint=request["fingerprint"], request=request_ref, prompt=prompt,
                         prompt_sha256=digest(prompt.encode()), started_at=now(), run_id=run_id,
                         settings=config.public()))
            response, failure, delay, kind, error_ref = None, None, 0, None, None
            try:
                response = transport.send(request, prompt)
            except (KeyboardInterrupt, SystemExit):
                store.append("attempt_end", dict(attempt_id=aid, ended_at=now(), usage=read_usage(None),
                             cost=None, response=None, error="Interrupted; service outcome unknown"))
                outcome.update(execution="interrupted", errors=["Interrupted; service outcome unknown"])
                checkpoint_result(store, letter, request, outcome, ids, run_id)
                raise
            except Exception as exc:
                failure = transport.clean_error(exc)
                kind, delay = error_policy(exc)
                body = getattr(exc, "response_json", None)
                if body is not None:
                    cleaned = transport.clean_error(ValueError(json.dumps(body, ensure_ascii=False, default=str)))
                    error_ref = store.blob(cleaned.encode("utf-8"), ".json")
            # Preserve raw response before validation, including rejected/incomplete content.
            response_ref = store.blob(encoded(response), ".json") if response is not None else None
            usage = read_usage(response)
            store.append("attempt_end", dict(attempt_id=aid, ended_at=now(), usage=usage,
                         cost=estimate(usage, config.model, config.rates), response=response_ref,
                         error=failure, failure_kind=kind, error_response=error_ref))
            if response is not None:
                checked = interpret(response, letter)
                # A later empty failure must not erase substantive partial text.
                if not checked["text"] and outcome["text"]:
                    checked["text"] = outcome["text"]
                outcome = checked
                if outcome["execution"] == "complete":
                    break
                if not outcome["retryable"] or corrections >= 1:
                    break
                corrections += 1
                prompt = request["provenance"]["prompt"] + correction(outcome["errors"])
            else:
                outcome.update(errors=[failure], execution="failed")
                if kind in {"daily", "billing", "configuration"}:
                    if kind == "daily":
                        quota.update(exhaust=True)
                    outcome.update(execution="paused" if kind != "configuration" else "failed", stop_batch=True)
                    break
                if kind != "retry":
                    break
                if delay > config.max_retry_wait:
                    outcome.update(execution="paused", stop_batch=True,
                                   errors=[failure, "Server wait exceeds configured maximum; resume later"])
                    break
                if index == config.attempts - 1:
                    outcome["stop_batch"] = True
                delay = max(delay, min(60, 5 * 2 ** index))
            if index < config.attempts - 1:
                while delay > 0:
                    sleep(min(60, delay))
                    delay -= min(60, delay)
        return checkpoint_result(store, letter, request, outcome, ids, run_id), False
    finally:
        transport.close()
