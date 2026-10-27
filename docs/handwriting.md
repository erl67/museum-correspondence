# Handwriting recognition and writer profiles

Ordinary transcription needs no writer profile. Each request contains the complete ordered
scans of one letter. The reading instructions ask the model to compare repeated letterforms,
capitals, joins and abbreviations across those pages, follow text across line/page breaks,
and revisit difficult passages as well as confident but awkward readings. Names, signatures,
dates and ornithological terms receive particular attention. Unresolved passages retain
their uncertainty marks. These checks take place within the same response.

## What carries over between letters

There is no automatic learning of a writer from earlier runs. A batch sends each letter as
a separate request; earlier letters and their saved transcriptions are not silently added
to the next request. Repeatedly transcribing Percy letters does not create a Percy handwriting
model. Writer-specific context is supplied through an explicitly selected profile.

| Context | How it is supplied | What it does |
| --- | --- | --- |
| Current letter's pages | Automatically, in saved page order | Lets the reader compare forms across the letter |
| Filename and folder hints | Automatically from inventory | Supplies provisional sender, recipient and date hints |
| Correspondent names and aliases | Automatically from approved person records in the same store | Supplies candidate expansions for initials and abbreviated names |
| Handwriting profile | Explicit `--profile` file on that command | Supplies observations and checked text examples for a particular hand |

The person registry contains names, not handwriting samples. Its internal source notes and
past transcriptions are not sent as name context. Catalogue display aliases also do not
select a profile. The sender, attributed author and physical writer can differ: a secretary,
copyist or later annotator may have written some or all of a letter.

## Create a profile for a particular hand

Save profiles under ignored `local/handwriting/`, for example `percy-v1.json`. Use a distinct
`profile_id` for each physical hand or period that needs separate context. The ID is a
descriptive label you choose; it is not generated from a sender name or a letter ID.

1. Find source image IDs and `original_sha256` values in `local/full-exports/images.csv`.
   `show --letter` also lists the letter's image IDs and saved request provenance.
2. Compare the selected examples with their scans. Record concrete observations about
   letterforms, joins or abbreviations, plus the exact reading of each chosen passage.
3. Fill in the profile below. The loader requires `review_status: "approved"` on the profile,
   `review_status: "verified"` on every example, and a nonempty `reviewer` in both places.
   Those are existing file-format requirements; a transcription status alone does not create
   a profile or set these fields.

```json
{
  "schema_version": 1,
  "profile_id": "hand_percy_1890s",
  "version": "1",
  "hand_description": "Describe the specific hand and period represented by the examples",
  "review_status": "approved",
  "reviewer": "Name of person who checked these observations",
  "notes": ["Replace with an observation checked against the source scans."],
  "examples": [
    {
      "image_id": "img_REPLACE",
      "source_sha256": "REPLACE_WITH_64_HEXADECIMAL_DIGITS",
      "region": "Top of page, address line",
      "transcription": "Replace with the checked reading of this source region",
      "review_status": "verified",
      "reviewer": "Name of person who checked this passage"
    }
  ]
}
```

This is a template, not an existing Percy profile. The placeholder hash deliberately fails
validation. Profiles allow up to five examples and 16,000 bytes of compact UTF-8 JSON. Each
example cites a stable image ID and its exact SHA-256; `region` optionally identifies a passage.

The request includes the profile's **text notes, example text and source references**. It
does not retrieve the cited scans or attach example crops. Profile loading checks format,
required status fields and hash syntax; it does not compare an example with its source image.
An example may cite a separately held source. Use observations that can be understood from
the text and checked against the current letter's supplied pages.

## Apply a profile to selected letters

Run these commands from the repository root, replacing the placeholders with saved IDs and
the path of a completed profile:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" show
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" transcribe --letter "LETTER_ID_FROM_INVENTORY" --profile "local/handwriting/percy-v1.json" --fresh --env-file .env --output "local/full-exports"
```

`--fresh` requests a new reading with that profile. For several letters in the same hand,
repeat `--letter` in one command:

```powershell
.\.venv\Scripts\python.exe -m correspondence --store "local/full-collection" transcribe --letter "FIRST_LETTER_ID" --letter "SECOND_LETTER_ID" --profile "local/handwriting/percy-v1.json" --fresh --env-file .env --output "local/full-exports"
```

One profile applies to every selected letter. There is no per-writer routing within `--all`;
select the appropriate letters and run separate commands for different hands. The program
does not infer the profile from a filename, folder, sender or previous request. Supply
`--profile` every time you want it used, including when resuming a batch. Omitting the option
means no handwriting profile, even if an earlier revision used one.

## Update a profile and retain its history

The file is loaded once at batch start. Its full content is frozen for that batch, registered
in the store, and copied into each request's provenance. Editing the file during a run does
not change later letters in that run.

To revise observations/examples, increase `version` (for example, from `"1"` to `"2"`) and
prefer a new local filename such as `percy-v2.json`. The same ID/version with different
content is rejected by a store that has already registered it. Existing snapshots remain
available in the store even if the local profile file is later edited.

Profile content and version affect the request fingerprint, so a changed profile normally
requires a new reading. Letter and image IDs stay the same; a new result has a new revision.
Existing reports change only after transcription or export commands run. Adding a profile
does not rewrite saved readings, train the model, or update the profile automatically.
See [rerunning letters](rerunning.md) and [output updates](outputs.md).
