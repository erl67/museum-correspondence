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
and Drive per-letter publication use active letters. Use the website project's publication
workflow to prepare the files for public reading.
A status report is generated even when a complete reading is unavailable.

The viewer bundle includes `processed_at` from the latest recorded attempt end for each letter,
including failed and incomplete readings. `transcribed_at` records the saved time of a current
complete reading. Refresh existing data with `export` to pick up the new
field from the saved journal without making a transcription request.

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

The public catalogue is [ericlaslo.com/birds/letters](https://ericlaslo.com/birds/letters).
Direct letter links use `https://ericlaslo.com/letter/<archival-id>`.

1. Add and transcribe scans in `G:\My Drive\Correspondence`. The collection store retains the
   results and the program refreshes `local/full-exports` and the enabled working copies on Drive.
2. Refresh the public mirror through the website project using the current scans and reading
   outputs. The current local reading bundle is `local/full-exports/viewer.json`, with a
   working copy at `G:\My Drive\Correspondence\Correspondence_viewer.json`. Prepared files in
   `local/viewer-deployment` and archived exports are snapshots.
3. After the website mirror is updated, open the public catalogue and the updated letter.
   Verify that the expected text and scan pages are present.

The Python commands refresh local and Drive files. Updating the website mirror is a separate
step owned by the website project. Google Drive remains the working collection. The public
reader serves the mirrored files from the website, without Apps Script or Drive file IDs.

## Publication errors and recovery

The store records ownership hashes for published files. An unrelated or edited file at a
managed destination blocks replacement, so preserve it separately and resolve the collision
before retrying. Superseded owned Drive reports are archived into the store before removal.
Only exact managed paths are excluded from later scan discovery.
Copies that already match the regenerated content keep their existing Drive files.

Results are durable before export begins. Local exports are written before publication, so
Drive being unavailable or an output collision does not lose the saved reading. Restore the
destination and run the `export` command again. Do not rerun transcription merely to recreate
a text file or viewer bundle. Drive for desktop handles synchronization of working copies.
Refresh the public mirror separately after recovering the current outputs.
