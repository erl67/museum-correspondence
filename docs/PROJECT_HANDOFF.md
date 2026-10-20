# Project handoff — 2026-10-20

Application **0.1.0**, schema **1**, prompt **correspondence-1.0**. Initial independent
correspondence implementation. The repository began clean on main at `fa8abd1`, containing
six tracked JPEGs and .gitignore. The read-only reference repository was clean on main at
`ca81d25`; its files, configuration, counters and source collection were not edited.

## Resumption and integration

On resumption after the usage interruption, Git was clean at merge `d2438ca`. The previously
written implementation had been committed externally as `cb78591` (alpha); source changes
in `54d5ef4` moved the original six byte-identical JPEGs into `Shufeldt, Percy`, replaced their
A–D suffixes with numeric labels, and added 19 scans. Current fixtures contain 25 tracked
JPEGs in `Shufeldt, Percy` and `Shufeldt, RW`, grouped into eight provisional letters. These
commits and source changes were preserved; this task did not make them or revert them.

The remaining final verification was completed against that state. Tests/docs now reflect
the current collection while retaining historical six-scan hash/A–D regression coverage.
Additional fixes bound numeric-label validation, prevent missing historical paths from
blocking a distinct current group, persist selection of an older cache revision so exports
show the requested result, and invalidate prior approval when human text/metadata changes.
Current offline results are 88 Python and 18 viewer tests passing, with no failures/skips.

The original local store/export history is retained. Refreshing it creates eight current
unprocessed records and leaves two older missing-path records visible for explicit identity
reconciliation. No automatic hash merge or purported human historical verification is applied.
No live requests, quota reservations, uploads, deployment, new commits or pushes occurred
during this resumed work.

## Responsibilities

| Module | Responsibility |
| --- | --- |
| discovery | Recursive JPEG inventory, integrity, conservative folder-scoped grouping, persistent IDs, overrides and missing/retired history |
| prompt / schema | Historical reading policy, metadata evidence/uncertainty, JSON/page validation and defensible date intervals |
| images | In-memory JPEG preparation, original/submitted hashes, whole-letter payload check, immutable complete request context/fingerprint |
| provider | Explicit Gemini SDK transport, credentials, completion signals; no retry loop |
| execution / usage | One attempt loop, retry policy, persistent quota/pacing, raw responses, checkpointing, usage and optional rate assumptions |
| storage | Atomic writes, OS locks, fsynced append-only journal and content-addressed blobs |
| review / profiles | Persistent human correction/identity/link layers and explicit frozen handwriting context |
| relationships | Local explained candidates, unresolved references, decisions and graph validation |
| exports / cli | Offline TXT/CSV/JSON/viewer output and documented commands |
| apps_script/viewer | Read-only user-authorized Drive viewer, search and ordered scans |

No sibling imports, server, plugin framework, provider benchmark or hidden background worker.

## Reuse and origin

Read `museum-transcription/docs/PROJECT_HANDOFF.md`, current configuration/testing docs,
`transcribe.py` image preparation, request/retry/quota/completion/journal/hash/report code,
`token_usage.py`, and Apps Script viewer patterns before implementation.

The small JPEG preparation routine was adapted from `prepare_image_bytes` in
museum-transcription build **2026-10-19.1** at commit `ca81d25`:
preserve unmodified JPEG bytes, EXIF transpose, optional Lanczos resize, RGB conversion,
quality 95 and subsampling 0. It now also reports transformations and hashes original bytes.
Usage field separation/aggregation, explicit retry accounting, atomic counter writes,
checkpoint-before-export and 48-hour reuse are independently implemented from those proven
patterns. No price table, egg-specific schema, catalogue dependency, paths, credentials,
front/back rules, or report parser was copied.

The viewer reuses design patterns (reader identity access gate, deferred authenticated image
loading, stable positions, escaped text and version/hash checks), not the old collection's
IDs, catalogue routing or deployment. Source materials retain their existing rights; this
task makes no new licensing/publication claim.

## Persistence and review choices

One authoritative JSONL journal plus blobs keeps this first version inspectable. Derived
exports are replaceable. Source updates preserve image IDs at the same path but invalidate
request fingerprints and human-review applicability. Added pages require grouping review;
explicit regrouping retains an existing letter ID only when requested in the override.

The reference application's 48-hour automatic completed-cache eligibility is preserved.
Unlike its fresh console modes, `--fresh` here journals every new revision; this deliberate
departure protects correspondence history. Damaged journal tails fail closed rather than
being silently skipped. Raw response recovery can avoid repeat payment after an interrupted
result checkpoint; unknown network outcomes require explicit retry acknowledgement.

Quota state is deliberately separate and incompatible with old counters. Defaults are a
conservative 2 RPM/20 attempts/day allocation, not a second project allowance. Coordination
with the existing application is a staff operational responsibility.

Reviews bind to one service revision, and relationship decisions retain the document state
that supported them. A new service revision does not silently overwrite/reapply human text.
Named-person approval is distinct from physical handwriting and from full transcription review.
Profiles contain reviewed text examples/source references only; no automatic training.

## Verification and limits

See [testing.md](testing.md) for commands/results. Current numeric-page grouping, the original
six scan hashes and historical A–B/A–D inventory behavior are regression-checked. None of the
scans were transcribed by a live service in this task; no verified reference readings are
claimed. Synthetic fixtures test reply behavior.

Current limits:

- Python command line is the local editing/review interface; no review GUI.
- Grouping is conservative exact-folder/stem parsing, not handwriting/page-content clustering.
- Whole-letter inline JPEG requests only; no PDF, TIFF, splitting or upload strategy.
- JSON MIME requests use the prompt contract plus local validation; no claimed semantic guarantee.
- Failed malformed responses are preserved, but local correction requires a current structurally
  complete base result. There is no salvage-import operation yet.
- Text reports/CSV/viewer exports are local. Viewer installation, actual Drive mapping/access,
  native Google rendering and any future service-account availability require staff setup.
- Pairwise matching and full export rereads are appropriate for an initial collection, not
  unlimited scale. Matching uses saved structured references rather than automatic prose NLP.
- The explicit access gate/file IDs are blank. No data upload, sharing change or deployment occurred.
- Historical reading fidelity, transcription completeness, identities, dates and reply links
  require human review. Hashes and software test counts establish neither accuracy nor authorship.

Future work should start with a small authorized transcription and reviewed source baseline,
then improve metadata/reference extraction from that evidence. Do not silently tune the prompt
or generation settings from unreviewed model output.
