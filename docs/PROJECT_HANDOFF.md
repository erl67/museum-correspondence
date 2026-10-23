# Project handoff — 2026-10-20

Application **0.1.0**, schema **1**, prompt **correspondence-1.0**. Initial independent
correspondence implementation. The repository began clean on main at `fa8abd1`, containing
six tracked JPEGs and .gitignore. The read-only reference repository was clean on main at
`ca81d25`; its files, configuration, counters and source collection were not edited.

## Resumption and integration

On resumption after the usage interruption, Git was clean at merge `d2438ca`. The previously
written implementation had been committed externally as `cb78591` (alpha); source changes
in `54d5ef4` moved the original six byte-identical JPEGs into `Shufeldt, Percy`, replaced their
A–D suffixes with numeric labels, and added 19 scans. Current fixtures contain 25 tracked
JPEGs in `Shufeldt, Percy` and `Shufeldt, RW`, grouped into eight provisional letters. These
commits and source changes were preserved; this task did not make them or revert them.

The remaining final verification was completed against that state. Tests/docs now reflect
the current collection while retaining historical six-scan hash/A–D regression coverage.
Additional fixes bound numeric-label validation, prevent missing historical paths from
blocking a distinct current group, persist selection of an older cache revision so exports
show the requested result, and invalidate prior approval when human text/metadata changes.
Current offline results are 88 Python and 18 viewer tests passing, with no failures/skips.

The original local store/export history is retained. Refreshing it creates eight current
unprocessed records and leaves two older missing-path records visible for explicit identity
reconciliation. No automatic hash merge or purported human historical verification is applied.
No live requests, quota reservations, uploads, deployment, new commits or pushes occurred
during this resumed work.

## Responsibilities

### Main viewer settings filled — 2026-10-23

At the user's explicit request, all three Drive settings are now populated in the main
`apps_script/viewer/Code.gs`, as well as the ignored local deployment copy. The same supplied
viewer JSON file serves as access gate and export; the supplied collection folder is the scan
root. This supersedes the earlier blank-template setup described below. The offline viewer
harness replaces configured IDs with synthetic IDs before execution; no real Drive calls occur.

### Normalized name/date display — 2026-10-22

Folder tables, accessible letter links, headings and metadata details now prefer saved
normalized sender/recipient/attributed-author names and dates, falling back to original
readings when normalization is absent/blank. Dates retain their exported precision. Raw
readings/evidence remain in the collapsed provenance panel and page text is unchanged.
Other metadata still shows its source reading with a separate normalized value where present.
Uncertainty, review labels, chronology policy, records and archival identities are preserved;
different saved normalized names are not automatically merged or rewritten.

The ignored configured deployment copy's Viewer.html was refreshed with its three existing
Drive IDs preserved in Code.gs. Only Viewer.html needs replacing for this display update;
the existing deployment must then use a new version. No export regeneration is required.
Offline verification: **110 Python and 38 viewer tests passed, no failures or skips**.
No live requests, upload, sharing changes, deployment, commit or push occurred.

### Read-only scan lookup by collection folder — 2026-10-22

The deployed-viewer setup exposed that local exports have scan paths but no Drive image IDs.
The optional `SCAN_ROOT_FOLDER_ID` setting now lets the viewer resolve an unmapped scan by
its exact relative folder/filename path under that explicit Drive root. `loadLetter` advertises
folder lookup only in its response; stored exports and source scans remain unchanged. Image
requests keep the access gate, export pin, page membership, inventory state, MIME/size limits
and SHA-256 checks. Explicit mappings take priority and do not silently fall back on errors.

Only exact child-name lookups are used, with no Drive-wide search, shortcut following or
cross-reader cache. Duplicate visible paths and unsafe relative paths are refused. Inaccessible
or absent paths are honestly reported as unavailable to the reader. Staff must copy both updated
viewer source files into Apps Script, preserve their existing file IDs, set the collection root
folder ID, and update the deployment version; no JSON regeneration is needed for this option.

