# Local review workflow

Use `show --letter "ltr_…"` or `local/exports/records.json` to find IDs, current revision IDs
and evidence. Create review JSON under ignored `local/`, then run `review --file`.
Every correction needs a `source` explaining its basis; `reviewer` is optional. The journal's
timestamp supplies the correction date. Earlier events remain unchanged.

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

Example shape (replace identifiers and source text):

```json
{
  "kind": "letter",
  "letter_id": "ltr_REPLACE",
  "base_revision": "rev_REPLACE",
  "source": "Compared with original scan at full resolution",
  "reviewer": "Reviewer name",
  "pages": {
    "img_REPLACE": {"text": "Complete corrected page text, including unchanged passages."}
  },
  "metadata_review": "in_progress",
  "transcription_review": "in_progress"
}
```

Page `text` replaces the whole page reading, not a substring. Optional `annotations` and
`status` replace those page fields; do not omit existing annotations when replacing their
array. The original service text always remains in the saved result.

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
The corrected document must retain exact page coverage and the document schema.
Use `approved` only after the corresponding work was actually checked. Approval leaves
uncertainty/conflict reasons visible for future readers; it is not an assertion of perfection.
Later page corrections reset transcription, metadata and relationship review to `in_progress`.
Later metadata corrections reset metadata and relationship review to `in_progress`. The
correction can explicitly approve a state when that updated work was checked. Earlier approval
is retained in history, rather than automatically carried onto changed content.
The first version requires a current structurally complete result for field/text correction;
malformed failed responses remain readable but need a subsequent valid service result before
using this correction operation. It does not silently import failures as complete.

After review:

```powershell
.\.venv\Scripts\python.exe -m correspondence match
.\.venv\Scripts\python.exe -m correspondence export
```

Metadata corrections do not trigger transcription. New service revisions require copying
appropriate earlier corrections into a new review citing the new base revision. This is
deliberate protection against applying old text to different scans.

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

Two-digit years remain excluded from automatic chronology. After checking the intended date,
append a letter review with its current `base_revision`, a source explaining the confirmation,
and the following field:

```json
"catalogue_date": {"value": "1899-08-07", "precision": "day"}
```

This must agree with the current normalized date/precision. If those are wrong, correct the
date metadata in the same review, preserving its actual source reading and evidence. The
confirmation saves the date evidence and review event and affects catalogue sorting only;
relationship matching still follows the conservative document-date policy. It does not mark
the whole document reviewed. Date or page corrections, changed scans and new service revisions
invalidate the confirmation. Name-only corrections do not.

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
