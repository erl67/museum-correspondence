# Correspondence relationships

`match` works entirely locally over saved, active, currently complete letter readings across
the whole store. It uses human corrections where applicable and excludes stale/unprocessed/
failed records as evidence-bearing targets. It does not call Gemini or scan filenames for
assumed correspondence links.

Links are directed and typed:

| Relation | Direction |
| --- | --- |
| `reply_to` | reply → earlier letter it answers |
| `mentions` | mentioning letter → mentioned letter |
| `encloses` | covering letter → enclosed letter |
| `related_subject` | source candidate → another letter with a specific shared subject/identifier; direction is navigational, not chronological |

There is no permanent thread ID. Confirmed reply edges form a graph that can branch or have
multiple predecessors. The viewer displays outgoing predecessors and incoming replies.

## Candidate generation

An explicit, evidenced correspondence reference whose normalized date overlaps a target,
together with reversed correspondent readings or a shared exact specimen/catalogue identifier,
produces a typed candidate. Reviewed person IDs take priority over names. Without approved
IDs, exact normalized/full readings provide a weak candidate signal, never an identity merge.
Uncertain/unknown name fields do not establish reversed pairs.

Ranking is additive: 8 for the dated reference, 3 for reversed correspondents, 2 for an
exact shared specimen/catalogue identifier. A separate related-subject candidate receives
2, plus 2 when a specific identifier is shared. Reversed pairs plus an explicitly extracted
shared subject can generate only related_subject; a subject alone generates no candidate.
Scores are explainable sorting aids, **not measured probabilities**.

Evidence includes source-page quotations, source revision IDs, document-state fingerprints,
supporting reasons, shared exact identifiers and contrary chronology. All alternative
targets remain; the system never chooses one as confirmed. References with no supported
target remain unresolved and do not fabricate missing letter records.

Chronology compares date intervals: full day, month, or year. A definitely earlier purported
reply is contradictory; overlapping intervals remain uncertain. Short-year expansion is
excluded. Confirming a definite chronology contradiction, self-link or reply cycle fails.
Later metadata changes recheck the confirmed graph and expose problems in exports.

## Decisions and rematching

Run `review --file` using the relationship decision shape in [review.md](review.md), then
`match` and `export`. Candidate snapshots and human decisions are different journal events.
Rerunning matching replaces only the current candidate view; confirmed/rejected decisions
survive even if the candidate no longer appears.

Changes to metadata or transcription flag old candidates for rematching and old decisions
for renewed review. A rematch updates candidates but cannot silently renew a staff decision.
Repeat the explicit decision after review to record its new evidence basis.

Version-one limits: pairwise matching is O(n²), intended for initial collections rather than
millions of letters. References come from saved structured readings; there is no full NLP
resolver for arbitrary prose, no fuzzy-name identity merging, and no inference that a partial
date identifies one unique communication. Entity/subject quality remains a human review task.
All reply tests use clearly synthetic letters; the real sample pair is not labelled as replies.