The root setting is blank in tracked source; institution-specific IDs stay out of the repository.
Offline verification: **110 Python and 35 viewer tests passed, no failures or skips**.
No source scans, exports, saved results, sharing or deployed code were changed. No live Drive
or transcription-service requests, upload, deployment, commit or push occurred.

### Folder catalogue and letter reading view — 2026-10-22

The Apps Script viewer now starts with expandable source folders and complete chronological
sender/recipient tables, including labelled unprocessed/retired entries. Search filters those
folders without the legacy 100-row cap. Supported document dates determine order; valid filename
dates are explicitly provisional fallbacks only when no document date exists. Ambiguous and
undated letters sort last. Equal dates use stable IDs; partial dates retain their precision.

Each letter view places its interpretive summary first, then one scan-left/transcription-right
pair per source page, matched by image ID in exported order. Both sheets match the decoded
image's proportions on desktop, with scrollable long text; mobile pairs stack with full-height
text. Metadata, reviews, notes, partial responses and connections follow all pages. Previous/next
letter controls at both ends follow that folder's full order; returning to folders reopens it.
Existing schema-1 exports work without regeneration. Authentication and hash checks are unchanged.

Offline verification: **110 Python and 28 viewer tests passed, no failures or skips**.
No source scans, saved readings or exports were changed. No live service requests, upload,
sharing change, deployment, commit or push occurred. The access/export IDs remain unconfigured;
native Google rendering and authenticated deployment checks still require authorized setup.
The local synthetic browser preview could not be reached by the in-app browser (connection
timeout), so visual browser verification remains outstanding. Its optional preview harness is
in ignored `local/viewer-preview-20261022.cjs`; the preview server has been stopped.

### Authorized filename convention migration — 2026-10-21

The user explicitly authorized renaming the Drive collection to
`Sender-Recipient-YYYYMMDD_01.jpg`. All 44 JPEGs in `G:\My Drive\Correspondence` were
renamed in place, with unchanged SHA-256 values. Explicit path reconciliation preserves
21 active saved completed readings, all image/letter IDs, page membership/order, review
states, prior journal bytes, original results and quota counters. Four grouping overrides
and `local/drive-grouping.json` use current paths; recognized title dates are compact.

`naming.py` now owns page-label parsing, date-hint normalization and compact report stems.
Discovery, reconciliation and readable reports share it. Compact dates, partial dates,
`undated`, and separate same-date letters (`-a`, `-b`) are supported alongside legacy names.
Catalogue/schema dates remain dashed; no historical metadata is inferred from renaming.
The tracked source fixtures remain unchanged for legacy compatibility coverage.

Both current local export trees were refreshed, and 25 current Drive outputs were read
back and verified. Publication archives obsolete owned reports as content-addressed blobs
before removal, retaining ownership through interrupted cleanup. Twenty-two old Drive
report paths were removed, including one earlier superseded placeholder. Local obsolete
readable reports are backed up outside active exports. Current filenames appear in reports
and viewer scans; historical provenance retains the names used for original requests.

Recovery material and verification are under ignored `local/naming-migration-20261021/`;
the operation script is `local/migrate_naming_20261021.py`. It checked all renamed scan
hashes, saved text inclusion, future JPEG grouping, unchanged evidence/history and zero new
attempts. Independent `analysis.txt`, historical `prompt.txt` and the PNG map were preserved.
The Drive desktop mount was verified; cloud synchronization completion was not observed.
No Gemini calls, sharing changes, viewer deployment, commit or push occurred.
Offline verification: **110 Python and 19 viewer tests passed, no failures or skips**.
See [naming.md](naming.md) for staff rules and recovery details.

### Output cleanup and filename corrections — 2026-10-21

Staff TXT reports no longer append the closing AI disclaimer. Existing local reports,
including older generated filenames, were cleaned and the Drive reader copies refreshed.
Current filename/reading conflict notes are recalculated from current hints; historical
validation and request provenance remain unchanged in the saved results.

