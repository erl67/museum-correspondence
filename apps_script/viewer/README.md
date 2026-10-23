# Read-only correspondence viewer

Files: `Code.gs`, `Viewer.html`, `appsscript.json`. Node tests and this README are not Apps
Script source. The viewer requires no Gemini credentials, no Python runtime, and no
transcription-service requests. It reads an explicitly supplied `viewer.json` export and
scans from a configured collection folder or explicit image mappings. This checkout is
configured for intentional public reading, running under the deploying account.

Nothing was uploaded or deployed during implementation. These installation steps are for
the maintaining staff member's later authorized setup.

## Prepare data locally

1. Run Python `inventory`, then any authorized transcription/review work.
2. Run `match` and `export`. Unprocessed records can be displayed without transcriptions.
   For the Drive collection, `export --publish-text` also saves
   `Correspondence_viewer.json` at the scan root, alongside human-readable text reports.
   The viewer continues to consume JSON internally; staff do not need to open that file.
3. For the simplest setup, configure `SCAN_ROOT_FOLDER_ID` during installation below.
   Existing exports with `missing_mapping` scans work without regeneration. The viewer finds
   each JPEG by its exact exported relative path beneath that folder, then verifies its bytes.
   Alternatively, use `images.csv` to create an explicit image-ID mapping under ignored `local/drive-map.json`.
   Verify each Drive scan is the same original byte content before recording its local hash.

```json
{
  "version": 1,
  "images": {
    "img_REPLACE": {
      "file_id": "REPLACE_WITH_ACTUAL_DRIVE_FILE_ID",
      "original_sha256": "REPLACE_WITH_INVENTORY_SHA256"
    }
  }
}
```

This is a schema example, not a functioning ID. Obtain real file IDs from Drive links for
the already-accessible originals. Do not use a Windows path as a URL, infer IDs from filenames,
or make files public. Duplicate filenames require matching folder context and bytes.

```powershell
.\.venv\Scripts\python.exe -m correspondence export --mapping "local/drive-map.json"
```

Explicit mappings bind to exact inventoried image hashes. The viewer rechecks Drive image bytes against
that hash before display. The mapping file is external to transcription identity; editing it
never triggers a transcription request. Supply `--mapping` whenever regenerating the mapped
viewer bundle. Ordinary exports without that option explicitly show missing mappings.

The current naming convention is `Sender-Recipient-YYYYMMDD_01.jpg`. The viewer uses
ordered scans and filenames from the export, so it needs no filename parser changes.
Search accepts the compact date or full filename through current filename hints, as well
as normalized dashed dates. Regenerate the export after path reconciliation; preserve
image IDs and byte hashes, and verify the actual Drive IDs when maintaining the mapping.

## Installation and access

The three Drive IDs in Code.gs are prefilled with the IDs supplied by the user.
`PUBLIC_MODE: true` intentionally publishes all records marked `active: true` in that export.
Anyone can read and save their scans, transcriptions, summaries, historical metadata, evidence,
notes and connections. Future active records added to this export also become public.
The JSON and scan folders can stay private in Drive: the app reads them using your account.
Only trusted maintainers should be able to edit the script, JSON or image mappings.

Public responses use explicit field lists. They omit technical provenance/prompts/handwriting
profiles, raw partial responses, internal review reasons, authority sources/IDs, previous paths,
Drive IDs and export-wide diagnostic warnings. Retired records are refused by every public
RPC, including direct letter/image requests; connections to them are withheld. Stored exports
and history are unchanged. This filtering is not a content review: historical letter text,
addresses, notes and evidence are intentionally public. Keep the raw JSON private if it contains
internal information; making that file public would bypass the viewer's filtering.

1. Create a separate Apps Script project. Add Code.gs and an HTML file named **Viewer**.
2. Show the manifest in Project Settings; copy `appsscript.json`.
3. Keep `PUBLIC_MODE: true`. `ACCESS_FILE_ID` is unused in public mode and can remain filled in.
   An owner-executed Drive read checks the owner's permissions, not the visitor's.
4. Use the synced `Correspondence_viewer.json` created by `export --publish-text`, or upload
   the local `viewer.json` through the institution's approved Drive workflow, and set
   `EXPORT_FILE_ID` to that file's real Drive ID. Verify the synced file ID after updates.
   No Drive API uploader or sharing modification exists in this project.
5. Set `SCAN_ROOT_FOLDER_ID` to the Drive folder containing the scan subfolders. For example,
   if the displayed caption is `4. Shufeldt, Percy/Shufeldt,P-Todd-18990807_04.jpg`, the root
   must contain the `Shufeldt, Percy` folder. The `4.` is the page number, not part of the path.
   Open the collection folder in Drive; copy the part after `/folders/` from its address.
   Put that folder ID in `SCAN_ROOT_FOLDER_ID` near the top of Code.gs.
   Keep `ACCESS_FILE_ID` and `EXPORT_FILE_ID` as file IDs. This new setting is specifically a
   folder ID. Leave it blank only when using explicit per-image mappings instead.
