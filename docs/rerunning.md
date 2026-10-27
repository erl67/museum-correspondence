# Rerun individual letters or a selected set

Use the existing collection store and saved inventory. The examples below are for the Drive
collection, with store `local/full-collection` and outputs `local/full-exports`. Run them from
the repository root. These paths are relative to that directory; the `--output` choice is
not remembered between commands. If using a configuration file, put
`--config "local/config.json"` before the command, alongside `--store`.

## Find the letter ID

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" show
```

This prints each `ltr_...` ID with its ordered scan filenames. Match the filenames to the
letter you want, then copy the entire ID, including `ltr_`. The same ID is the `letter_id`
column in `local/full-exports/catalogue.csv`. To inspect its saved reading and current revision:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" show --letter "LETTER_ID_FROM_INVENTORY"
```

`LETTER_ID_FROM_INVENTORY` is a placeholder. A scan filename, page `img_...` ID, result
`rev_...` ID or Drive file ID cannot be used in its place. Only active letter IDs can be
selected for transcription. [Identifier construction](schema.md#identity-and-inventory)
explains where these identifiers come from.

## Request a new reading of one letter

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" transcribe --letter "LETTER_ID_FROM_INVENTORY" --fresh --env-file .env --output "local/full-exports"
```

`--fresh` bypasses the completed-result cache. It reads every page of that letter in its
saved order and may incur service charges. There is no single-page rerun option. Other
letters' saved readings remain selected, while collection-wide outputs are regenerated.

For multiple letters, repeat `--letter`:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" transcribe --letter "FIRST_LETTER_ID" --letter "SECOND_LETTER_ID" --fresh --env-file .env --output "local/full-exports"
```

Selection follows inventory order. `--letter`, `--all` and `--pending` are mutually exclusive.
An unknown or retired selected ID is rejected. Unchanged scans need no inventory refresh;
transcription checks their bytes against the saved inventory before each request.

For this existing Drive collection, avoid repeating root-wide discovery just to reread letters:
supporting material in `old/` and `analysis/` is also visited by recursive discovery. Discovery
has no automatic exclusion for those folder names. Use the saved inventory for unchanged scans.

## Choose reuse, a new reading, or export only

| Purpose | Options/command | Behavior |
| --- | --- | --- |
| Reread one letter immediately | `transcribe --letter ID --fresh` | Bypasses cache and retains earlier revisions |
| Continue selected letters with reuse | `transcribe --letter ID` | Reuses an exactly matching complete result up to 48 hours old; otherwise requests a reading |
| Finish letters lacking a current complete result | `transcribe --pending` | Skips completed letters regardless of cache age or prompt/profile changes |
| Apply current prompt/settings across all active letters | `transcribe --all` | Reuses eligible matching results; requests readings for the rest |
| Regenerate outputs from saved readings | `export` | Makes no transcription requests, regardless of result age |

These are option summaries; keep the store, credentials and output arguments from the full
examples. A changed prompt, model, generation settings, page context or handwriting profile
changes the request fingerprint. A matching recent result must exist for reuse; the most
recent result for that fingerprint must be complete. `--fresh` always bypasses that reuse.

For writer-specific context, add `--profile "local/handwriting/percy-v1.json"` after creating
the file described in [handwriting profiles](handwriting.md). The selected file applies to
the whole command and must be supplied again on later commands. Registered names/aliases
are loaded automatically from the same store.

## What happens to IDs and earlier readings

A new saved result receives a new `rev_...` ID under the same `ltr_...` letter ID. Its pages
retain their `img_...` IDs. The request fingerprint describes the inputs, so an unchanged
`--fresh` rerun has the **same fingerprint and a new revision ID**. Reusing a saved result
creates neither a new revision nor another service attempt. Cache selection may restore an
older eligible revision as the current one, without deleting intervening results.

The store keeps previous responses, page text, request context and review history. New
readings become current after they are saved. Earlier revision-bound corrections/date
confirmations do not automatically apply to a new reading; they remain in history. Reusable
person names and aliases continue to apply. The viewer can still place a letter by its
valid filename date when the new document date is unusable.

Keep the entire store, including `journal.jsonl` and `blobs`, backed up. Starting a new store
is not a rerun: it loses access to saved revisions, overrides, names and publication ownership.
See [schema and identity rules](schema.md) for changes to filenames, pages and grouping.

## Automatic reports and viewer updates

The result is saved before exports run. After each processed result, and again at normal
batch completion, the command rebuilds reports, CSVs, `records.json` and `viewer.json` in
the requested output folder. If publication was enabled with `--publish-text` for this store,
it also refreshes individual/folder/collection TXT files and `Correspondence_viewer.json`
beside the scans. Add `--publish-text` to a transcription or export command to enable it
for a store that has not used it before.

Drive for desktop syncs those files. The viewer reads the configured JSON file on subsequent
requests; reload the page after synchronization. A data-only update using the same Drive
file ID needs no script deployment. [Outputs and automatic updates](outputs.md) details all
destinations, synchronization checks and the separate prepared deployment copy.

## Resume or repair outputs

If a batch pauses, repeat its command **without `--fresh`**, keeping the same profile and
settings, to reuse matching completed results within 48 hours. After that window, select
only the remaining IDs. `--pending` is suitable for finishing unprocessed/failed work, but
will skip older complete letters that you intended to reread after a prompt update.

An interrupted request with an unknown outcome requires inspection before adding
`--retry-interrupted`; it can cause a repeat charge. See [recovery details](configuration.md#cache-interruption-and-recovery).

If the result was saved but report writing or Drive publication failed, fix the destination
problem and regenerate from saved data:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" export --output "local/full-exports"
```

This also retries remembered publication. A failed/paused reading is retained as the current
status; exports do not silently substitute an older complete reading. Earlier text remains
in the store. Recovering an export failure does not require another transcription request.
