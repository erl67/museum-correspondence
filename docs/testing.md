# Offline verification

From the repository root, with the pinned environment installed:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s test -t . -v
node --test apps_script/viewer/test_viewer.cjs
.\.venv\Scripts\python.exe -m compileall -q correspondence test
git diff --check
```

Recorded on **2026-10-20**, Windows, Python **3.14.2**, Node **24.19.0**:
**100 Python tests passed, 0 failed, 0 skipped; 18 viewer tests passed, 0 failed,
0 skipped.** Pinned runtime dependencies were installed in this repository's `.venv`:
google-genai 2.23.0, Pillow 12.3.0, tzdata 2026.3. The SDK emits a Python 3.14
`_UnionGenericAlias` deprecation warning; it does not fail the suite.

The first run exposed a test expectation that assumed nested camelCase wire serialization.
The actual pinned SDK preserves `thinking_level` within `thinkingConfig`; the test now checks
the real serialized high-thinking value. Both real-SDK success and error HTTP paths pass using
`httpx.MockTransport`. No test sends network requests or uses a real API key.

After the chat pause, the repository was clean at merged commit `d2438ca`: implementation
commit `cb78591` was present alongside scan changes from `54d5ef4`. The baseline rerun had
82 Python passes and one stale six-file inventory expectation failure; all 18 viewer tests
passed. The current suite incorporates those source changes without moving or editing any
scan. It preserves the original six SHA-256 checks and replays their former A–D names in
temporary test storage. Added regressions cover numeric-label bounds, historical missing
paths, selecting older eligible cache revisions for exports, and approval invalidation.

## Coverage

- Current 25-file inventory under singular `test/inputs`, eight numeric-page groups, original
  six SHA-256 values, and replay of their former two/four-image A–B/A–D grouping.
- Folder/name collisions, duplicate/mixed labels, missing pages, ambiguous filenames,
  corrupt/unsupported/missing images, overrides, explicit regrouping, stable IDs and source changes.
- Original-byte preservation, EXIF transform, optional resize, request limits and fingerprint
  changes for complete prompt/settings/order/hints/profile changes.
- Metadata evidence/conflicts, Unicode, partial dates, unknown identities, two-digit-year
  ambiguity, blank/unrelated pages, duplicate/missing/out-of-order page coverage.
- Malformed/nested JSON, duplicate JSON keys, refusals, truncation, missing finish state,
  thought exclusion, preserved partial text and the saved synthetic truncated response.
- Service/format retries, pacing, quota across restarts/day boundaries, authentication/model/
  billing/daily limits, server retry hints, quota write failures and unknown token/cost values.
- 48-hour cache eligibility, fresh history, no credentials for cache hits, interrupted outcomes,
  raw-response recovery without resetting cache age, lock exclusion, damaged journals and
  export failure after durable payment-result checkpoints (including CLI continuation).
- Independent human review states, immutable original results, stale review rebasing, stable
  people/aliases, profile approval/versioning/bounds/batch isolation.
- Formula-safe CSV, significant-zero canonical strings, multiline Unicode, offline reports,
  explicit missing Drive mappings, hash-bound mappings and unprocessed/failed catalogue rows.
- Transcription-first named reports, source-folder publication and exact generated-file
  exclusions, protection of unowned/edited text and source paths, interrupted publication
  recovery, name collisions, current/absent/stale readings and pending-only continuation.
- Explicit byte-verified external filename reconciliation, preserved IDs/results/journal
  history, and rejection of changed bytes, path escapes and duplicate targets.
- Synthetic strong reply evidence, ambiguous alternatives, misleading shared topics,
  unavailable references, chronology conflicts, mentions/enclosures, branching, cycles,
  explicit confirmations/rejections and metadata-driven rematching.
- Apps Script server functions and actual client script: literal escaped historical text,
  ordered scans, authorization on every RPC, missing/inaccessible/changed/oversized images,
  explicit relationship/review labels, unresolved references and absent transcriptions.

All temporary fixtures live under ignored `local/test-tmp` and are cleaned up by unittest.
No optional skips hide missing SDK coverage: install requirements before running.

## Integration smoke checks

```powershell
.\.venv\Scripts\python.exe -m correspondence dry-run --input test/inputs
.\.venv\Scripts\python.exe -m correspondence inventory --input test/inputs
.\.venv\Scripts\python.exe -m correspondence match
.\.venv\Scripts\python.exe -m correspondence export
.\.venv\Scripts\python.exe -m correspondence show
```

The initial smoke check generated two unprocessed letter reports plus all CSV/JSON tables.
After the external source reorganization, refreshing the same store preserves those two
historical records with missing paths and adds eight current provisional records for the
25 scans. Missing historical records do not block the current groups. Their identities are
not automatically merged; an explicit grouping override can reconcile them after review.
The old journal bytes remain an exact prefix of the refreshed journal. No quota file or API
attempts were created. Matching finds zero proposals because no transcriptions exist; it
does not infer replies from filenames.

These tests establish software behavior, not reading accuracy. Synthetic fixtures are clearly
labelled and do not derive a supposed reference transcription from the museum scans.
Historical accuracy requires reviewed comparisons with source images. The viewer's native
Google template rendering, real authorization, deployment audience, image-transfer capacity
and latency remain unverified until authorized installation. Current Gemini account/model
access and actual billed prices were not tested.
