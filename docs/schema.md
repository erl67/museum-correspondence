# Records, identifiers and exports

Schema version is **1**. Python 3.12+ standard JSON/CSV are used; no database is required.
UTF-8 JSON preserves Unicode, newlines and string identifiers. JSON null means unavailable;
empty arrays mean no items reported, not proof that the source has none. All timestamps are
timezone-aware UTC ISO strings. Historical dates are strings with separate precision.

## Identity and inventory

The first inventory derives a collection UUID from the resolved root and assigns UUID-based
`ltr_…` letter and `img_…` image IDs. The persisted inventory is authoritative thereafter.
Automatic group keys use exact folder plus filename stem without the final page label; no
surname/date normalization is used for identity. The persistent store must move with its
records; starting another store at another root creates another identity namespace.

- Correcting metadata does not change letter/image IDs.
- A newly discovered page under the same group keeps the letter ID, gains an image ID,
  and holds grouping for review. A reviewed override confirms membership/order.
- Replacing bytes at the same relative path keeps the image ID and records a new SHA-256.
  Earlier inventory events and request manifests retain prior hashes; cache identity changes.
  Earlier readings/reviews are stale until a new result and deliberate review.
- Files removed from the root remain inventoried as missing. No history is deleted.
- Explicit regrouping can retain an existing `letter_id`, or omit it and use a new override
  `key` to create a new letter ID. Displaced groups become retired records. Original service
  responses remain attached to their original IDs and source manifests.
- If staff independently rename/move a scan, automatic discovery treats the new path as a
  new image, leaving the earlier one missing. Use a reviewed grouping override to retain the
  letter ID; there is no automatic filename/hash identity merge or source rename operation.

An inventory event contains `collection_id`, `input_root`, ordered `images`, `letters` and
the exact applied `overrides`. Images contain ID, original path/filename/folder, SHA-256,
byte count, dimensions where readable, and ready/unsupported/unreadable/symlink/missing status.
Letters contain ID, group key, ordered image IDs, provisional hints, grouping state, review
reasons, override evidence and active/retired state.

## Journal and blobs

Each `journal.jsonl` line has `schema_version`, `event_id`, `at`, `kind`, and `data`.
Kinds are inventory, profile, run_start, attempt_start, attempt_end, result, selection, review,
matching, and run_end. Append and fsync precede dependent operations. Never edit exported
JSON and expect it to update the journal.

`blobs/<sha256>.jpg` holds submitted bytes; `blobs/<sha256>.json` holds complete request
provenance, raw SDK response objects, or redacted structured service errors. The raw SDK
response preserves all fields supplied by the SDK, including rejected text and usage.
All blobs and all journal events should be backed up together. There is no pruning operation.

Attempt-start records include ID, letter, run ID, initial request blob, exact effective prompt
(including any format correction), prompt hash, timestamps and operational settings.
Attempt-end records contain raw response/error references, returned usage and cost assumptions.
A result references every attempt contributing to it and contains revision ID, execution
state, raw answer text, parsed document, errors/review reasons, returned model version, saved
timestamp, complete initial provenance and fingerprint.
A selection event chooses a previously saved eligible revision when cache reuse returns an
older result after another configuration was used. It adds no request, usage or revision and
does not reset cache age. Reports and reviews follow the selected revision.

Source originals are not copied into the store when a transformation differs; submitted
bytes are retained. The original hash plus preserved source path identifies the source.
Submitted byte blobs, page labels, prompt, model and generation configuration reconstruct
the service input even if a source file later changes. Results never require the sibling repo.

## Document contract

`pages`: ordered `{image_id, status, text, annotations}` records. Status is text/blank/unrelated/
illegible; text always explicitly accounts for that page. Annotations contain `kind` and `text`.

`metadata` fields: sender, recipient, date, place_written, addresses, affiliations, language,
document_type, attributed_author, physical_hand. Each has `value` (source reading),
`normalized` (search proposal), `certainty`, and `evidence: [{image_id, quote}]`.
Addresses/affiliations may be multiline strings; entities can separately index organizations
and places. Human corrections may add a registered `person_id` to identity fields.

`date` also has `precision`: day/month/year/partial/ambiguous/unknown. ISO normalized values
are YYYY-MM-DD, YYYY-MM or YYYY. A year is never stored as January 1. Partial/ambiguous dates
retain wording and normally null normalization. Two-digit years are not expanded. The
chronology matcher excludes unsupported normalizations; date bounds used internally for
interval comparisons are not exported as asserted dates. Postmark/receipt/body dates stay
in their page annotations/text and optional entities/references, not the letter-date field.

`entities`: one record per person/organization/place/bird/specimen/catalogue/subject, with
verbatim `value`, `normalized`, `role`, `certainty`, `evidence`. Catalogue/specimen numbers
are strings, including zeros.

`references`: kind reply_to/mentions/encloses/related_subject, description, date_as_written,
date_normalized, date_precision, certainty, evidence. References do not assert that a scan
exists. `summary`, string-array `notes`, and optional page-linked `translations` are separate.
The exact response skeleton is generated by `schema.empty_document`.

## Independent states and review

Grouping: provisional/reviewed/needs_review/retired. Execution:
unprocessed/blocked/complete/failed/paused/interrupted/stale. Metadata, human transcription,
and relationship review each use unreviewed/in_progress/approved. Approval is never inferred
from structural completion or another approval. A complete result may have many review flags.

Human corrections are dated review events bound to a base service revision, preserving the
original. New revisions do not silently inherit old correction text. Earlier reviews remain
in exported `review_history`; `stale_reviews` lists those needing rebasing.

## Export conventions

`records.json` is a versioned current view including full original results and review history.
`viewer.json` is a smaller reading view with ordered scans, explicit availability, links,
unresolved references and separate provenance. It contains collection data; it is not public.

CSV tables use UTF-8 BOM, standard quoting and CRLF row endings. Newlines inside quoted
fields remain newlines. No pipe/semicolon-separated relationship encoding is used.

| CSV | Row key/content |
| --- | --- |
| catalogue | one row per letter, including retired, blocked and failed |
| images | letter ID + image ID + order; exact relative path and original filename |
| evidence | one metadata quotation per row; letter, field, certainty, image, quote |
| entities | one entity per row; evidence_json is a documented JSON array |
| relationships | one directed typed link per row; evidence_json and contradictions_json are JSON arrays |
| unresolved | one unresolved reference per row; reference_json is its structured source reference |

`review_reasons_json` is also a JSON array. Empty CSV cells mean null/unavailable.
`catalogue.date_normalized` is blank when local normalization checks reject the proposed
date; the unmodified service proposal remains in records/provenance with review reasons.
Formula-leading cells (after whitespace: =, +, -, @; or initial tab/CR/LF) receive one leading
apostrophe in CSV. JSON and text remain unchanged. For significant zeros, import numeric-looking
identifier columns as Text; CSV has no type system and quoting alone cannot force Excel types.
