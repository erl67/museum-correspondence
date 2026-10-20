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
