# Transcribe the Drive collection on Windows

Use `G:\My Drive\Correspondence` as the input folder. The program searches its subfolders
automatically, so one run can include all correspondent folders. It currently accepts JPEG
files (`.jpg` and `.jpeg`). It groups pages into letters within each folder and writes one
UTF-8 `.txt` report per letter, with page boundaries, plus combined text files. Readable
reports show the actual letter text before plain-English catalogue details and review notes;
they contain no JSON sections.

Already transcribed the collection and want the improved reading prompt? Follow
[Rerun after a prompt update](prompt-rerun.md). It uses the existing inventory and store;
the first-time discovery and `--pending` instructions below do not refresh completed letters.
To reread a particular letter, use [Rerunning individual letters](rerunning.md). For a specific
writer's letterforms, see [Handwriting recognition and profiles](handwriting.md).

## Add a new folder to the existing collection

Keep the collection root and `local/full-collection` store. Use `--folder` to discover just
the new subfolder, preserving other saved inventory, IDs, readings and grouping overrides.
Repeat `--folder` for several exact relative folder names. The option includes nested folders;
it is not remembered, and does not check for changes or missing scans in unvisited folders.
Without it, discovery still walks the entire root, including `old/` and `analysis/` copies.
Do not change `--input` to the new subfolder: that would change the collection root.
Windows `desktop.ini` folder settings are skipped; other unsupported files remain visible.

For the Smith batch checked on 2026-11-17, there are **25 JPEG pages in 14 letters**.
`Smith,D` identifies **Daisy Smith** and `Smith,H` identifies **Herbert Smith**. Those two
user-supplied name records are now registered in the existing local store, alongside
**W.E. Clyde Todd**. Names remain separate from handwriting profiles and letter approval.
One shared folder gives all three people's exchanges one chronological list; sender and
recipient labels still use their individual catalogue names. Unknown or conflicting readings
need review rather than being assigned an identity from the folder name.

From PowerShell:

```powershell
Set-Location "C:\Users\x5769\Documents\GitHub\museum-correspondence"
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" dry-run --input "G:\My Drive\Correspondence" --folder "Smith, Daisy-and-Herbert"
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" inventory --input "G:\My Drive\Correspondence" --folder "Smith, Daisy-and-Herbert" --output "local/full-exports"
```

Check the ordered pages before inventorying. The dry run makes no requests or store changes.
Inventory refreshes local reports and, because publication is already enabled for this store,
the managed Drive text and viewer files too. Earlier letters remain in the combined catalogue.
Use the existing `.env` file for the next step; do not replace it with the example.

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" transcribe --pending --env-file .env --output "local/full-exports" --publish-text
```

This final command sends images to the transcription service and can incur charges.
At the batch check, all 21 existing active letters had complete readings, so after the targeted
inventory only the 14 Smith letters should need transcription. `--pending` selects unfinished
letters across the whole store; it is not a folder filter. It skips completed readings regardless
of age. Repeat that command to continue after an ordinary pause; inspect unknown interrupted
outcomes before using `--retry-interrupted`. Do not use `--all` or `--fresh` for this addition.

Results and working exports refresh after each saved letter. After updating the website mirror,
check the Smith folder in the public catalogue. Inventory, transcription and export record the
available timestamps from the saved store. See the [website mirror workflow](outputs.md#how-the-website-receives-new-readings).

If the service returns 503/high demand for every retry, the batch stops and saves the failure.
The terminal now prints the actual saved error and the batch-stop message. Resume later with
the same `transcribe --pending` command. Check the saved status in the working reports before
refreshing the public mirror.

For an explicit Gemini 3.8 Flash attempt after repeated service failures, use the
[alternate-model configuration](configuration.md#opt-in-gemini-38-flash). The prepared local
configuration caps attempts at 20 per day and allows one attempt per letter per invocation:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" --config "local/config-gemini-3.8-flash.json" transcribe --pending --env-file .env --output "local/full-exports" --publish-text
```

Keep that `--config` option when continuing the 3.8 run. Omitting it returns to the usual
3.5 Flash-Lite default. Completed letters remain skipped in either case.

## 1. Open PowerShell in the project folder

Open PowerShell and paste:

```powershell
Set-Location "C:\Users\x5769\Documents\GitHub\museum-correspondence"
```

Make sure Google Drive for desktop is running and you can open the scans in File Explorer
under `G:\My Drive\Correspondence`. Let Drive finish downloading them if necessary.
Name new scans using [the naming guide](naming.md), for example
`Smith,D-Todd_19031105_01.jpg`. Existing inventoried scans require an explicitly
authorized, byte-verified migration and path reconciliation before changing their names.

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