The user-renamed July 4 scan was byte-verified and explicitly reconciled to February 4,
1908, retaining the same image/letter IDs and saved February 4 reading. The user also
approved reconciling the November 8, 1923 filename from Unknown to Sutton. This corrects
filename references only; it does not change the saved sender metadata or approve the reading.
Both generated report names and current catalogue/viewer references were refreshed. The
already-renamed February TXT was checked against its recorded generated content before adoption.
Obsolete local report names were archived under ignored `local/`; old Drive report paths
are absent. All 26 managed Drive outputs were read back and their ownership hashes verified.

All 44 scan paths/bytes present at the start were preserved, along with 21 completed saved
readings, the earlier journal prefix, original results and quota counters. No Gemini calls,
sharing changes, deployment, commit or push occurred. Offline verification: **101 Python
and 18 viewer tests passed, no failures or skips**. Recoverable snapshots and verification
summaries are in ignored `local/output-repair-20261021` and `local/sutton-output-repair-20261021`.

### Drive reading/export update — 2026-10-20

The requested daily allocation is now **100 attempts**, still 2 starts/minute. The ignored
`local/config.json` contains that override; the code default also applies to commands without
`--config`. Existing counters are preserved. `transcribe --pending` skips current complete
readings regardless of cache age and is the preferred continuation command.

`plaintext.py` renders staff reports with ordered transcription text before plain-English
metadata/notes. `exports.py` retains technical ID reports and JSON/CSV, and adds readable
filenames plus a plain combined report. `publication.py` implements explicit `--publish-text`:
named TXT beside scans, per-folder combined TXT, collection-wide TXT and a viewer JSON copy.
Publication is remembered per store. Journalled output hashes protect unowned/edited files,
allow interrupted publication recovery, and identify exact generated paths to exclude from
discovery. This is the intentional exception to keeping full diagnostic exports outside scans.
Files sync through Drive for desktop; no sharing or deployment changes are performed.

`relocation.py` and `reconcile-paths --file` apply only explicit old/new path maps verified
against original SHA-256 values. Stable IDs, prior responses and all old journal bytes remain
intact. No automatic hash-based merge is added. In the local Drive store, the user corrected
filenames and identified the page-2 naming mistake. A byte-verified map plus explicit local
grouping overrides preserve 44 source images and 18 saved completed readings; 3 letters
remain unprocessed, with no active grouping blocks. The April 18 letter has two pages, as
confirmed by the user. Mixed `Shufeldtt`/`Shufeldt` September filenames are handled by an
override rather than editing scans. All these decisions are grouping/identity only.

25 generated Drive files were saved and read back: 21 individual reports, two folder reports,
one collection report and one viewer bundle. All saved page text was checked for inclusion;
the 44 scans and the earlier journal prefix are unchanged. No new Gemini attempts were made
by this update. The viewer still needs real Drive mappings/access-gate/export IDs and deployment.
Offline verification: **100 Python and 18 viewer tests passed, no failures or skips**.

| Module | Responsibility |
| --- | --- |
| naming | Current/legacy page labels, date-hint formatting and compact report stems |
| discovery | Recursive JPEG inventory, integrity, conservative folder-scoped grouping, persistent IDs, overrides and missing/retired history |
| prompt / schema | Historical reading policy, metadata evidence/uncertainty, JSON/page validation and defensible date intervals |
| images | In-memory JPEG preparation, original/submitted hashes, whole-letter payload check, immutable complete request context/fingerprint |
| provider | Explicit Gemini SDK transport, credentials, completion signals; no retry loop |
| execution / usage | One attempt loop, retry policy, persistent quota/pacing, raw responses, checkpointing, usage and optional rate assumptions |
| storage | Atomic writes, OS locks, fsynced append-only journal and content-addressed blobs |
| review / profiles | Persistent human correction/identity/link layers and explicit frozen handwriting context |
| relationships | Local explained candidates, unresolved references, decisions and graph validation |
| exports / cli | Offline TXT/CSV/JSON/viewer output and documented commands |
| apps_script/viewer | Read-only user-authorized Drive viewer, search and ordered scans |

