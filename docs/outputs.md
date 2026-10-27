# Outputs and automatic updates

The collection store is the saved record of inventory, results and changes. Reports and
viewer JSON are generated from it. For the Drive collection, use `local/full-collection`
as the store and `local/full-exports` as the output directory on every export/transcription
command. The default `local/collection` and `local/exports` belong to the fixture workflow.
The program does not remember the last `--output` directory.

## Local files

| File beneath `local/full-exports` | Contents |
| --- | --- |
| `readable/<folder>/<letter filename>.txt` | One readable letter report with ordered page text, annotations, catalogue details and notes |
| `combined.txt` | All active letters' readable reports together |
| `letters/<ltr_ID>.txt` | Diagnostic report with IDs, request provenance and revision details |
| `catalogue.csv` | One row per letter, including status, names, date, summary and readable report path |
| `images.csv` | Ordered image IDs, current paths, source hashes and any supplied Drive mappings |
| `evidence.csv`, `entities.csv` | Metadata quotations and extracted people, places, subjects and other entities |
| `relationships.csv`, `unresolved.csv` | Saved connection decisions/candidates and unresolved references |
| `records.json` | Current records, selected results, review history, people and relationships |
| `viewer.json` | Reading bundle: text, summaries, metadata, ordered scans, availability, connections and provenance |

Local per-letter reports and structured exports also retain retired records. Combined text
and Drive per-letter publication use active letters; the public viewer exposes active letters.
A status report is generated even when a complete reading is unavailable.

Current generated files are rebuilt, not edited in place as authoritative records. Make
lasting text/metadata changes through the [review workflow](review.md), then export. Local
export files may be overwritten; obsolete local filenames are not automatically removed.

## Enable copies beside the scans

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" export --output "local/full-exports" --publish-text
```

This creates local exports first, then saves the following beneath the input root recorded
in the store (`G:\My Drive\Correspondence` for this collection):

| Published path | Contents |
| --- | --- |
| `<folder>/<letter filename>.txt` | Individual letter report, using the letter stem without the page suffix |
| `<folder>/<folder>_transcriptions.txt` | Combined reports for that output folder |
| `Correspondence_transcriptions.txt` | All active letter reports |
| `Correspondence_viewer.json` | Exact byte copy of the freshly generated local `viewer.json` |

Publication is remembered in the store's `text_publication` journal events. Later commands
that refresh outputs also publish, even when `--publish-text` is omitted. A different
`--output` directory changes the local destination, but published copies still go to the
same recorded scan root. There is currently no command-line switch to disable remembered
publication for that store.

## When files refresh

| Command/action | Local exports | Published copies, when enabled |
| --- | --- | --- |
| `inventory` | After saving the inventory | Refreshed from the saved state |
| `transcribe --letter`, `--all` or `--pending` | After each returned result, including reuse, and at normal batch completion | Refreshed at the same points |
| `export` | Regenerated from saved records, with no transcription requests | Refreshed at the same time |
| `review`, `match`, `reconcile-paths` | No immediate refresh; run `export` afterward | Updated by that later export |
| `show`, `dry-run` | No changes | No changes |
| Edit a profile/configuration file | No changes to saved readings or exports by itself | No changes |

Rerunning one letter regenerates the collection-wide files using that letter's new current
result and the other letters' saved results. During a batch, outputs can contain a mixture
of already refreshed letters and letters awaiting processing. There is no background watcher
or automatic polling of local changes. A hard interruption can leave outputs behind the
saved store; use `export` to bring them up to date.

`match` recalculates correspondence candidates. Export includes the saved matching state;
it does not run a new search for candidates. After changed readings or references, run:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" match
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" export --output "local/full-exports"
```

## How the website receives new readings

The normal path is: saved result → local `viewer.json` → published
`Correspondence_viewer.json` → Drive for desktop synchronization → the configured viewer.

Apps Script's `EXPORT_FILE_ID` identifies the Drive JSON file to read. The filename alone
does not select it. Once Drive has synced the updated contents of that same file, subsequent
viewer requests read the new bundle. Reload [cmbirds.org/letters](https://cmbirds.org/letters)
to refresh an already open catalogue or letter. The page does not continuously refresh itself.
If data changes between a letter request and an image request, the viewer asks for a reload
so text and scans come from a consistent export.

A new reading, summary, name, date or relationship in the same JSON file does not require
redeployment. Changed viewer source/settings do require a new deployment version. Verify
that Drive retained the configured file ID after synchronization. If the JSON is replaced by
a different Drive file, update `EXPORT_FILE_ID` and redeploy; in restricted mode also check
`ACCESS_FILE_ID` if it uses that same file. See the [viewer setup guide](../apps_script/viewer/README.md).

The automatic process does **not** refresh `local/viewer-deployment/Correspondence_viewer.json`,
archived exports or other manually prepared copies. The current local source is
`local/full-exports/viewer.json`; its published copy is at the scan root. Use those current
files when maintaining the viewer.

The configured scan-root lookup resolves images by exported relative paths, without requiring
stored per-image Drive mappings. For installations using explicit mappings instead, pass
`--mapping "local/drive-map.json"` to the final `export`. Mappings are not remembered;
inventory/transcription refreshes produce bundles without them. Perform a final mapped
export before relying on a mapping-only viewer. Publication copies that mapped bundle too.

## Publication errors and recovery

The store records ownership hashes for published files. An unrelated or edited file at a
managed destination blocks replacement, so preserve it separately and resolve the collision
before retrying. Superseded owned Drive reports are archived into the store before removal.
Only exact managed paths are excluded from later scan discovery.

Results are durable before export begins. Local exports are written before publication, so
Drive being unavailable or an output collision does not lose the saved reading. Restore the
destination and run the `export` command again. Do not rerun transcription merely to recreate
a text file or viewer bundle. The program writes through the local Drive mount; Drive for
desktop handles remote synchronization, which must finish before the website can use it.
