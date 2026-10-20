# Repository instructions

- Work only in this repository. `museum-transcription` is a read-only reference, never a
  runtime dependency. Read `docs/PROJECT_HANDOFF.md`, relevant code/docs, Git status and diffs
  before changes; preserve local and unpushed work.
- Never modify, rename, move or overwrite source scans. Fixtures are in **test/inputs**.
  They are not reviewed reference transcriptions or evidence of a reply pair.
- Keep collection discovery/prompt/schema/review/relationships/exports separate from provider,
  execution, quota/accounting and storage. Use small modules; no plugin framework or database.
- Default provider: `gemini-3.5-flash-lite`, temperature 1.0, high thinking. Never silently
  substitute a model or call paid services during routine tests.
- Preserve page coverage/order, uncertainty, partial text, raw responses, hashes and history.
  Complete is not human verified. Never promote model output into approved handwriting context.
- Record and pace every attempt in the execution layer; keep SDK retries disabled, counters
  persistent, and results durable before exports. Unknown usage/cost remains unknown.
- Keep stable archival IDs separate from 48-hour cache fingerprints. Human reviews and
  relationship decisions are append-only, explicitly bound to their evidence/revision.
- Credentials, stores, quotas, mappings, local review/profile files and generated exports go
  in ignored local paths. Preserve existing tracked scans; inspect Git status before delivery.
- Run `.venv/Scripts/python.exe -m unittest discover -s test -t . -v` and
  `node --test apps_script/viewer/test_viewer.cjs` for cross-cutting changes. Report failures
  and skips. No live requests, upload, sharing change, deployment, commit or push unless
  explicitly authorized by the user.
- Update staff-facing README and focused docs when workflows change. Update the handoff when
  responsibilities or limitations change. Do not claim historical accuracy from regression tests.
