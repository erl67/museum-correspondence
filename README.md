# Museum correspondence

This application inventories scanned historical letters, prepares page-linked transcriptions,
and builds a searchable local catalogue. Letters may be filed under different correspondents;
local relationship matching searches the whole saved collection.

Routine commands leave source scans unchanged. An explicitly authorized naming migration
can rename files with byte verification and identity reconciliation. Filename names and dates
are provisional hints. The document reading, normalized search values, and staff corrections
remain separate. **A complete service response is not a verified historical transcription.**

The first version provides a Python command line and a small read-only Google Apps Script
viewer. No source spreadsheet is needed. The current `test/inputs` contains 25 tracked JPEGs
in two correspondent folders, forming eight provisional letters with 2, 4, 2, 4, 2, 7, 3,
and 1 ordered pages. The original six scans remain byte-identical after their external move
into `Shufeldt, Percy` and relabelling from A–D to numeric page suffixes. These are source
fixtures, not verified reference transcriptions, and do not establish confirmed reply links.

## Scan filenames

Use `Sender-Recipient-YYYYMMDD_01.jpg`, for example
`Shufeldt,P-Todd-18990807_01.jpg`. Number every scan, including single-page letters,
with at least two digits. Keep the same letter stem and increase `_01`, `_02`, etc.
Use `YYYYMM`, `YYYY`, or `undated` when the date is incomplete; use `-a`, `-b`
before the page suffix for separate letters with the same sender, recipient and date.
See the [naming guide](docs/naming.md) for examples and migration safeguards.

The Drive collection was migrated on 2026-10-21: 44 scans, 21 saved readings and 25
current Drive outputs. Legacy filenames remain supported, including the unchanged
tracked test scans. Individual TXT reports use the compact date and omit the page suffix.

## Install on Windows

Use Python **3.12 or newer**. From PowerShell:

```powershell
Set-Location "C:\Users\x5769\Documents\GitHub\museum-correspondence"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m correspondence --help
```

The sibling egg-slip checkout is not needed at runtime. Node.js is needed only for viewer
tests. There is no database server or web service to run locally.

## Start with the collection, without service requests

```powershell
.\.venv\Scripts\python.exe -m correspondence dry-run --input "test/inputs"
.\.venv\Scripts\python.exe -m correspondence inventory --input "test/inputs"
.\.venv\Scripts\python.exe -m correspondence show
```

`dry-run` reads and decodes images, checks grouping, hashes, and whole-letter payload sizes.
It needs no credentials and creates no reports, journals, quota reservations, or output folders.
`inventory` creates the persistent local records and reports under `local/`.

For the full collection, use its actual scan directory and a separate store:

For step-by-step Windows instructions covering both Drive subfolders and `.txt` output,
see [Transcribe the Drive collection](docs/drive-transcription.md).

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" inventory --input "G:\My Drive\Correspondence" --output "local/full-exports"
```

Check that the selected root contains the intended scans. Every unsupported/unreadable file
remains visible. Files in different folders are not merged just because the names/dates match.
Ambiguous groups require a [reviewed grouping override](docs/review.md) before transcription.

## Transcribe when ready

Only `transcribe` can contact Gemini. It sends the selected letter's **complete ordered image
set**, filename/folder hints, and any explicitly selected handwriting context to Google.
Requests may incur costs. Confirm the institution's collection-data handling arrangements and
account allocation before choosing to run them. No live requests were made while implementing
this version.

Copy `.env.example` to `.env` and enter your own key locally. The example contains no key.
If `.env` already exists, keep it rather than replacing it with the empty example.
The program reads that file only when explicitly passed; it also supports `GEMINI_API_KEY`
or `GOOGLE_API_KEY` in the process environment. Never commit credentials.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env locally; do not paste its contents into a report or commit.
.\.venv\Scripts\python.exe -m correspondence transcribe --letter "LETTER_ID_FROM_INVENTORY" --env-file .env
.\.venv\Scripts\python.exe -m correspondence transcribe --all --env-file .env
```

These commands use the default fixture store. For the Drive collection, use the commands
in the [Drive guide](docs/drive-transcription.md), including `--store "local/full-collection"`
and `--output "local/full-exports"` on each transcription/export command. The output path
from `inventory` is not remembered by later commands.

Defaults are `gemini-3.5-flash-lite`, temperature `1.0`, high thinking. There is no automatic
provider/model substitution. The local allocation is 2 starts/minute
and 100 attempts/day, including retries. **It is not an additional provider allowance.**
The egg-slip application may share the same Google project quota; coordinate allocations.
See [configuration](docs/configuration.md) before using the full collection.

Repeat the same command to continue. Exactly matching complete results no more than 48 hours
old are reused without a request. Older results remain archived but a transcription rerun may
spend again. Use `export` to read or regenerate older work for free. `--fresh` explicitly
requests another transcription and retains previous revisions. Interrupted requests with an
unknown service outcome require inspection and explicit `--retry-interrupted`.
Use `transcribe --pending` to process only letters without a current complete result,
regardless of cache age. This is the usual continuation command after exporting saved work.

