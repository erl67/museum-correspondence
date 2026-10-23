# Read-only correspondence viewer

Files: `Code.gs`, `Viewer.html`, `appsscript.json`. Node tests and this README are not Apps
Script source. The viewer requires no Gemini credentials, no Python runtime, and no
transcription-service requests. It reads an explicitly supplied `viewer.json` export and
the reader's accessible scans from a configured collection folder or explicit image mappings.

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

The three settings in this checkout's Code.gs are prefilled with the collection IDs explicitly
supplied by the user. The viewer JSON file is also used as the access-check file. Verify those
settings when copying the viewer to another collection; Drive permissions still govern access.

1. Create a separate Apps Script project. Add Code.gs and an HTML file named **Viewer**.
2. Show the manifest in Project Settings; copy `appsscript.json`.
3. Set `ACCESS_FILE_ID` in Code.gs to the institution's existing collection access-gate file
   (for example the already-shared master institutional workbook). It is an authorization
   gate only; this collection does not need a catalogue spreadsheet.
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
6. Use **Execute as: User accessing the web app** (`USER_ACCESSING`).
   The manifest's `ANYONE` audience means signed-in Google accounts, not anonymous scan sharing.
   The reader must pass the configured gate and independently have read access to the export
   and each scan. Workspace policy may further restrict eligible deployment audiences.
7. Deploy a versioned web app. Updates require a new deployment version; saving code alone
   does not update an existing `/exec` deployment.

For an existing installation, copy the updated **Code.gs and Viewer.html** into Apps Script,
preserving your existing access/export file IDs, and set the new collection folder ID.
Save, then **Deploy → Manage deployments → Edit (pencil) → Version: New version → Deploy**.
Reload the viewer. Setting this folder does not require replacing the JSON export.

Folder lookup is read-only and uses the signed-in reader's access. It walks only the exact
exported path under the configured root, including nested subfolders; it does not search the
whole Drive or follow shortcuts. Duplicate visible folder/file names are refused, with a
request for an explicit mapping. A path not visible to the reader is reported as unavailable,
without asserting deletion. Renamed or byte-changed scans require correcting the export/path
or mapping. Explicit image mappings take priority and never fall back after a mapped-file error.
Both modes enforce the same JPEG type, image/letter byte limits and SHA-256 verification.
Folder lookups occur only when loading a page image, after the access gate and export token
checks. They do not modify the export, archive IDs, source files or sharing.

The scope is only `drive.readonly`. Every page/export/image RPC rechecks access under the
accessing account. No credentials appear in browser code. No ACLs, sharing links or public
visibility are changed. Gate access does not grant access to other files. Do not switch to
owner execution to bypass a reader's restrictions.

Official references: [web-app permissions](https://developers.google.com/apps-script/guides/web#permissions),
[manifest settings](https://developers.google.com/apps-script/manifest/web-app-api-executable),
[escaped templates](https://developers.google.com/apps-script/guides/html/templates),
[Drive file access](https://developers.google.com/apps-script/reference/drive/file).
Folder lookup uses the read-only [Drive Folder methods](https://developers.google.com/apps-script/reference/drive/folder).

## Reading view and availability

The start page lists every source folder represented in the export. Click its disclosure
arrow or name (or use Enter/Space on the focused heading) to expand a complete table of dates,
senders, recipients, page counts and reading availability. Folders begin collapsed. Unprocessed
letters remain listed; retired records are labelled. Search folders, sender, recipient, date or
saved text to show matching letters in expanded folders; **Show all** restores the full catalogue.
The folder catalogue is not subject to the legacy search RPC's 100-result cap.

Folder tables, accessible letter-link labels, letter headings and the details panel prefer
the saved normalized sender, recipient, attributed author and date. Dates use the export's
ISO form (`YYYY-MM-DD`, `YYYY-MM` or `YYYY`) without adding precision. If a normalized value
is missing or blank, the original reading is displayed. Existing uncertainty and filename-hint
labels remain visible. Original spellings/date wording and evidence remain available under
**Metadata evidence and technical provenance**; the source transcription is displayed verbatim.
Other metadata retains its original reading with a separate normalized value where available.
This presentation change does not merge people, invent names/dates, approve metadata, or change
chronological eligibility. Different saved normalized names still require staff identity review
to reconcile; normalization is a saved proposal rather than proof of historical identity.

Within each folder, letters run oldest first, using supported normalized document dates.
Partial dates retain year/month precision and sort before more specific dates with the same
prefix; equal dates use the stable archival ID as a deterministic tie-breaker. This display
order does not establish the sequence of overlapping partial dates. When there is no document
date, a valid filename date can position a letter and is explicitly labelled as an unverified
hint. Ambiguous/unsupported document dates and undated records follow dated records; filename
hints never override an ambiguous document date. Folder membership comes from the export,
not live Drive folder discovery; empty folders without letters are not in that export.

**Read letter** opens one complete letter at `…/exec?letter=ltr_…`, independent of names/dates.
An interpretive summary appears above all its source pages. Each page pairs its original scan
on the left with its own source-language transcription on the right, matched by image ID in
exported scan order. The transcription has a subtle paper background and left accent. On desktop,
both panels have equal width and the loaded scan's proportions; long text scrolls inside its
keyboard-focusable panel, preserving every line, annotation and optional translation. While
loading or unavailable, scans reserve a portrait-shaped slot. On narrow screens each pair stacks
scan then transcription, and the text flows to its full height.

Sender, recipient, date, place, addresses, affiliations, language and other saved metadata are
shown below all pages, followed by review states, separate notes, partial responses and
correspondence connections. Evidence and technical provenance remain in a collapsed panel.
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
authenticated original JPEG bytes are returned as data URLs. Downloads are sequential and
scan slots preserve manifest order. Historical text is assigned through `textContent`;
template parameters use escaped printing. No source text is evaluated as HTML.

## Limits and offline verification

This minimal version rereads the export on each RPC. Maximum export: 10 MiB; image: 12 MiB;
sum of planned image bytes per letter: 24 MiB. The folder catalogue and its search return all
matching rows within that export; full page text/images load only when opening a letter.
The older `searchLetters` RPC retains its 100-result limit and limitation flag for compatibility.
Large collections will need partitioned viewer exports later.
These bounds do not establish Apps Script response/runtime capacity for every deployment.

```powershell
node --test apps_script/viewer/test_viewer.cjs
```

Tests run the real server functions against synthetic Drive objects, and the actual browser
script against a small DOM/RPC adapter. They cover complete folder lists, conservative chronology,
search, navigation boundaries, matching each scan to its text, image-driven panel proportions,
escaping, missing mappings/scans, folder lookup, duplicate/unsafe paths, explicit-mapping
priority, revoked access, hash changes, limits, relationship labels and
text surviving image failures.
No authenticated Drive calls occur. After authorized installation, verify with an allowed
reader and a denied reader; check native template rendering, image payload size/latency,
Google authorization and access revocation. Offline tests cannot prove deployed permissions.
