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

### Manual notes, entities and Percy corrections — 2026-10-27

Letter reviews now support explicit replacement of `notes` and `entities` arrays alongside
the existing page, metadata and summary fields. The same document validation runs before
append; omitted arrays stay unchanged and empty arrays clear them. These changes reset
metadata/relationship review to `in_progress`, preserve transcription approval unless pages
change, and expire on a new service revision just like other letter corrections. Reports,
viewer notes and local entity exports use the reviewed values. References and translations
still have no manual replacement fields. README and the review walkthrough describe the flow.

Three user-requested reviews were appended to `local/full-collection`: August 7, 1899 notes
and entities now use S. forsteri and explain Prof. Holland as William Jacob Holland; the
unsupported Brighton/Brightwood equivalence was removed from notes, summary and place
normalization while retaining the source reading Brighton, Virginia. April 18, 1899 has a
sourced, explicitly inferred location note for Smith Island near Cape Charles in Northampton
County. March 21, 1901 page 4 uses the user's exact Northampton / not Northumberland wording,
with the county entity's evidence aligned. The existing August page correction is preserved.
Holland was already normalized in the August entity data; its explanatory note was missing.

Review JSON is in `local/reviews/` with filenames ending `notes-20261027.json`,
`smith-island-20261027.json` and `page4-20261027.json`. Backups and verification are in
`local/manual-reviews-20261027/`; the guarded one-time helper is
`local/apply_manual_reviews_20261027.py`. The prior journal prefix, all original results,
inventory, blobs, quota and unrelated current records were checked unchanged. Local
`local/full-exports` was refreshed using `export_all`; Drive publication was not run
in that initial correction step.

Publication follow-up (2026-10-27): at the user's request, refreshed local exports,
published all 25 managed reader files to `G:\My Drive\Correspondence`, and refreshed
`local/viewer-deployment/Correspondence_viewer.json`. The local, Drive and prepared
viewer JSON copies match. Browser inspection of `https://cmbirds.org/letters` confirmed
the corrected Brighton summary in the catalogue and the Smith Island location note in
the April 18 reader. No redeployment or transcription request was needed. All 44 source
scan hashes, saved results, reviews, inventory and quota were preserved. Prior output
copies and the verification audit are in `local/publication-refresh-20261027/`.
No transcription requests, source-scan changes, deployment, commit or push occurred.
Verification: **122 Python and 55 viewer tests passed, no failures/skips**.

Deferred prompt work requested by the user: add concise approximate location explanations
in Separate Notes where evidence supports them, and consistently explain supported person
normalizations. Keep original names in source text; distinguish contextual inferences from
established identifications, cite research sources when used, and avoid inventing historical
equivalences between similar place names. Smith Island has namesakes, so preserve the basis
for the inferred Virginia identification. The user intends to revisit the prompt later;
this task made no prompt change or handwriting-profile update.

### Operating documentation and terminology — 2026-10-26

The README now links directly to individual reruns, handwriting recognition, identifier
construction and output updates. `docs/rerunning.md` covers selecting saved IDs, `--fresh`,
48-hour reuse, multiple letters, profile selection, unchanged-scan inventory reuse and
recovery. `docs/outputs.md` documents each output, remembered publication, refresh triggers,
Drive synchronization, mapping-only installations and the separate prepared deployment copy.

`docs/handwriting.md` explains within-letter comparison and the optional text-only profile
workflow. Profiles are explicitly selected for every command, frozen for a batch, versioned
and applied to all selected letters; names/aliases are separate automatic context. There is
no automatic writer learning, profile selection, sample-image retrieval or profile updating.
`docs/schema.md` now gives exact UUID5 construction, retained inventory identity, UUID4 result
revisions and request fingerprints. An unchanged fresh rerun keeps the fingerprint but creates
a new revision. Store continuity preserves revisions, reconciled IDs and publication ownership.

The Drive, prompt-rerun, review, configuration, transcription and viewer guides are aligned.
Publication refreshes `Correspondence_viewer.json` after results, but does not refresh the
prepared JSON in `local/viewer-deployment`. `review`, `match` and `reconcile-paths` need a later
export. Same-file data updates need synchronization/reload; script/settings changes need
redeployment. The user's neutral terminology preference is recorded in `AGENTS.md`.
This update changes documentation and a comment only; operating behavior is unchanged.
Verification: **120 Python and 55 viewer tests passed, no failures/skips**. Argument-only
checks accepted 46 documented command examples; all 70 local documentation links/anchors
resolved. A terminology scan passed across 58 tracked/new text files. No live transcription,
collection export, Drive write, deployment, commit or push was performed.

### Catalogue summary snippets — 2026-10-26

Catalogue rows now include a maximum 360-character interpretive-summary snippet from the
saved summary, rendered as literal text beneath its letter's metadata across four columns.
Inset spacing, a subtle background and left accent distinguish it within the same table.
Missing summaries omit the extra row; full letter summaries and stored text remain unchanged.
This adds bounded text to the existing response and DOM, with no additional Drive reads,
RPCs or image downloads. Both Code.gs and Viewer.html must be replaced and deployed as a
new version; JSON regeneration is unnecessary. The existing footer and date/name changes
are preserved. Prepared local source copies were refreshed with backups.
Verification: 120 Python and 55 viewer tests passed, zero failures/skips. No deployment,
Drive writes, source changes, commit or push occurred; native browser layout remains unverified.

