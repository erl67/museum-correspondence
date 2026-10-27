# Local review workflow

To fix words in a saved transcription, start with
[Correct a reading or metadata](#correct-a-reading-or-metadata). The walkthrough uses the
production store `local/full-collection` and exports `local/full-exports`; the separate fixture
store uses `local/collection` and `local/exports`. Keep the same store throughout a review.

Create review JSON under ignored `local/reviews/`, then run `review --file`. Every correction
needs a `source` explaining its basis; `reviewer` is optional. The journal's timestamp supplies
the correction date. Earlier events and original service readings remain unchanged.
`review` saves the change but does not regenerate reports. Run `match` when references have
changed, then `export` with the same store/output arguments to refresh files and any remembered
publication. See [output refresh triggers](outputs.md#when-files-refresh). To request a new
reading instead of a local correction, see [Rerunning letters](rerunning.md).

## Group and order pages

Copy `docs/grouping.example.json` to `local/grouping.json`, populate exact root-relative
paths using `/`, and run:

```powershell
.\.venv\Scripts\python.exe -m correspondence inventory --input "test/inputs" --overrides "local/grouping.json"
```

An override group has a unique stable `key`, explicit ordered `paths`, and `source`.
Optionally include an existing `letter_id` to retain that letter's identity. Omit it for a
new regrouped record. One path can appear in only one override. Listed paths must be visible
in the inventory. An override can join pages across folders or separate same-date letters;
no source files are changed. Unlisted files still appear in automatic groups.

The applied override is saved; subsequent inventory calls reuse it unless another override
file is specified. A reviewed override resolves grouping ambiguity but never makes an
unreadable/missing scan transcribable. Discovery warnings remain visible. Review order after
adding pages: the previous override does not silently acquire new pages.

An optional `title` supplies a readable report filename without changing scan names or
historical metadata. Recognized letter titles use compact dates; custom descriptive titles
are preserved. Otherwise the name comes from the first scan with its page suffix removed.
Use [the current naming convention](naming.md) in new path lists. Legacy paths remain supported.

## Reconcile filenames changed outside the application

After staff rename scans, preserve the existing store and its saved results. Create an
explicit local map rather than silently matching and merging records by hash:

```json
{
  "version": 1,
  "source": "Staff authorized compact-date naming; same original image and page position",
  "paths": {
    "Folder/Shufeldt,P-Todd-1899-08-07(1).jpg": "Folder/Shufeldt,P-Todd-18990807_01.jpg"
  }
}
```

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" reconcile-paths --file "local/source-renames.json"
```

The old path must be absent, the new JPEG must exist within the same input root, and its
SHA-256 must equal the saved original. The command appends a new inventory, preserving image
and letter IDs, earlier paths/responses, and review history. It never moves or edits a scan.
Current reports use the corrected filenames and recheck filename/reading conflicts against
the current hints. Historical request provenance and validation remain in the saved history.
Then refresh `inventory` with any needed grouping overrides. Correcting page membership
still requires explicit grouping review; a filename map does not approve a transcription.
Root-folder relocation is not supported by this command. Use `--pending` when continuing
to avoid re-requesting completed readings after filename changes.
Update any local grouping override file to the reconciled paths before supplying it again.
Then run `export` with the existing store and output directory to refresh current reports.
Original request provenance retains the old names as historical evidence; current scan
references use the new paths. See [the naming guide](naming.md) for output cleanup and recovery.

## Correct a reading or metadata

A review file records your changes against one saved transcription revision. The `show`,
`review` and `export` commands below make no transcription-service requests. Review the scan
alongside the current reading, then save corrections through this workflow. Local generated
exports are rebuilt; edits to published reader copies can block refresh because publication
protects edited files. Use review files for lasting changes and leave source scans untouched.

### 1. Find the letter and its current reading

Run in PowerShell:

```powershell
Set-Location "C:\Users\x5769\Documents\GitHub\museum-correspondence"
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" show
```

Find the scan filename in the listing and copy its letter's `ltr_...` ID. Use the active
complete letter, not an older retired grouping containing one of the same scans. Replace
`ltr_REPLACE` in the next command:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" show --letter "ltr_REPLACE"
```

Copy these values from the displayed record:

| Displayed value | Use in the review file |
| --- | --- |
| `letter_id` | `letter_id` |
| `result.revision_id` | `base_revision` |
| The selected page's `image_id` in `document.pages` | Key under `pages` |
| The selected page's `text` in `document.pages` | Starting text to correct |

Use the top-level `document.pages`, which includes applicable earlier corrections.
`result.document` contains the original service reading and can omit those corrections.
The record must have `active: true` and `execution: "complete"` for this walkthrough.
No new inventory or transcription is needed to review an existing complete reading.

### 2. Create a review file

Create `local/reviews/` if needed. In a text editor, save a UTF-8 `.json` file there with a
descriptive name, for example `percy-18991206-page1-20261027.json`. Its name is for your own
organization; the IDs inside it determine which letter and page change.

Use this structure, replacing every placeholder with the values and text from step 1:

```json
{
  "kind": "letter",
  "letter_id": "ltr_REPLACE",
  "base_revision": "rev_REPLACE",
  "source": "Compared page 1 with the scan; describe the words or passages corrected.",
  "reviewer": "Reviewer name",
  "pages": {
    "img_REPLACE": {
      "text": "Complete corrected page text, including unchanged passages.\nThe next line goes here."
    }
  },
  "transcription_review": "in_progress"
}
```

**The `text` field replaces the entire page.** Copy its complete current text first, then
edit the words you checked. Supplying only a corrected sentence removes the remaining text
from the reviewed page. Preserve line breaks, uncertainty marks and unchanged passages.

Inside a JSON text string, `\n` represents a line break, `\"` represents a quotation mark,
and `\\` represents a literal backslash. Do not put literal line breaks inside the quoted
string. Use double quotes around keys and strings, commas between fields, and no trailing
comma after the last field. Copying the existing JSON `text` value preserves its escaping.

For several pages in the same letter, add entries under `pages`, each keyed by its own
`image_id` and containing its complete corrected text. Include only pages you are changing.
Use separate review files for different letters. Optional `annotations` and `status` replace
those page fields; leave them out to retain them, and preserve unchanged annotations if
replacing their array.

Keep `transcription_review` as `in_progress` when only selected passages have been checked.
Use `approved` only after reviewing the whole transcription. A page correction also returns
metadata and relationship review to `in_progress`, because their evidence may have changed.

### 3. Apply the correction and refresh the outputs

Replace the example review filename with your own:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" review --file "local/reviews/percy-18991206-page1-20261027.json"
```

After `review` succeeds, refresh the reports and published reader data:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" export --output "local/full-exports" --publish-text
```

`review` appends the correction to the store but does not change reports immediately.
`export` rebuilds the collection's reports and viewer JSON using the current corrections.
`--publish-text` also updates managed reader files in the source folders, including
`Correspondence_viewer.json`. Previously enabled publication is remembered even if the flag
is omitted. Source scans and original service responses remain intact.

Open the refreshed report under `local/full-exports/readable/` and check the corrected page.
After Drive synchronization, reload the viewer to check it there. A data update to the same
Drive JSON file does not require redeploying the viewer. See [output updates](outputs.md).

If review fails, fix the reported issue before exporting. In particular, a stale
`base_revision` means you must inspect the current reading again; changing the ID alone can
apply an old whole-page replacement over newer text.

### Later corrections and transcription reruns

For another correction, create a new review file from the latest `show --letter` output,
including earlier applicable corrections in the page text. Editing a review file after it
was applied does not edit its saved event. Running `review` again appends another event;
exporting again only refreshes outputs.

| Later action | What happens to the correction |
| --- | --- |
| Export or reuse the same saved revision with unchanged scans | The correction continues to apply |
| Obtain a new transcription revision | The earlier correction stays in history and needs checking/rebasing |
| Change source content or page membership | Earlier corrections need checking against the changed evidence |

Rebasing means reading the new page, carrying over only corrections still supported by the
scan, and creating a new review with the new `result.revision_id`. Even a fresh request with
the same settings creates a new revision. Do not copy an old complete page over the new one
without comparing them.

A page review does not create or update a handwriting profile. To use confirmed excerpts
as reading context, add them to a [handwriting profile](handwriting.md), increase its version
when changing a registered profile, and supply `--profile` on each transcription command
that should use it. Profiles guide future readings; manual corrections change saved page text.

### Metadata, summaries and current limits

`metadata` is an object keyed by field name; supply the complete field object to replace it:

```json
{
  "sender": {
    "value": "A. Example",
    "normalized": "Alice Example",
    "certainty": "inferred",
    "evidence": [{"image_id": "img_REPLACE", "quote": "A. Example"}]
  }
}
```

Add this under the review's `metadata`. A date correction also needs `precision`.
The corrected document must retain exact page coverage and the document schema. Metadata
corrections return metadata and relationship review to `in_progress`. A correction can
explicitly approve a state when that work has been checked; earlier approval remains in
history. Approval does not remove uncertainty or conflict reasons from the record.

Field/text correction requires a current complete result. Failed or malformed responses
remain in history, but need a subsequent complete reading before this operation can be used.

An optional top-level `summary` string replaces the interpretive summary. Page corrections
do not automatically revise metadata, summaries, extracted species/entities, references or
notes. Include explicit top-level `notes` and `entities` arrays when those also need changing.
Each supplied array replaces the entire corresponding list: copy the current list first and
preserve unaffected entries. An empty array clears it. Omit the field to leave it unchanged.

For example, add this field to a letter review, retaining any other current notes:

```json
{
  "notes": [
    "Prof. Holland is interpreted as William Jacob Holland (W. J. Holland), director of the Carnegie Museum."
  ]
}
```

For `entities`, retain each object's `kind`, source `value`, `normalized`, `role`, `certainty`
and page `evidence`. Correct its quote if the reviewed page text changed. A location inferred
from other correspondence or an external source should be labelled inferred, with its basis
and source recorded in the review's `source` and an explanatory note. Keep historical wording
in the transcription; explanatory geography belongs in separate notes.

Notes and entities are validated before saving, apply only to their `base_revision`, and
return metadata and relationship review to `in_progress`. They do not change transcription
approval on their own. Export refreshes the notes in reports/viewer data and entities in the
local records/CSV. The current review command still has no correction fields for `references`
or `translations`.

If a change affects relationship evidence, recompute candidates before the export in step 3:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" match
```

Matching uses the saved structured evidence; it does not extract new references from corrected
page prose. Metadata corrections do not trigger transcription.

## Approved identities

Create a person with:

```json
{
  "kind": "person",
  "name": "Alice Example",
  "aliases": ["A. Example"],
  "review_status": "approved",
  "source": "Reviewed institutional authority record",
  "reviewer": "Reviewer name"
}
```

The returned review supplies a stable `per_…` ID. Include that `person_id` when correcting
a sender/recipient/attributed-author field. To update a person, supply the existing ID and
the full updated name/alias list. Shared surnames or aliases never automatically merge people;
two different approved people may legitimately share initials. Alias approval is separate
from every letter's attribution and transcription review.

## Standard catalogue names

Use a single preferred name for display, separate from what a letter actually says. A person
review can include `"standardize_display": true` to enable its name and exact aliases as
catalogue labels. Matching ignores case and repeated whitespace, but does not guess from
similar spelling, initials or folder membership. Add each intended variant explicitly.
Use the returned `person_id` and a complete updated record for later authority changes.

The current collection's user-supplied preferred forms are **Percy Shufeldt**, **Robert W.
Shufeldt**, **W.E. Clyde Todd**, and **George Miksch Sutton**. Their local authority records
include the known filename abbreviations and saved name variants. `C. M. Sutton` is not an
alias for George Miksch Sutton; its inferred attribution still needs checking.

From prompt `correspondence-1.1`, approved person names and aliases also accompany new
requests as candidate identities, separately from handwriting profiles. Only names and aliases
are sent, not reviewer/source notes. The model must check the visible initials and wording;
name expansions remain inferred metadata, with the written initials preserved in source text.
Ambiguous candidates are retained and no person link or letter approval is assigned by this
context. Updating a name/alias changes future request fingerprints; changing an internal
authority note alone does not. Model-generated readings never become approved examples.

Enabled aliases apply to existing and future exports from that store, so transcription need
not be rerun. Sender, recipient and attributed-author display labels use an explicit person
link where present, otherwise a unique enabled alias in the reading/normalized value. Only
when there is no reading may the filename supply a labelled hint. Ambiguous or conflicting
alias matches are left unchanged. Unknown names remain unknown. No automatic person links,
relationship matches, metadata approval or handwriting context are created by display aliases.

Viewer labels/search, readable TXT catalogue details, and CSV `sender_display` and
`recipient_display` use this layer. Original values, normalized proposals, evidence, page text
and certainty stay intact. `catalogue_names` in JSON records each label's authority and basis.
The viewer keeps **Filename hint · unverified**, **inferred** and other uncertainty labels.

These rules run in the main program whenever current records are built, including ordinary
inventory/export runs and exports after new transcriptions. No repair script is required.
Filename/name conflict notes are recalculated against the saved authorities: if both names
resolve uniquely to the same authority, the spelling discrepancy is resolved for the catalogue.
Unknown, ambiguous and different identities remain reviewable. Original service validation
and responses are retained unchanged; this does not establish historical attribution.
Back up and reuse the collection store: a new empty store has no staff authority decisions.

## Confirm a catalogue date

Two-digit years remain excluded from document-based relationship chronology. For catalogue
placement, the viewer now falls back to a valid filename date, labelled **Filename hint ·
unverified**, even when a document date is abbreviated or uncertain. A staff confirmation is
optional for that placement. To explicitly confirm the intended date after checking it,
append a letter review with its current `base_revision`, a source explaining the confirmation,
and add the `catalogue_date` field to that review object:

```json
{
  "catalogue_date": {"value": "1899-08-07", "precision": "day"}
}
```

This must agree with the current normalized date/precision. If those are wrong, correct the
date metadata in the same review, preserving its actual source reading and evidence. The
confirmation saves the date evidence and review event and affects catalogue sorting only;
relationship matching still follows the conservative document-date policy. It does not mark
the whole document reviewed. Date or page corrections, changed scans and new service revisions
invalidate the confirmation. Name-only corrections do not. A valid filename date continues to
position the letter after a confirmation expires; this is a provisional catalogue hint, not
carried-forward approval of the new reading.

Re-export after catalogue changes. Remember that the CLI `export` command republishes reader
files beside scans when publication was previously enabled for that store. For local-only
preparation, use `correspondence.exports.export_all` directly, without `publication.publish_text`.
The 2026-10-23 local repair and its backups are under ignored `local/catalogue-repair-20261023/`;
`local/standardize_catalogue_20261023.py` performs only local review/export work.

## Link decisions

```json
{
  "kind": "relationship",
  "from_letter": "ltr_REPLY",
  "to_letter": "ltr_EARLIER",
  "relation": "reply_to",
  "decision": "confirmed",
  "source": "Compared explicit dated reference with both letters",
  "reviewer": "Reviewer name"
}
```

Use `rejected` to reject a candidate (or change an earlier decision); never delete its event.
Other relations are mentions, encloses and related_subject. Self-links and confirmed reply
cycles/definitely reversed chronology are rejected. Correct dates or choose a different
relation before confirming. Partial/overlapping dates remain uncertain. The decision saves
its evidence basis so later metadata changes flag it for review without discarding it.
