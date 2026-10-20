# Configuration and request execution

Global options precede the command. All relative paths are relative to the current working
directory. Use `--store` consistently for a collection; its recorded absolute input root
cannot silently change. Source, store, quota and export paths must be separated.

Copy `docs/config.example.json` to `local/config.json`, edit it, then:

```powershell
.\.venv\Scripts\python.exe -m correspondence --config "local/config.json" dry-run --input "test/inputs"
.\.venv\Scripts\python.exe -m correspondence --config "local/config.json" transcribe --all --env-file .env
```

Unspecified settings use `correspondence/config.py`. Unknown configuration keys fail.
Model IDs must explicitly begin `gemini-`; this first version has one provider.
Unavailable models/parameters are reported as errors. No fallback model is selected.

| Setting | Default / meaning |
| --- | --- |
| `model` | `gemini-3.5-flash-lite` |
| `temperature`, `thinking_level` | `1.0`, `high`; supported local levels minimal/low/medium/high |
| `max_output_tokens` | 16,384; truncation is a failure, without automatic output-cap changes |
| `max_edge` | 0: retain resolution; positive value resizes in memory using Lanczos |
| `max_request_bytes`, `max_pages` | 19,000,000 conservative estimated inline bytes; 40 pages |
| `timeout` | 180 seconds per attempt |
| `attempts` | 3 total attempts per letter, including service and format retries |
| `rpm`, `daily_limit` | 2 starts/minute, 20 attempts/day; local allocation, not entitlement |
| `quota_file` | `local/quota.json`; persistent counter and cross-process start spacing |
| `quota_timezone` | `America/Los_Angeles`; `tzdata` installed on Windows |
| `max_retry_wait` | 120 seconds; larger server hints pause, never shorten the hint |
| `rates` | null: costs unknown; no copied/stale provider price table |

## Shared quota

Both applications may use the same Google project allowance. This application does not read,
reset, migrate, or modify the egg-slip counter. Its quota schema intentionally rejects the
egg-slip state format. Choose an agreed conservative allocation, coordinate concurrent use,
and retain the same counter path across runs and repository moves. Other machines or tools
can consume quota the local counter cannot see. Multiple correspondence stores can explicitly
share one correspondence quota file; they must use the same limits, timezone and account
allocation. Counters are keyed by provider/model, not account/key.

Every attempt is reserved under an OS lock before transmission. Atomic counter writes include
fsync. Start pacing persists across restarts. Daily exhaustion is remembered until the next
configured day; billing exhaustion stops immediately. A damaged/unwritable counter blocks
requests rather than silently resetting. A reserved but unsent attempt after a crash remains
conservatively counted.

## Transport and retry boundaries

The Google Gen AI SDK uses the fixed Developer API endpoint
`https://generativelanguage.googleapis.com/`, API version `v1beta`, `vertexai=False`,
millisecond timeout, SDK `retry_options.attempts=1`, disabled automatic function calling,
and JSON response MIME type. One execution loop accounts for all requests. The pinned SDK's
wire representation retains `thinking_level` inside `thinkingConfig`; the mocked HTTP test
asserts the value actually transmitted.

HTTP 408/429/500/502/503/504 and connection/timeouts may retry. Backoff starts at 5 seconds,
doubles to at most 60, and respects Retry-After and Google's RetryInfo. Retryable 429 waits at
least 60 seconds. Configuration/authentication/model errors stop the batch. Daily or billing
limits pause. A 503 is service unavailability, not proof of daily exhaustion.

Malformed/empty/incorrect-page output permits at most one format correction within the same
total attempt budget. Corrections resend all original images and the original prompt plus
structural instructions, not the previous answer as evidence. Truncation, blocked/refused
completion and non-text responses fail without correction. Honest uncertainty generates
review reasons rather than repeat spending. Every raw response and available partial text
is retained.

Request bytes are preserved unchanged where possible. EXIF orientation, color conversion,
and optional resizing occur only in memory; transformed JPEGs use quality 95, subsampling 0.
Original and submitted SHA-256 hashes and transformation descriptions are separate. The whole
letter must fit the configured payload/page bounds. There is no splitting or Files API upload.
The size bound is conservative and includes base64/JSON overhead, not a claim about a live
account's token limits. Use an explicit smaller `max_edge` only after assessing legibility.

Official references inspected on 2026-10-20:
[image input](https://ai.google.dev/gemini-api/docs/image-understanding),
[thinking levels](https://ai.google.dev/gemini-api/docs/thinking),
[generateContent API](https://ai.google.dev/api/generate-content),
[structured output](https://ai.google.dev/gemini-api/docs/structured-output),
[Python SDK](https://googleapis.github.io/python-genai/).
These describe transport capabilities, not this account's access or available quota.

## Cache, interruption and recovery

Cache identity covers ordered image IDs/paths/original and submitted contents, complete prompt,
prompt/application/schema versions, exact hints, handwriting context and generation settings.
Pacing, quota path and prices do not affect it. Stable letter IDs are independent.

Only the latest matching structurally complete result at most 48 hours old is eligible.
A later failed result for that fingerprint prevents falling back to an earlier success.
`--fresh` bypasses reuse while preserving history. `export` never reads credentials or scans
and works for older saved revisions. Normal transcription cache checks occur after source
integrity/payload checks.

The store lock covers a whole mutation/batch. Every request starts with a durable event;
submitted bytes and prompt are already content-addressed. Raw responses and usage are saved
before validation. Accepted/failed results are checkpointed before reports. If export fails,
fix its destination and use `export`; rerunning within cache eligibility also avoids payment.

After a crash between response journaling and result checkpointing, a normal run reconstructs
the result from the saved response with zero service calls. A start with no durable response
has an unknown outcome and blocks automatic retry. Inspect `show`, the journal and blobs;
only use `transcribe ... --retry-interrupted` if accepting a possible repeat charge.
No client can guarantee exactly-once billing after an unacknowledged network request.

Damaged journal lines fail closed, including a truncated final line. Back up the entire store,
inspect the byte-preserved tail and response blobs, and restore a known-good journal from
backup before resuming. There is deliberately no automatic truncation/deletion command.

## Usage and costs

Attempt-end events contain input, output, reasoning, cached-input, total and billed-output
counts where available. Reasoning is added to output for billed output once; cached input is
a subset of input, not an additional count. Total is the provider's total, not a sum that
double-counts cached input. Missing fields remain null. Aggregates with any unknown component
remain unknown. Errors before usage arrives are not labelled zero-cost.

`rates`, when explicitly supplied, must contain `model`, `currency`, `as_of`, `source`, and
prices per million tokens named `input`, `cached`, `output` (including reasoning). The result
is an estimate under those recorded assumptions, not an invoice or verified current price.
Default costs are unknown. Local exports and cache hits generate zero new API attempts;
historical revision usage stays separate from each run's new attempts.