### Filename dates keep catalogue placement after reruns — 2026-10-26

The latest complete August 7 Percy result reads `Aug 7 - 99`, normalized to `1899-08-07`.
Its prior catalogue-date review correctly became stale on the new revision. The remaining
viewer bug was that any document date blocked filename fallback, so the valid saved filename
date could not place the letter. The earlier per-revision confirmation was too narrow a fix.

Catalogue sorting now prefers an applicable confirmation, then a supported document date,
then any calendar-valid filename date, including when the document date is ambiguous,
abbreviated, uncertain or malformed. Lists, navigation, headings and details use the selected
date consistently and label filename placement **Filename hint · unverified**. Source date
readings/evidence remain intact. Unsupported/missing dates without a valid filename still
sort last. Partial dates retain precision. Relationship chronology and review expiry are unchanged.

Both main viewer source files and the local prepared copies are updated. Deploying those two
files as a new version is required; the existing fresh JSON already has the needed hints.
No additional transcription, JSON replacement or review event is needed. Original saved
results, store, quota, source scans and exports are unchanged. Verification: **120 Python
and 53 viewer tests passed, no failures/skips**, covering public and restricted readers,
short-year reruns, navigation, differing unsupported proposals and partial/invalid dates.
An offline check of the latest real export placed all current letters, including the four-page
August 7 letter between April 18 and September 16, in both public and restricted modes.
No live requests, Drive writes, deployment, commit or push occurred.

### Correspondent context and reading prompt — 2026-10-25

Prompt `correspondence-1.1` responds to staff review of saved Sutton/Shufeldt readings.
It asks for evidence-backed identity expansion, scientific/common bird-name recognition,
cross-line/page and repeated-letterform checks, a second look at uncertain and confidently
awkward readings, and plain-text superscript ordinals. It preserves source spellings and
uncertainty; no hardcoded letter corrections or automatic text replacements were introduced.

The existing approved person registry now supplies a frozen names/aliases-only candidate
list in both dry-run and transcription requests. `prompt.py` owns its projection/policy;
the CLI reads it once per batch and `images.py` snapshots it in provenance and fingerprints.
This is separate from approved handwriting profiles and catalogue display matching. Saved
model readings, reviewer notes and internal authority sources are not sent as name context.
Provider/settings, image preparation/order, schema, retries/accounting and stable IDs are
unchanged. The new prompt intentionally invalidates old request fingerprints, retaining all
stored revisions and reviews. Names/aliases change fingerprints; internal note edits do not.

See [prompt rerun](prompt-rerun.md) for the existing-store command, 48-hour continuation,
review rebasing and same-Drive-file viewer update. The actual current export tree is
`local/full-exports`; its pre-update snapshot and the store/deployment/config backup are under
ignored `local/archives/20261025-before-prompt-1.1/`, with a hash manifest. Active exports are
retained for refresh; no new transcriptions, Drive writes, publication or deployment were run.
The source root now contains `old/` and `analysis/` material, so unchanged-scan reruns should
use the saved inventory rather than rediscovering those folders as potential records.
Existing uncommitted catalogue/rerun/documentation work was preserved.

Preflight found the Drive viewer JSON was already the 23 October catalogue export, identical
to both local generated copies, while the publication ledger still owned its older hash.
A single `text_publication` event adopts that exact verified version, preserving the prior
journal prefix and all result/inventory/review/quota bytes. This avoids an overwrite refusal
on the first rerun; no publication guard was relaxed. The archive includes the Drive copy,
adoption audit and readiness report. Verification: **120 Python and 50 viewer tests passed,
no failures/skips**; all 21 original-resolution requests fit, with 44 unchanged ordered scans.
No live requests, source edits, Drive writes, commits or pushes were performed. Reading
improvement still needs assessment after an authorized rerun.

### Main-program catalogue reruns — 2026-10-25

Confirmed that all inventory/transcription/export paths derive catalogue labels from persistent
person reviews, including fresh responses and newly discovered letters. No dependency on the
ignored one-time repair script exists. Current filename/name conflict checks now recognize
unique enabled authority aliases, so known Todd/Shufeldt abbreviations stop generating false
spelling conflicts. Genuine/ambiguous conflicts and historical result validation are preserved.

New offline CLI regressions exercise grouping repair, repeat inventory, pending continuation,
cache reuse, exports, automatic publication into temporary synthetic inputs, fresh responses,
and new letters with all four preferred names. They verify original results/pages, saved
authority records, unchanged scans/quota on no-request reruns, and proper expiry of date
confirmation on a new revision. The current full-collection store remains the source of the
user's names and decisions; replacing it with an empty store does not carry those decisions.
Verification: **117 Python and 50 viewer tests passed, zero failures/skips**. Read-only
inspection of the real store found all four enabled names, 49 standard name fields, 21 active
letters and two retired records. Only the unresolved C. M. Sutton name conflict remains.
No live transcription, Drive write, deployment, commit or push was performed.