6. Use **Execute as: Me** and **Who has access: Anyone**, including visitors without a Google
   account. The manifest uses `USER_DEPLOYING` and `ANYONE_ANONYMOUS`. `ANYONE` in the
   manifest means logged-in users only. Workspace policy may prevent anonymous deployment.
7. Deploy a versioned web app. Updates require a new deployment version; saving code alone
   does not update an existing `/exec` deployment.

For an existing installation, copy all three files: **Code.gs, Viewer.html and appsscript.json**.
To see the manifest, open **Project Settings → Show appsscript.json manifest file in editor**.
Save, then **Deploy → Manage deployments → Edit (pencil) → Version: New version**.
Choose **Execute as: Me**, **Who has access: Anyone**, then **Deploy** and authorize the
read-only Drive scope as the deploying account. If that deployment cannot change execution
identity, create a new web-app deployment with those settings and use its new `/exec` URL.
Test the `/exec` URL in a signed-out/private browser window, including a letter and all its scans.
This public-mode update does not require regenerating the JSON.

To end public access, archive every public deployment in **Manage deployments**. Saving source
alone does not change a published version, and previously downloaded copies cannot be recalled.
For a restricted replacement, set `PUBLIC_MODE: false`, configure `ACCESS_FILE_ID`, and deploy
with `USER_ACCESSING` / `ANYONE` (or a narrower audience). Readers then need permission to the
gate, JSON and individual scans. **Changing PUBLIC_MODE to false alone does not make an
owner-executed deployment private.** Restricted mode retains direct historical links and
full technical evidence for authorized staff; verify both allowed and denied reader accounts.

Folder lookup is read-only and uses the deploying account in public mode, or the reader in
restricted mode. It walks only the exact
exported path under the configured root, including nested subfolders; it does not search the
whole Drive or follow shortcuts. Duplicate visible folder/file names are refused, with a
request for an explicit mapping. A path not visible to the executing account is reported as unavailable,
without asserting deletion. Renamed or byte-changed scans require correcting the export/path
or mapping. Explicit image mappings take priority and never fall back after a mapped-file error.
Both modes enforce the same JPEG type, image/letter byte limits and SHA-256 verification.
Folder lookups occur only when loading a page image, after the mode checks and export token
checks. They do not modify the export, archive IDs, source files or sharing.

The scope is only `drive.readonly`: no Drive writes, deletes or sharing changes are implemented.
That OAuth scope can read the executing account's Drive broadly, but the viewer's RPCs accept
only exported letter/image IDs; visitors cannot supply arbitrary Drive IDs or paths. Scans
must pass membership, JPEG type, size and SHA-256 checks. No OAuth tokens reach the browser.
Public image responses omit Drive links, since visitors may not have direct Drive permission.

