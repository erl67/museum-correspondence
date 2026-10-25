# Rerun existing correspondence after a prompt update

The 25 October 2026 update, `correspondence-1.1`, improves the reading instructions for
initials and correspondent identities, scientific/common bird names, difficult cursive,
and plain-text dates. It uses the store's approved names/aliases as candidates, with visible
evidence required. It does not alter existing readings or certify future ones as accurate.
Gemini 3.5 Flash-Lite, temperature 1.0, high thinking and original-resolution JPEGs remain
the defaults. Every attempt, including retries, still counts toward the allocation.

## Keep the existing store and archival IDs

Use `local/full-collection` for this Drive collection. It preserves the current 21 active
letters / 44 scans, two retired groups, grouping overrides, names, original responses and
review history. A new reading gets a new revision ID and fingerprint; the `ltr_...` letter
ID and `img_...` image IDs stay the same. Do not replace the store or change grouping/paths
just to rerun. Reviews bound to an earlier reading, including the August 7 catalogue-date
confirmation, require checking/rebasing against the new revision. Person authority records
continue to apply as candidates and catalogue labels.

The actual export folder is `local/full-exports`, not a root `local-exports` directory.
The pre-update snapshot is under `local/archives/20261025-before-prompt-1.1/`: current full
exports, the prepared viewer deployment, full collection store, quota/config/grouping files,
and code before this edit. A SHA-256 manifest checks the copies. The active paths are retained
so subsequent commands can refresh them. `local/exports` is the separate fixture collection;
it is not the production upload source. Archives and store data remain ignored by Git.

Preflight also reconciled the existing Drive viewer JSON with the publication ledger after
verifying it was byte-identical to both generated local copies and the backup. This appended
one ownership event only; source files, readings, reviews, inventory and quota were unchanged.
The archive's `publication-adoption.json` records it, and `readiness.json` records successful
offline preparation of all 21 letters. The 23 moved TXT files can be recreated safely.

## Reread the saved collection

Keep Drive for desktop available, then paste into PowerShell:

```powershell
Set-Location "C:\Users\x5769\Documents\GitHub\museum-correspondence"
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" transcribe --all --env-file .env --output "local/full-exports" --publish-text
```

This command sends images and reading context to Gemini and may incur charges. The changed
prompt/context makes old results ineligible for reuse, so `--fresh` is unnecessary for this
first rerun. Results are checkpointed and reports refreshed after each letter. Publication
was already enabled in this store: it also updates Drive reader files and the viewer JSON
as the batch proceeds, so readers can temporarily see a mixture of old and new revisions.

Do **not** use `--pending` to apply this update: it skips old complete readings regardless
of their prompt. If the batch stops, repeat the same `--all` command within 48 hours; matching
new complete results are reused. After that cache window, target the remaining letter IDs
with repeated `--letter` options to avoid paying to reread finished letters. Inspect unknown
interrupted attempts before adding `--retry-interrupted`, which accepts possible repeat charges.
`--fresh` always bypasses completed-cache reuse, so do not add it to a routine continuation.

No new inventory is needed for unchanged scans. The current root also contains `old/` text
archives and `analysis/` material, including a reference JPEG. Discovery walks all subfolders;
an `old` folder is not automatically excluded. Avoid running root-wide inventory/dry-run as
part of this rerun. Before adding future scans, review the discovery scope so supporting
material is not accidentally treated as new letters. Existing transcribe requests verify
every selected scan's bytes against the saved inventory before sending it.

Moving generated TXT files to `old/` does not remove saved transcriptions: the store holds
them. The rerun recreates the original managed TXT paths and leaves the manual archive alone.
It preserves unowned or staff-edited output files by refusing to overwrite them; resolve any
such error before continuing publication.

## Refresh and upload the viewer data

After the batch, review the revised reports against the images, particularly the flagged
Sutton and Percy passages. Do not assess improvement solely by counting uncertainty marks.
To regenerate all exports from the saved results without service requests:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" export --output "local/full-exports" --publish-text
```

The fresh upload source is `local/full-exports/viewer.json`. Its synced copy is
`G:\My Drive\Correspondence\Correspondence_viewer.json`. Do not upload the older JSON
in `local/viewer-deployment` or an archive; the normal export command does not refresh those.

The Drive **file ID** used by Apps Script's `EXPORT_FILE_ID` is separate from archival letter
IDs. Keep using the same Drive JSON file. Let Drive desktop finish syncing and compare its
file ID with the configured value. If uploading manually, select that existing JSON in Drive,
then **More → Manage versions → Upload new version**, choosing the fresh `viewer.json`.
Google documents this workflow in [Drive file versions](https://support.google.com/drive/answer/2409045).
Creating a separate file with the same filename does not select it in Apps Script.

No Apps Script code update/redeployment is needed for this prompt change or a new version of
the same JSON file. Reload [cmbirds.org/letters](https://cmbirds.org/letters) after sync/upload.
If the Drive file ID actually changes, update `EXPORT_FILE_ID` and redeploy the existing app;
also update `ACCESS_FILE_ID` if that file is used as the gate in restricted mode. Public mode
does not use that gate. Keep `SCAN_ROOT_FOLDER_ID` unchanged for the same scan folder.
Local export writes cannot guarantee Drive desktop's remote file identity, so check it rather
than assuming a filename proves it.