### Canonical viewer address — 2026-10-25

The canonical reader address is **[cmbirds.org/letters](https://cmbirds.org/letters)**.
The main README, Drive guide and viewer setup guide use it for access, bookmarks and sharing.
Apps Script execution (`/exec`) and script-editor URLs are maintenance details. When replacing
a deployment, maintainers must keep the canonical address pointing to the intended deployment
and verify reading through that address. This documentation-only change does not alter or
verify live routing, deployment or access settings.

### Intentional public viewer — 2026-10-23

At the user's request, Code.gs now enables PUBLIC_MODE and the manifest uses USER_DEPLOYING /
ANYONE_ANONYMOUS, retaining drive.readonly. This supersedes the earlier reader-only deployment
guidance. The existing supplied IDs, catalogue-name display and date confirmations are preserved.
Public mode deliberately skips the reader gate: owner Drive access is not visitor authorization.
Every RPC filters to active:true records; retired IDs/images and connections to retired targets
are refused/withheld. Explicit response field lists retain reading content, uncertainty and
metadata evidence while withholding provenance/prompts/profiles, partial raw responses, internal
review reasons, authority sources/IDs, prior scan paths, Drive IDs and global diagnostics.
Public search uses the same filtered fields. All source data/history remains intact.

Public image replies omit direct Drive links but retain original verified bytes, sequential
loading, membership, path, MIME, size and hash checks. Export errors no longer return parser
excerpts or Drive exceptions. A lock/cache counter sheds excess public load before Drive reads
(120 requests / 60 image requests per minute shared by all visitors); eviction may reset it.
It is not authentication, a hard quota or denial-of-service protection. Anonymous traffic can
still exhaust owner quotas. The current design is not validated for 10,000 letters.

Staff must copy Code.gs, Viewer.html and appsscript.json, then deploy a new version as Me /
Anyone and test signed out. Existing JSON works; the prior catalogue update still requires its
refreshed JSON for standard-name/date data. Keep raw JSON private to preserve the response
filtering. End public access by archiving all public deployments; PUBLIC_MODE:false alone
does not restrict an owner-executed deployment. Restricted mode requires USER_ACCESSING and
an appropriate audience as documented in the viewer README.

Offline verification: 114 Python and 50 viewer tests passed, zero failures/skips. No Drive
requests, uploads, sharing changes, deployments, commits or pushes occurred. Native Google
authorization/rendering and deployed access remain unverified. Other chats' catalogue changes
and Python work were preserved.
An additional offline smoke check of the current local export preserved all 21 active letters,
44 scans and 44 transcription pages across two folders, and refused the two retired records.
The check first compared JSON property order unnecessarily; after using structural comparison,
all original page text/annotations and metadata matched. The ignored deployment copies of all
three source files and SETUP.txt were refreshed with content-hashed pre-update backups; its
prepared JSON was left unchanged.

### Catalogue corrections and standard names — 2026-10-23

The viewer now excludes retired groupings from catalogue/search/navigation while preserving
direct historical links with links to active letters sharing the scans. The two retired
one-page groups caused the duplicate August 7, 1899 and December 9, 1923 entries. The complete
August letter had a saved `Aug 7 - '99` date; the four-digit-year guard excluded it from sorting.
A separate revision-bound catalogue-date confirmation records the user's confirmation of
1899-08-07 without rewriting that source date or changing relationship matching policy.

`catalogue.py` resolves explicitly enabled, unique authority aliases for display only.
Original normalized proposals, source text/evidence, attribution certainty and person links
remain unchanged. The local full-collection store now contains the four user-supplied standard
names (Percy Shufeldt; Robert W. Shufeldt; W.E. Clyde Todd; George Miksch Sutton), yielding
49 standard name labels across 21 active letters. The inferred C. M. Sutton / [CMS] reading
on 1923-12-13 remains unresolved. Future exports reuse these aliases; new/ambiguous variants
need explicit staff decisions. No alias is promoted into approved handwriting context.

The original journal prefix, results, documents, inventory/page order, review states and quota
bytes were verified unchanged. Four authority reviews and one catalogue-date review were
appended. `local/full-exports` and the prepared files in `local/viewer-deployment` were refreshed.
The fixture store/export was left alone. Backups and verification are in
`local/catalogue-repair-20261023/`; the repeatable local script is
`local/standardize_catalogue_20261023.py`.

To update the live viewer, both Apps Script source files and the contents of its existing
viewer JSON file need replacing, preserving its Drive ID, followed by a new deployment version.
Nothing was published to Drive or deployed in this task; the local script deliberately calls
`export_all` directly because CLI export remembers prior publication and would write beside scans.
Offline results: **114 Python and 41 viewer tests passed, no failures or skips** after fixing
a renderer variable-shadowing failure. Source scans were untouched. No service calls, upload,
sharing changes, deployment, commit or push occurred.

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

Staff TXT reports no longer append the closing disclaimer. Existing local reports,
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
| apps_script/viewer | Read-only public or reader-authorized Drive viewer, search and ordered scans |

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
