# Reviewed handwriting context

Profiles are optional explicitly selected JSON files. A model does not learn a writer between
requests. Each request receives only the chosen frozen profile's approved notes and verified
text examples. Unreviewed service output is never automatically promoted into a profile.

Create a local file using this shape:

```json
{
  "schema_version": 1,
  "profile_id": "hand_EXAMPLE",
  "version": "1",
  "hand_description": "Reviewed hand, correspondence dated 1890–1895; attribution uncertain",
  "review_status": "approved",
  "reviewer": "Reviewer name",
  "notes": ["Only include observations actually checked against source scans."],
  "examples": [
    {
      "image_id": "img_REPLACE",
      "source_sha256": "REPLACE_WITH_64_HEXADECIMAL_DIGITS",
      "region": "Top of page, address line",
      "transcription": "Verified reading of that source region",
      "review_status": "verified",
      "reviewer": "Reviewer name"
    }
  ]
}
```

The placeholder hash deliberately fails validation. An example identifies a source scan by
stable image ID and exact source hash, optionally describes a region, and supplies verified
text. The profile can cite an externally held reviewed source, so loading validates its
format/reviewer status but does not assert the reviewer or historical reading is correct.
This first version supplies **text notes/examples and source references**, not additional
example image crops. It never looks up example sources in another repository.

At most five examples and 16,000 UTF-8 JSON bytes are allowed. Each example must be verified;
the profile and its notes must be approved. Source hashes must be valid hexadecimal SHA-256.
Use different profile IDs for distinct hands or periods, even when attributed to the same
author. A secretary/copyist's hand is not automatically the named sender's.

```powershell
.\.venv\Scripts\python.exe -m correspondence dry-run --input "test/inputs" --profile "local/hand.json"
.\.venv\Scripts\python.exe -m correspondence transcribe --letter "ltr_REPLACE" --profile "local/hand.json" --env-file .env
```

Profiles are selected explicitly, never by filename similarity. The file is loaded once at
batch start and its content is copied into request provenance. File changes during the batch
cannot affect later requests. Registering a different profile under the same ID/version in
one store is rejected; increment the version. The complete content and version affect the
request fingerprint, while older results remain intact. No profile is needed for ordinary
transcription. Fine-tuning, automatic writer clustering and learned profile updates are absent.
