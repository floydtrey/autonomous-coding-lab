# SR-2 Intended-Host Qualification

## Status

**QUALIFIED on the intended Windows/PostgreSQL host.**

This document records the bounded intended-host qualification of the accepted SR-2 segment-serving path. It does not expand SR-2 scope or replace the amended SR-1 / KC-D025 contract.

## Executable checkpoint

- Branch: `architecture/knowledge-core`
- Host-qualification executable checkpoint: `c3bfac41eb3a1787d5b770274370b5e59f082eb4`
- CI workflow: Knowledge Core Actions run `34475309465`
- CI result: **success**
- CI head SHA: `c3bfac41eb3a1787d5b770274370b5e59f082eb4`
- Host entrypoint: `components/knowledge-core/tools/sr2_host_qualification.py`
- Host phase worker: `components/knowledge-core/tools/sr2_host_phase.py`

The CI rehearsal is supporting evidence for the executable entrypoint. It is not itself intended-host evidence.

## Pinned qualification corpus

The host run used the accepted G22 corpus without substitution:

- manifest ID: `sr2-g22-real-document-pilot-v1`
- source commit: `bb42835442c03478da2b61c3f79b1c41c26e4e92`
- manifest: `docs/architecture/knowledge-core/SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json`
- exactly three governed source documents
- no retirements

The three source documents are the SR-1 contract, current-state document, and historical Slice 7 pause handoff pinned by the G22 manifest.

## Intended-host execution

The user executed the bounded qualification from the Knowledge Core component on the intended Windows machine on 2026-09-10.

Recorded environment/evidence:

- qualification: `SR-2-intended-host`
- status: `success`
- started: `2026-09-10T12:26:58.091901+00:00`
- completed: `2026-09-10T12:27:15.218984+00:00`
- repository root: `C:\Projects\autonomous-coding-lab`
- state root: `C:\Users\floyd\AppData\Local\KnowledgeCore\sr2-host-qualification-01`
- artifact root: `C:\Users\floyd\AppData\Local\KnowledgeCore\sr2-host-qualification-01\artifacts`
- Docker server: `29.7.2`
- PostgreSQL image: `postgres:18`
- loopback port: `55433`
- PostgreSQL container: `knowledge-core-sr2-host-c3c09d94b99e`
- PostgreSQL volume: `knowledge-core-sr2-host-pg-c3c09d94b99e`
- resulting text generation: `adc37173-6147-40c5-bb07-3d88d36e9f70`

The raw evidence JSON is retained on the intended host at:

`C:\Users\floyd\AppData\Local\KnowledgeCore\sr2-host-qualification-01\SR2_HOST_QUALIFICATION_EVIDENCE.json`

The raw JSON is intentionally not copied into this repository because it contains a large segment-by-segment evidence dump. This document records the acceptance-relevant values.

## Verified acceptance properties

All bounded host-qualification assertions passed:

- `postgres_restart_verified = true`
- `application_reconstruction_verified = true`
- `segment_serving_verified = true`
- `current_historical_retrieval_verified = true`
- `artifact_integrity_verified = true`
- `structural_reconstruction_verified = true`
- `profile_identity_verified = true`
- `governed_provenance_verified = true`
- `exact_replay_verified = true`

The first process, recovered pre-replay state, and recovered post-replay state contained the same durable counts:

- bindings: 3
- generations: 1
- locators: 3
- observations: 3
- receipts: 1
- resources: 3
- resource versions: 3
- text-generation profiles: 1
- text-generation sources: 3
- segment search rows: 107
- whole-resource search rows: 0

The pre-restart snapshot exactly matched the reconstructed pre-replay snapshot, and the reconstructed pre-replay snapshot exactly matched the post-replay snapshot. The same settled generation ID, `adc37173-6147-40c5-bb07-3d88d36e9f70`, was reused after restart/replay.

Public retrieval reported `retrieval_mode = segment`. Current retrieval returned the current-state source; contract retrieval returned the SR-1 source. The superseded Slice 7 handoff was absent from default retrieval and returned only when historical retrieval was explicitly enabled, with lifecycle `superseded`.

## Explicit non-claims

The bounded qualification did **not** perform or claim:

- machine reboot persistence (`machine_reboot_performed = false`)
- backup/restore (`backup_restore_performed = false`)
- production deployment qualification
- broad corpus import
- embeddings/vector retrieval/RAG
- model-based lifecycle inference
- autonomous execution
- PDF/DOCX/HTML/OCR extraction

Those omissions are expected and are not qualification failures.

## Relationship to RI-4

RI-4 remains accepted intended-host evidence for the older RF-2 whole-`ResourceVersion` retrieval path. It must not be relabeled as SR-2 evidence.

This qualification independently exercises the SR-2 section-aware import, derived segment generation, atomic publication, public segment retrieval, PostgreSQL restart, application reconstruction, exact governed provenance recovery, deterministic structural reconstruction, and exact replay behavior.

## Result

The bounded SR-2 intended-host restart/recovery barrier is closed. G1–G22 and the intended-host segment-serving qualification are now accepted checkpoints.

Further work should be selected according to the vertical-slice dependency path rather than extending SR-2 by default. Any future change that alters the accepted SR-1 / KC-D025 structural, lifecycle, lineage, publication, or serving semantics requires a new governed decision/qualification rather than silently changing this checkpoint.
