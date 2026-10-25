# Offline verification

From the repository root, with the pinned environment installed:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s test -t . -v
node --test apps_script/viewer/test_viewer.cjs
.\.venv\Scripts\python.exe -m compileall -q correspondence test
git diff --check
```

Recorded on **2026-10-25**, Windows, Python **3.14.2**, Node **24.19.0**:
**120 Python tests passed, 0 failed, 0 skipped; 50 viewer tests passed, 0 failed,
0 skipped.** Pinned runtime dependencies were installed in this repository's `.venv`:
google-genai 2.23.0, Pillow 12.3.0, tzdata 2026.3. The SDK emits a Python 3.14
`_UnionGenericAlias` deprecation warning; it does not fail the suite.

The correspondence-1.1 baseline passed 117 Python tests; the final 120 include approved-name
projection without private authority notes, retained ambiguous aliases, frozen context,
name/alias fingerprint changes with stable image bytes/order/IDs, and matching dry-run/live
request preparation using a fake transport. Existing CLI catalogue cases also check all four
names reach fresh requests without becoming a handwriting profile or changing saved evidence.
No service requests occurred. Read-only preparation of the actual saved 21-letter / 44-scan
inventory verified original bytes/order/resolution, four name candidates, changed fingerprints
for all old results and payloads below the configured limit (largest 10,105,383 estimated bytes).
This establishes request readiness, not improved reading accuracy. The 194-file pre-update
archive was hash-verified; results, inventory, quota and active exports are unchanged. One
append-only publication event adopts the existing Drive JSON only after exact byte comparison
with both generated local copies and the backup. No Drive files were written.

The catalogue update covers opt-in authority aliases, conflicting-name refusal, retained
uncertainty and source readings, catalogue-date confirmation expiry, and retired-record
exclusion with direct-link history/recovery. An initial viewer run caught a label variable
shadowing error (15 renderer failures); that was fixed and all 41 viewer tests then passed.
Tests establish software behavior, not historical accuracy.

Main-program rerun coverage uses the actual CLI and fake provider responses with temporary
synthetic scans. It verifies saved grouping/authority reuse through inventory, `--pending`,
cache reuse, export and remembered publication, plus fresh revisions and newly added letters.
All four preferred names persist across those workflows; original readings/certainty remain
intact. Known aliases stop generating spelling-conflict notes while ambiguous/different
identities remain flagged. No-request reruns preserve quota bytes, and a new service revision
expires a prior catalogue-date confirmation. No live collection publication occurs in tests.

The public-viewer update adds server-side active-record filtering, explicit reading-field
responses, search/connection leakage checks, verified public images without Drive links,
shared request/image budget exhaustion and reset, lock/cache failure behavior, and safe export
errors. Restricted-mode regressions remain covered. Public deployment configuration retains
drive.readonly. No live anonymous deployment or quota/load test was performed.

The 2026-10-22 folder/reader update passed the offline DOM/RPC tests. Its local synthetic
preview server was unreachable from the in-app browser (connection timeout); visual browser
verification remains outstanding. No native Google rendering or authenticated calls were made.

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

- Compact full/partial filename dates, `undated`, calendar validation, numeric page order
  through page 11, missing/zero/duplicate positions, same-date `-a`/`-b` letters, readable
  report names, legacy compatibility and migration preserving completed readings/history.
- Superseded managed reports are archived before removal; edited obsolete reports stop
  publication and interrupted cleanup can be retried.
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
  history, current filename-conflict notes after date corrections, and rejection of changed
  bytes, path escapes and duplicate targets.
- Synthetic strong reply evidence, ambiguous alternatives, misleading shared topics,
  unavailable references, chronology conflicts, mentions/enclosures, branching, cycles,
  explicit confirmations/rejections and metadata-driven rematching.
- Apps Script server functions and actual client script: literal escaped historical text,
  ordered scans, authorization on every RPC, missing/inaccessible/changed/oversized images,
  explicit relationship/review labels, unresolved references and absent transcriptions;
  compact-date/full-filename search and displayed current scan names in exported order.
- Complete expandable folder catalogues beyond 100 letters, filtered searches and stale-response
  handling, conservative document/hint chronology, partial/ambiguous dates, retired records,
  previous/next boundaries, folder return links, page-specific scan/text/translation pairing,
  summary-before-pages and metadata-after-pages, image proportions and decode failure recovery.
- Optional collection-folder lookup for unmapped images, exact nested Unicode paths and root
  images, duplicate/missing/trashed children, unsafe paths, MIME/size/hash failures, explicit-map
  priority without fallback, revoked access and bounds checked before any folder read.
- Saved normalized name/date display across lists, accessible links, letter headings and
  details, fallback for blank normalization, partial-date precision, preserved uncertainty,
  raw readings/evidence and literal source text, with original/normalized values searchable.

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