Official references: [web-app permissions](https://developers.google.com/apps-script/guides/web#permissions),
[manifest settings](https://developers.google.com/apps-script/manifest/web-app-api-executable),
[escaped templates](https://developers.google.com/apps-script/guides/html/templates),
[Drive file access](https://developers.google.com/apps-script/reference/drive/file).
Folder lookup uses the read-only [Drive Folder methods](https://developers.google.com/apps-script/reference/drive/folder).

## Reading view and availability

The start page lists every source folder represented in the export. Click its disclosure
arrow or name (or use Enter/Space on the focused heading) to expand a complete table of dates,
senders, recipients, page counts and reading availability. Folders begin collapsed. Unprocessed
letters remain listed; retired records are excluded from browsing, search and previous/next
navigation. Public mode also refuses old direct links. In restricted mode, those links open
a labelled historical record with links to current letters containing its scans. Search folders, sender, recipient, date or
saved text to show matching letters in expanded folders; **Show all** restores the full catalogue.
The folder catalogue is not subject to the legacy search RPC's 100-result cap.

Folder tables, accessible letter-link labels, letter headings and the details panel prefer
staff catalogue names, then the saved normalized sender, recipient, attributed author and date. Dates use the export's
ISO form (`YYYY-MM-DD`, `YYYY-MM` or `YYYY`) without adding precision. If a normalized value
is missing or blank, the original reading is displayed. Existing uncertainty and filename-hint
labels remain visible. Original spellings/date wording and evidence remain available under
**Metadata evidence** (plus technical provenance in restricted mode); the source transcription is displayed verbatim.
Other metadata retains its original reading with a separate normalized value where available.
Standard catalogue names come from explicitly enabled authority aliases in the local store.
They change presentation/search only: no person IDs are assigned to readings and no attribution
or transcription is approved. Conflicting aliases remain unresolved. Filename-based names retain
**Filename hint · unverified**, and inferred readings remain labelled. Original metadata and
the catalogue label's name/basis remain in the evidence panel; internal authority sources are
restricted to staff mode. See [review.md](../../docs/review.md#standard-catalogue-names).

Within each folder, letters run oldest first, using supported normalized document dates.
Partial dates retain year/month precision and sort before more specific dates with the same
prefix; equal dates use the stable archival ID as a deterministic tie-breaker. This display
order does not establish the sequence of overlapping partial dates. When there is no document
date, a valid filename date can position a letter and is explicitly labelled as an unverified
hint. Ambiguous/unsupported document dates and undated records follow dated records; filename
hints never override an ambiguous document date. Folder membership comes from the export,
not live Drive folder discovery; empty folders without letters are not in that export.

A separate, revision-bound staff catalogue-date confirmation can place an abbreviated date
such as `Aug 7 - '99` at `1899-08-07`. The viewer labels it **Catalogue date confirmed**.
This does not rewrite the source date or relax automatic relationship chronology. A later
date/text correction or new service revision invalidates that confirmation.

For this catalogue update, replace **both Code.gs and Viewer.html**, preserve the configured
IDs, and update the existing deployment version. Also replace the contents of the existing
viewer JSON file with the refreshed local export, preserving its Drive ID. The prepared copy
is `local/viewer-deployment/Correspondence_viewer.json`. Code changes alone remove retired
rows; the refreshed JSON supplies the standard names and confirmed catalogue date. Neither
publication nor deployment is performed by preparing these local files.

**Read letter** opens one complete letter at `…/exec?letter=ltr_…`, independent of names/dates.
An interpretive summary appears above all its source pages. Each page pairs its original scan
on the left with its own source-language transcription on the right, matched by image ID in
exported scan order. The transcription has a subtle paper background and left accent. On desktop,
both panels have equal width and the loaded scan's proportions; long text scrolls inside its
keyboard-focusable panel, preserving every line, annotation and optional translation. While
loading or unavailable, scans reserve a portrait-shaped slot. On narrow screens each pair stacks
scan then transcription, and the text flows to its full height.

Sender, recipient, date, place, addresses, affiliations, language and other saved metadata are
shown below all pages, followed by review states, separate notes and correspondence connections.
Evidence remains in a collapsed panel. Raw partial responses and technical provenance are
available only in restricted mode.
**Previous letter** and **Next letter** at both top and bottom follow the complete folder order,
including when opened from search. They stop at folder boundaries. **All folders** returns to
the catalogue with that letter's folder expanded (`…/exec?folder=…`).

Proposed, confirmed, rejected and unresolved connections have distinct labels. Incoming
confirmed replies and outgoing predecessors use the same stable-ID links. Earlier decisions
whose evidence changed remain visible with an explicit review warning.

The view distinguishes absent transcription, missing local scan, missing Drive mapping,
trashed Drive scan, inaccessible image, changed content, and display-size limits. Google may
hide whether an inaccessible Drive ID exists; that case is honestly reported as inaccessible
or removed, rather than falsely asserting a missing scan. Image errors leave text visible.
Reload after fixing access/mappings.

The server pins the export version between text and image requests. Changed exports require
a reload, and changed image hashes require mapping review. No public image host is used:
server-read original JPEG bytes are returned as data URLs. Downloads are sequential and
scan slots preserve manifest order. Historical text is assigned through `textContent`;
template parameters use escaped printing. No source text is evaluated as HTML.

## Limits and offline verification

This minimal version rereads the export on each RPC. Maximum export: 10 MiB; image: 12 MiB;
sum of planned image bytes per letter: 24 MiB. The folder catalogue and its search return all
matching rows within that export; full page text/images load only when opening a letter.
The older `searchLetters` RPC retains its 100-result limit and limitation flag for compatibility.
Large collections will need partitioned viewer exports later.
These bounds do not establish Apps Script response/runtime capacity for every deployment.

Public mode allows a shared budget of 120 page/RPC requests and 60 image requests per minute,
checked before Drive reads. A script lock serializes the counter updates; contention/service
errors refuse the request. The counters live in script cache and can reset on eviction, so
this is best-effort load shedding, not a hard quota or protection against a determined attack.
All visitors share the budget, including legitimate readers; blocked requests still consume
some Apps Script resources. No trustworthy anonymous visitor identity or IP limit is assumed.
Heavy traffic can exhaust the owner's quotas and make the site unavailable. Ten thousand
letters or sustained public traffic calls for a static publication/CDN design, not just larger
limits here. See Google's [quotas](https://developers.google.com/apps-script/guides/services/quotas)
and [cache behavior](https://developers.google.com/apps-script/reference/cache/cache).

```powershell
node --test apps_script/viewer/test_viewer.cjs
```

Tests run the real server functions against synthetic Drive objects, and the actual browser
script against a small DOM/RPC adapter. They cover complete folder lists, conservative chronology,
search, navigation boundaries, matching each scan to its text, image-driven panel proportions,
escaping, missing mappings/scans, folder lookup, duplicate/unsafe paths, explicit-mapping
priority, revoked access, hash changes, limits, relationship labels and
text surviving image failures. Public-mode tests also cover filtering across every RPC,
search leakage, retired IDs, private connection targets, shared throttling, cache failures,
safe export errors and rendering images without Drive links.
No authenticated Drive calls occur. After installation, verify anonymous reading in a
signed-out window, unavailable retired IDs, native template rendering and image latency.
Offline tests cannot prove deployed permissions or Google quota capacity.
