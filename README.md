# Museum correspondence

This application inventories scanned historical letters, prepares page-linked transcriptions,
and builds a searchable local catalogue. Letters may be filed under different correspondents;
local relationship matching searches the whole saved collection.

Original scans are never renamed, moved, corrected, or overwritten. Filename names and dates
are provisional hints. The document reading, normalized search values, and staff corrections
remain separate. **A complete service response is not a verified historical transcription.**

The first version provides a Python command line and a small read-only Google Apps Script
viewer. No source spreadsheet is needed. The six tracked JPEGs in `test/inputs` form two
provisional records with two and four ordered pages. They are source fixtures, not verified
reference transcriptions, and do not establish a reply pair.

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

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" inventory --input "G:\My Drive\Correspondance" --output "local/full-exports"
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
The program reads that file only when explicitly passed; it also supports `GEMINI_API_KEY`
or `GOOGLE_API_KEY` in the process environment. Never commit credentials.

```powershell
Copy-Item .env.example .env
# Edit .env locally; do not paste its contents into a report or commit.
.\.venv\Scripts\python.exe -m correspondence transcribe --letter "LETTER_ID_FROM_INVENTORY" --env-file .env
.\.venv\Scripts\python.exe -m correspondence transcribe --all --env-file .env
```

Defaults are `gemini-3.5-flash-lite`, temperature `1.0`, high thinking. There is no automatic
provider/model substitution. The local allocation is deliberately conservative: 2 starts/minute
and 20 attempts/day, including retries. **It is not an additional provider allowance.**
The egg-slip application may share the same Google project quota; coordinate allocations.
See [configuration](docs/configuration.md) before using the full collection.

Repeat the same command to continue. Exactly matching complete results no more than 48 hours
old are reused without a request. Older results remain archived but a transcription rerun may
spend again. Use `export` to read or regenerate older work for free. `--fresh` explicitly
requests another transcription and retains previous revisions. Interrupted requests with an
unknown service outcome require inspection and explicit `--retry-interrupted`.

## Read, review, and connect letters

Default outputs:

| File | Use |
| --- | --- |
| `local/exports/letters/ltr_….txt` | Readable UTF-8 report with source order, status, metadata/evidence, page boundaries and separate notes |
| `local/exports/combined.txt` | Combined readable reports |
| `local/exports/catalogue.csv` | One row per letter, including blocked/unprocessed/failed/retired records |
| `images.csv`, `evidence.csv`, `entities.csv` | Related tables with stable IDs; original paths, evidence, and identifiers |
| `relationships.csv`, `unresolved.csv` | Proposed/confirmed/rejected links and references to unidentified letters |
| `records.json`, `viewer.json` | Structured export and viewer bundle |
| `local/collection/journal.jsonl`, `blobs/` | Durable history, original responses, request context and submitted image bytes; back these up |

Open CSVs using Excel's **Data → From Text/CSV** and set identifier columns to **Text** to
preserve leading zeros. Formula-like cells are prefixed with an apostrophe in CSV only.
The canonical transcription and plain-text report are unchanged.

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

Reply candidates retain evidence and alternatives. They are never confirmed automatically.
A reply link points **from the reply to the earlier letter**. Staff can confirm or reject
individual links; rematching preserves those decisions. Missing referenced letters stay
unresolved. Shared subject matter alone does not establish a reply.

## Viewer and verification

The [Apps Script viewer](apps_script/viewer/README.md) searches saved text and metadata, displays
ordered scans beside transcriptions, and navigates correspondence links. It makes no
transcription-service calls. It needs a deliberate Drive mapping and the institution's existing
access-gate configuration. Nothing is uploaded, deployed, made public, or shared by the Python
application.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s test -t . -v
node --test apps_script/viewer/test_viewer.cjs
```

These are software tests using synthetic readings and the six source-image inventory.
They do not measure historical reading accuracy. Authenticated Drive access and actual Gemini
account/model availability still need checking in their respective authorized workflows.

More detail: [configuration](docs/configuration.md), [transcription conventions](docs/transcription.md),
[schema and identifiers](docs/schema.md), [review](docs/review.md),
[handwriting profiles](docs/handwriting.md), [relationships](docs/relationships.md),
[testing](docs/testing.md), [project handoff](docs/PROJECT_HANDOFF.md).
