# Scan and report filenames

Use this convention for new scans:

```text
Sender-Recipient-YYYYMMDD_01.jpg
Shufeldt,P-Todd-18990807_01.jpg
Shufeldt,P-Todd-18990807_02.jpg
```

Keep the existing correspondent folders. Include sender and recipient in the filename
so a file remains identifiable outside its folder. Use consistent names and initials;
commas are allowed. Hyphens separate the sender, recipient and date fields, and an
underscore introduces the final numeric page position. Names containing ambiguous
separators need a reviewed grouping override; retain full names in catalogue metadata.

## Page positions

- Start each letter at `_01`, even when it has only one scan.
- Use at least two digits: `_01` through `_99`. For letters over 99 scans, use three
  digits throughout that letter (`_001`, `_002`, ..., `_100`).
- Number scans in reading order. The suffix does not assert printed pagination,
  recto/verso, or a physical sheet number.
- Preserve the position when renaming: `(4)` becomes `_04`, not `_01`.
- Duplicate numeric positions, zero, and missing initial/intermediate positions require
  review. `_1` and `_01` count as the same position.

## Dates and separate letters

| What is known | Example scan |
| --- | --- |
| Full date | `Shufeldt,P-Todd-18990807_01.jpg` |
| Year and month | `Shufeldt,P-Todd-189908_01.jpg` |
| Year only | `Shufeldt,P-Todd-1899_01.jpg` |
| No date | `Shufeldt,P-Todd-undated_01.jpg` |
| First of two separate letters on the same date | `Shufeldt,P-Todd-18990807-a_01.jpg` |
| Second letter on that date | `Shufeldt,P-Todd-18990807-b_01.jpg` |

Use lowercase letter suffixes consistently on every page of that letter. They distinguish
documents, not page positions or confirmed chronology within the day. The same rule works
for partial dates and undated letters. Do not invent month/day values or use `00` as a
date component. Keep uncertain readings, estimated dates and explanations in the catalogue.

Filename dates remain provisional hints. Internally, `18990807` becomes the hint
`1899-08-07`, `189908` becomes `1899-08`, and `undated` becomes null. This formatting
does not add precision or change historical metadata. The response schema and catalogue
date fields continue using dashed dates for comparisons and chronology.

## Reports and compatibility

One report covers the whole letter, so it omits the page suffix:
`Shufeldt,P-Todd-18990807.txt`. A separate same-date letter retains `-a` or `-b`.
Recognized legacy report titles also use compact dates; custom descriptive titles remain
intact. Colliding report names get stable-ID suffixes so every record is retained.

Folder reports keep `<folder>_transcriptions.txt`; collection reports keep
`Correspondence_transcriptions.txt` and `Correspondence_viewer.json`. CSV/JSON, individual
and combined text, and viewer scan labels use current filenames. Original request
provenance and append-only history retain the filenames used at the time of processing.

The parser still accepts dashed filename dates and parenthesized numeric or single-letter
page labels. Legacy and compact stems are not silently merged. The unchanged tracked
fixtures test that compatibility; synthetic tests exercise the new convention.

## Existing collections

Routine inventory, transcription and export commands do not rename scans. A naming
migration needs explicit authorization, an old-to-new path map, collision checks and
SHA-256 verification of every source. Preserve page order, letter/image IDs, saved
readings, reviews, raw responses, quota counters and the earlier journal bytes.

After an authorized external rename, use [reconcile-paths](review.md#reconcile-filenames-changed-outside-the-application)
with the existing store before rediscovery. Update active grouping override files to the
new exact paths, then regenerate reports using `export`. Archive obsolete local readable
reports outside the active export tree. Publication archives superseded, unedited managed
Drive reports into store blobs before removing their old paths; edited reports stop the
operation. Publication ownership is journalled before writes/removals for retry recovery.

Renaming does not require another Gemini request. Use `transcribe --pending` for future
unfinished work; filename changes affect request fingerprints used by `--all`/`--letter`.

## 2026-10-21 Drive migration

The user authorized migration of `G:\My Drive\Correspondence`. All 44 JPEGs were renamed
in their existing folders. Their bytes, IDs, page membership/order and 21 saved completed
readings were verified unchanged. Both current local export trees were refreshed, and
25 current Drive outputs were written and read back. Twenty-two obsolete Drive report
paths were removed after backup, including one earlier superseded report.

The checked map, previous journal, inventory, grouping configuration, output backups and
verification summary are in ignored `local/naming-migration-20261021/`. The local operation
script is `local/migrate_naming_20261021.py`; its `verify` mode checks the migrated state.
These are collection-specific recovery records, not a general-purpose rename command.
Historical source prompts, independent analysis and the correspondence map were preserved.
Drive for desktop handles cloud synchronization; local verification does not establish
that cloud sync has finished. No sharing or viewer deployment changes were made.