This is the first-time discovery step. For an already inventoried collection with unchanged
scans, go straight to `show` and the [rerun commands](rerunning.md). Discovery walks every
subfolder, including supporting material in `old/` or `analysis/`; review that scope before
inventorying new scans. Those folder names are not automatic exclusions.

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
Use it to continue without re-requesting completed letters.
Using the same `local/full-collection` store also retains grouping overrides, the four standard
catalogue names and their aliases, and revision-bound reviews. Every inventory, transcription
and export refresh applies those name standards automatically to TXT catalogue details, CSV
display columns and viewer data. This also applies to newly added letters and new model
responses; no separate repair script is needed for catalogue labels. Prompt `correspondence-1.1`
also supplies approved names/aliases as reading candidates on new requests. Source spellings, evidence
and certainty remain intact. Known aliases do not trigger filename/name conflict warnings;
unrecognized or ambiguous names still need review.

The confirmed August 7, 1899 catalogue date survives inventory, export, skipped completed
letters and reuse of the same saved revision. A genuinely new transcription (`--fresh`, or
an expired cache with `--all`) requires rebasing that evidence-bound date confirmation. The
program does not automatically approve a newly interpreted two-digit year. The viewer still
positions the letter using its valid filename date, labelled **Filename hint · unverified**,
when the new document date cannot be used. This fallback does not need staff reconfirmation.
Retired groupings
remain inactive and excluded from current viewer listings; the journal retains their history.

The `--all` and
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
  `Shufeldt, Percy\Shufeldt,P-Todd-18990418.txt`, with all pages of that letter in order.
- `Correspondence_viewer.json`: a structured copy of the generated local reading bundle.

Names use the compact-date letter stem without its page suffix. Grouping overrides can supply
an explicit readable `title`; collisions get distinct suffixes so no letter overwrites another.
Failed or unprocessed letters also have clearly labelled status reports, so the presence of
a `.txt` file alone does not mean transcription succeeded.

`--publish-text` enables these Drive copies for this store. Subsequent inventory/transcription/
export commands refresh them automatically. Drive for desktop handles syncing; the program
does not change sharing. Existing scans, unrelated files and staff-edited reports are protected.
Only the exact generated paths recorded by this store are excluded from later scan discovery.
If publication says a report was edited, preserve your version before regenerating it.
Superseded managed reports are backed up into the local store and removed from Drive;
their old names are not recreated as placeholder reports.

Local copies remain under `local/full-exports`: `readable` has the named staff reports,
`combined.txt` has all active letters, and `catalogue.csv` is the index. The older
`letters\ltr_....txt` files are detailed diagnostic reports with technical JSON sections.
Keep `local/full-collection` backed up: it holds original responses, IDs and revision history.
See [outputs and automatic updates](outputs.md) for the complete file list, refresh triggers
and recovery if publication is interrupted.

To regenerate the reports from saved results without any Gemini requests, run:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" export --output "local/full-exports" --publish-text
```

Always include both the store and output options shown above. The program does not remember
the last `--output` setting.

Read the public collection at **[ericlaslo.com/birds/letters](https://ericlaslo.com/birds/letters)**.
`G:\My Drive\Correspondence` is where you add scans and run transcriptions. The website serves
mirrored files from its own hosting. Drive copies refresh as part of the working workflow, and
the website mirror refreshes separately. See [how to refresh the mirror](outputs.md#how-the-website-receives-new-readings).

## Corrected scan filenames

If scans were renamed after inventory, use the [explicit filename reconciliation workflow](review.md#reconcile-filenames-changed-outside-the-application)
to preserve the saved readings and IDs, followed by inventory and any grouping overrides.
Do not create a replacement store or re-transcribe every letter just to fix filenames.
On 2026-10-21 the user authorized migration of all 44 Drive scans to compact dates and
`_01` page suffixes. The existing 21 saved readings, archival IDs and scan bytes were
preserved. Active grouping overrides and all current application outputs were refreshed;
the August 7 pages and December 9 Sutton pages retain their established numeric order.
See [migration records and recovery](naming.md#2026-10-21-drive-migration).

## Renaming the Drive folder

The commands above use the corrected spelling, `Correspondence`. A store records its absolute
input folder when first inventoried; an existing store tied to the old spelling cannot be
silently redirected. If you see “This store belongs to another input root,” preserve that
store and its history and resolve the path change before continuing. Do not edit the journal
or delete the old store to suppress the error. There is currently no root-relocation command.
