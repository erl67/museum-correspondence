# Read-only correspondence viewer

Files: `Code.gs`, `Viewer.html`, `appsscript.json`. Node tests and this README are not Apps
Script source. The viewer requires no Gemini credentials, no Python runtime, and no
transcription-service requests. It reads an explicitly supplied `viewer.json` export and
the reader's accessible mapped scans.

Nothing was uploaded or deployed during implementation. These installation steps are for
the maintaining staff member's later authorized setup.

## Prepare data locally

1. Run Python `inventory`, then any authorized transcription/review work.
2. Run `match` and `export`. Unprocessed records can be displayed without transcriptions.
   For the Drive collection, `export --publish-text` also saves
   `Correspondence_viewer.json` at the scan root, alongside human-readable text reports.
   The viewer continues to consume JSON internally; staff do not need to open that file.
3. Use `images.csv` to create an image-ID mapping under ignored `local/drive-map.json`.
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

Mappings bind to exact inventoried image hashes. The viewer rechecks Drive image bytes against
that hash before display. The mapping file is external to transcription identity; editing it
never triggers a transcription request. Supply `--mapping` whenever regenerating the mapped
viewer bundle. Ordinary exports without that option explicitly show missing mappings.

## Installation and access

1. Create a separate Apps Script project. Add Code.gs and an HTML file named **Viewer**.
2. Show the manifest in Project Settings; copy `appsscript.json`.
3. Set `ACCESS_FILE_ID` in Code.gs to the institution's existing collection access-gate file
   (for example the already-shared master institutional workbook). It is an authorization
   gate only; this collection does not need a catalogue spreadsheet.
4. Use the synced `Correspondence_viewer.json` created by `export --publish-text`, or upload
   the local `viewer.json` through the institution's approved Drive workflow, and set
   `EXPORT_FILE_ID` to that file's real Drive ID. Verify the synced file ID after updates.
   No Drive API uploader or sharing modification exists in this project.
5. Use **Execute as: User accessing the web app** (`USER_ACCESSING`).
   The manifest's `ANYONE` audience means signed-in Google accounts, not anonymous scan sharing.
   The reader must pass the configured gate and independently have read access to the export
   and each scan. Workspace policy may further restrict eligible deployment audiences.
6. Deploy a versioned web app. Updates require a new deployment version; saving code alone
   does not update an existing `/exec` deployment.

The scope is only `drive.readonly`. Every page/export/image RPC rechecks access under the
accessing account. No credentials appear in browser code. No ACLs, sharing links or public
visibility are changed. Gate access does not grant access to other files. Do not switch to
owner execution to bypass a reader's restrictions.

Official references: [web-app permissions](https://developers.google.com/apps-script/guides/web#permissions),
[manifest settings](https://developers.google.com/apps-script/manifest/web-app-api-executable),
[escaped templates](https://developers.google.com/apps-script/guides/html/templates),
[Drive file access](https://developers.google.com/apps-script/reference/drive/file).

## Reading view and availability

Search sender, recipient, date or saved text. Links use `…/exec?letter=ltr_…`, independent of
names/dates. Each letter displays source-language text beside ordered original scans,
separate notes/optional translations, review states, summary and correspondence connections.
Provenance/evidence is in a collapsed details panel, away from the main reading.

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
sum of planned image bytes per letter: 24 MiB. Search returns at most 100 results with a
clear limitation notice. Large collections will need partitioned viewer exports later.
These bounds do not establish Apps Script response/runtime capacity for every deployment.

```powershell
node --test apps_script/viewer/test_viewer.cjs
```

Tests run the real server functions against synthetic Drive objects, and the actual browser
script against a small DOM/RPC adapter. They cover escaping, order, missing mappings/scans,
revoked access, hash changes, limits, relationship labels and text surviving image failures.
No authenticated Drive calls occur. After authorized installation, verify with an allowed
reader and a denied reader; check native template rendering, image payload size/latency,
Google authorization and access revocation. Offline tests cannot prove deployed permissions.