No sibling imports, server, plugin framework, provider benchmark or hidden background worker.

## Reuse and origin

Read `museum-transcription/docs/PROJECT_HANDOFF.md`, current configuration/testing docs,
`transcribe.py` image preparation, request/retry/quota/completion/journal/hash/report code,
`token_usage.py`, and Apps Script viewer patterns before implementation.

The small JPEG preparation routine was adapted from `prepare_image_bytes` in
museum-transcription build **2026-10-19.1** at commit `ca81d25`:
preserve unmodified JPEG bytes, EXIF transpose, optional Lanczos resize, RGB conversion,
quality 95 and subsampling 0. It now also reports transformations and hashes original bytes.
Usage field separation/aggregation, explicit retry accounting, atomic counter writes,
checkpoint-before-export and 48-hour reuse are independently implemented from those proven
patterns. No price table, egg-specific schema, catalogue dependency, paths, credentials,
front/back rules, or report parser was copied.

The viewer reuses design patterns (reader identity access gate, deferred authenticated image
loading, stable positions, escaped text and version/hash checks), not the old collection's
IDs, catalogue routing or deployment. Source materials retain their existing rights; this
task makes no new licensing/publication claim.

## Persistence and review choices

One authoritative JSONL journal plus blobs keeps this first version inspectable. Derived
exports are replaceable. Source updates preserve image IDs at the same path but invalidate
request fingerprints and human-review applicability. Added pages require grouping review;
explicit regrouping retains an existing letter ID only when requested in the override.

The reference application's 48-hour automatic completed-cache eligibility is preserved.
Unlike its fresh console modes, `--fresh` here journals every new revision; this deliberate
departure protects correspondence history. Damaged journal tails fail closed rather than
being silently skipped. Raw response recovery can avoid repeat payment after an interrupted
result checkpoint; unknown network outcomes require explicit retry acknowledgement.

Quota state is deliberately separate and incompatible with old counters. Defaults are a
2 RPM/100 attempts/day allocation, not a second project allowance. Coordination
with the existing application is a staff operational responsibility.

Reviews bind to one service revision, and relationship decisions retain the document state
that supported them. A new service revision does not silently overwrite/reapply human text.
Named-person approval is distinct from physical handwriting and from full transcription review.
Profiles contain reviewed text examples/source references only; no automatic training.

## Verification and limits

See [testing.md](testing.md) for commands/results. Current numeric-page grouping, the original
six scan hashes and historical A–B/A–D inventory behavior are regression-checked. None of the
scans were transcribed by a live service in this task; no verified reference readings are
claimed. Synthetic fixtures test reply behavior.

Current limits:

- Python command line is the local editing/review interface; no review GUI.
- Grouping is conservative exact-folder/stem parsing, not handwriting/page-content clustering.
- Whole-letter inline JPEG requests only; no PDF, TIFF, splitting or upload strategy.
- JSON MIME requests use the prompt contract plus local validation; no claimed semantic guarantee.
- Failed malformed responses are preserved, but local correction requires a current structurally
  complete base result. There is no salvage-import operation yet.
- Full reports/CSV/history are local; explicitly enabled reader copies can be saved beside
  Drive scans. Viewer installation, actual Drive mapping/access,
  native Google rendering and any future service-account availability require staff setup.
- Pairwise matching and full export rereads are appropriate for an initial collection, not
  unlimited scale. Matching uses saved structured references rather than automatic prose NLP.
- The access/export file IDs and collection scan folder are configured from user-supplied links.
  No data upload, sharing change or deployment was performed by this agent.
- Historical reading fidelity, transcription completeness, identities, dates and reply links
  require human review. Hashes and software test counts establish neither accuracy nor authorship.

Future work should start with a small authorized transcription and reviewed source baseline,
then improve metadata/reference extraction from that evidence. Do not silently tune the prompt
or generation settings from unreviewed model output.
