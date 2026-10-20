# Transcribe the Drive collection on Windows

Use `G:\My Drive\Correspondence` as the input folder. The program searches its subfolders
automatically, so one run includes both correspondent folders. It currently accepts JPEG
files (`.jpg` and `.jpeg`). It groups pages into letters within each folder and writes one
UTF-8 `.txt` report per letter, with page boundaries, plus combined text files. Readable
reports show the actual letter text before plain-English catalogue details and review notes;
they contain no JSON sections.

## 1. Open PowerShell in the project folder

Open PowerShell and paste:

```powershell
Set-Location "C:\Users\x5769\Documents\GitHub\museum-correspondence"
```

Make sure Google Drive for desktop is running and you can open the scans in File Explorer
under `G:\My Drive\Correspondence`. Let Drive finish downloading them if necessary.
Leave the original scans and their names unchanged.

## 2. Check the installation

If `.venv` already exists, check that the program starts:

```powershell
.\.venv\Scripts\python.exe -m correspondence --help
```

For a new installation, install Python 3.12 or newer, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m correspondence --help
```

If an existing installation reports missing dependencies, run the `pip install` command
above. You do not need to activate the virtual environment or install Node.js to transcribe.

## 3. Set up the API key

Keep your existing `.env` file if it already contains your Gemini API key. If it is missing,
create it without overwriting an existing file:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

In Notepad, set `GEMINI_API_KEY=your_actual_key`, save, and close the file. Keep the key
private. The transcription commands below explicitly load this file.

The daily default is now 100 attempts, including retries. `local/config.json` is optional;
when used, pass `--config "local/config.json"` before the command. The local file created for
this collection contains `{"daily_limit": 100}`. Do not put that setting in `.env`.

## 4. Check both subfolders before transcribing

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" dry-run --input "G:\My Drive\Correspondence"
```

This reads the scans and checks page grouping, order and request size. It makes no Gemini
requests and writes no output. Check that both subfolders appear and that the listed pages
belong together in the correct order. `READY` means a letter passes the software checks;
it does not mean a person has confirmed its grouping or historical content.

Resolve any `BLOCKED` or grouping problems before proceeding. For ambiguous filenames or
page order, use a [reviewed grouping override](review.md), without renaming the scans.

Save the inventory:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" inventory --input "G:\My Drive\Correspondence" --output "local/full-exports"
```

This creates the collection records and initial reports locally. Reports at this stage say
that no complete transcription is available. `local/full-collection` is separate from the
default fixture store, `local/collection`. Keep using the same store for this collection.

## 5. Transcribe

This step sends the letter images to Google's Gemini service and may incur charges.
The configured default is `gemini-3.5-flash-lite`, temperature 1.0, high thinking.

For a first check, copy one `ltr_...` ID from the inventory output and replace
`LETTER_ID_FROM_INVENTORY` below with that entire ID:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" transcribe --letter "LETTER_ID_FROM_INVENTORY" --env-file .env --output "local/full-exports" --publish-text
```

Read that letter's report and compare it with the scans. To process the unfinished letters
from both subfolders, run:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" transcribe --pending --env-file .env --output "local/full-exports" --publish-text
```

Results are saved as the batch proceeds. Keep PowerShell open until the command finishes
or reports a pause/error. The default allocation allows 2 attempt starts per minute and
100 attempts per day, including retries. Coordinate this allocation if another application
uses the same Google project. A daily limit may require continuing on a later day.

`--pending` skips letters with a current complete saved reading, even after 48 hours.
Use it to continue without re-requesting completed letters. In contrast, `--all` and
`--letter` reuse exactly matching complete results only while they are no more than 48 hours
old; changed filenames/settings or older results can lead to another paid request.
If a request was interrupted
with an unknown outcome, inspect it before explicitly accepting a possible repeat charge
with `--retry-interrupted`. See [configuration](configuration.md#cache-interruption-and-recovery).

## 6. Open the text files

In File Explorer, open:

```text
G:\My Drive\Correspondence
```

- `Correspondence_transcriptions.txt`: all active letters in one big text file.
- `Shufeldt, Percy\Shufeldt, Percy_transcriptions.txt`: the Percy folder's letters together.
- `Shufeldt, RW\Shufeldt, RW_transcriptions.txt`: the RW folder's letters together.
- Each scan folder also has individual letter reports, such as
  `Shufeldt, Percy\Shufeldt,P-Todd-1899-04-18.txt`, with all pages of that letter in order.
- `Correspondence_viewer.json`: a machine-readable copy for the web viewer, not a staff report.

Names normally match the first scan without its page suffix. Grouping overrides can supply
an explicit readable `title`; collisions get distinct suffixes so no letter overwrites another.
Failed or unprocessed letters also have clearly labelled status reports, so the presence of
a `.txt` file alone does not mean transcription succeeded.

`--publish-text` enables these Drive copies for this store. Subsequent inventory/transcription/
export commands refresh them automatically. Drive for desktop handles syncing; the program
does not change sharing. Existing scans, unrelated files and staff-edited reports are protected.
Only the exact generated paths recorded by this store are excluded from later scan discovery.
If publication says a report was edited, preserve your version before regenerating it.

Local copies remain under `local/full-exports`: `readable` has the named staff reports,
`combined.txt` has all active letters, and `catalogue.csv` is the index. The older
`letters\ltr_....txt` files are detailed diagnostic reports with technical JSON sections.
Keep `local/full-collection` backed up: it holds original responses and history. AI readings
still need human checking against the scans.

To regenerate the reports from saved results without any Gemini requests, run:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" export --output "local/full-exports" --publish-text
```

Always include both the store and output options shown above. The program does not remember
the last `--output` setting.

The correspondence web viewer reads the synced viewer JSON internally and displays the
letter text. It still needs its actual Drive file IDs, scan mapping and deployment configured;
saving the TXT files alone does not configure it. See [viewer setup](../apps_script/viewer/README.md).

## Corrected scan filenames

If scans were renamed after inventory, use the [explicit filename reconciliation workflow](review.md#reconcile-filenames-changed-outside-the-application)
to preserve the saved readings and IDs, followed by inventory and any grouping overrides.
Do not create a replacement store or re-transcribe every letter just to fix filenames.
The current Drive collection has been reconciled with the user's corrected filenames;
the previously split August 7 pages and December 9 Sutton pages are grouped in numeric order.
Source files have not been renamed by this application.

## Renaming the Drive folder

The commands above use the corrected spelling, `Correspondence`. A store records its absolute
input folder when first inventoried; an existing store tied to the old spelling cannot be
silently redirected. If you see “This store belongs to another input root,” preserve that
store and its history and resolve the path change before continuing. Do not edit the journal
or delete the old store to suppress the error. There is currently no root-relocation command.
