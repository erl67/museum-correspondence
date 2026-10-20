"""Adapted accounting concepts from museum-transcription/token_usage.py.

No price table is copied. Missing counters stay unknown, including cached/reasoning.
"""


def read_usage(response):
    source = (response or {}).get("usage_metadata") or {}
    def count(name):
        value = source.get(name)
        return value if type(value) is int and value >= 0 else None
    usage = {k: count(v) for k, v in dict(input="prompt_token_count", output="candidates_token_count",
             reasoning="thoughts_token_count", cached="cached_content_token_count",
             total="total_token_count").items()}
    usage["billed_output"] = (usage["output"] + usage["reasoning"]
                              if usage["output"] is not None and usage["reasoning"] is not None else None)
    return usage


def estimate(usage, model, rates):
    if not rates or rates["model"] != model or any(usage[k] is None for k in ("input", "cached", "billed_output")):
        return None
    if usage["cached"] > usage["input"]:
        return None
    return dict(amount=((usage["input"] - usage["cached"]) * rates["input"] +
                        usage["cached"] * rates["cached"] + usage["billed_output"] * rates["output"]) / 1_000_000,
                currency=rates["currency"], assumptions=rates, kind="estimate, not invoice")


def aggregate(attempts):
    fields = ("input", "output", "reasoning", "cached", "total")
    return {key: sum(a["usage"][key] for a in attempts)
            if all(a.get("usage", {}).get(key) is not None for a in attempts) else None for key in fields}