## Read, review, and connect letters

Default outputs:

| File | Use |
| --- | --- |
| `local/exports/readable/<source folder>/<letter filename>.txt` | Staff report: ordered letter text, annotations, separate plain-English notes and review status; no closing AI disclaimer or JSON sections |
| `local/exports/combined.txt` | All active letter readings in one text file |
| `local/exports/letters/ltr_….txt` | Detailed diagnostic report with archival IDs, JSON evidence and technical provenance |
| `local/exports/catalogue.csv` | One row per letter, including blocked/unprocessed/failed/retired records |
| `images.csv`, `evidence.csv`, `entities.csv` | Related tables with stable IDs; current scan paths, evidence, and identifiers |
| `relationships.csv`, `unresolved.csv` | Proposed/confirmed/rejected links and references to unidentified letters |
| `records.json`, `viewer.json` | Structured export and viewer bundle |
| `local/collection/journal.jsonl`, `blobs/` | Durable history, original responses, request context and submitted image bytes; back these up |

Open CSVs using Excel's **Data → From Text/CSV** and set identifier columns to **Text** to
preserve leading zeros. Formula-like cells are prefixed with an apostrophe in CSV only.
The canonical transcription and plain-text report are unchanged.

To also save named text files beside the original scans on Drive, enable publication once
for that store:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" export --output "local/full-exports" --publish-text
```

This writes `<letter filename>.txt` in each scan folder, a `<folder>_transcriptions.txt`
combined file in each correspondent folder, and `Correspondence_transcriptions.txt` at the
collection root. It also writes `Correspondence_viewer.json` for the existing web viewer;
staff read the text files. Later `inventory`, `transcribe` and `export` commands for that
store refresh these copies automatically. Drive for desktop syncs these generated files.
Unowned files, edited reports and scans are never overwritten. Only exact managed output
paths are excluded from later scan discovery. See the [Drive guide](docs/drive-transcription.md).
Superseded managed Drive reports are archived in the local store before removal; edited
reports block replacement or removal. Earlier paths remain in historical provenance.

```powershell
.\.venv\Scripts\python.exe -m correspondence show --letter "LETTER_ID_FROM_INVENTORY"
.\.venv\Scripts\python.exe -m correspondence review --file "local/review.json"
.\.venv\Scripts\python.exe -m correspondence match
.\.venv\Scripts\python.exe -m correspondence export
```

Review JSON specifies the saved revision, corrected fields/text, reason/source and optional
reviewer. Corrections are append-only. Metadata approval, word-for-word transcription approval,
grouping and relationship review have separate states. New source pages or a new service
revision leave prior corrections in history and require deliberate rebasing.
Changing page text returns transcription, metadata and relationship review to `in_progress`;
changing metadata returns metadata and relationship review to `in_progress`, unless the same
review explicitly sets their status. Moving source files outside this program leaves their
old inventory paths marked missing; it never silently merges records by matching hashes.

Reply candidates retain evidence and alternatives. They are never confirmed automatically.
A reply link points **from the reply to the earlier letter**. Staff can confirm or reject
individual links; rematching preserves those decisions. Missing referenced letters stay
unresolved. Shared subject matter alone does not establish a reply.

## Viewer and verification

The [Apps Script viewer](apps_script/viewer/README.md) starts with expandable letter folders,
each listing dates, senders and recipients in chronological order. Search filters the folders
by saved text and metadata. Lists, letter headings and details prefer saved normalized names
and dates; original readings remain in the evidence panel. Open a letter for its summary,
then each original scan on the left and its matching transcription on the right.
Letter details and connections follow the pages;
previous/next letter and folder navigation appear at both top and bottom. It makes no
transcription-service calls. Configure the collection's Drive folder to find scans by their
exported paths, or supply explicit image mappings, plus the institution's access-gate file.
Every displayed scan is checked against its exported size and SHA-256. Nothing is uploaded,
deployed, made public, or shared by the Python
application through the Drive API. Explicit `--publish-text` writes generated files into the
local Drive folder for Drive for desktop to sync; it does not change sharing or deploy a viewer.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s test -t . -v
node --test apps_script/viewer/test_viewer.cjs
```

These are software tests using synthetic readings and the current source-image inventory.
They do not measure historical reading accuracy. Authenticated Drive access and actual Gemini
account/model availability still need checking in their respective authorized workflows.

More detail: [configuration](docs/configuration.md), [transcription conventions](docs/transcription.md),
[schema and identifiers](docs/schema.md), [review](docs/review.md),
[handwriting profiles](docs/handwriting.md), [relationships](docs/relationships.md),
[testing](docs/testing.md), [project handoff](docs/PROJECT_HANDOFF.md).
