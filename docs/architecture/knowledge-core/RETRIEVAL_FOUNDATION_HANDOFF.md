# Knowledge Core — Retrieval / Import Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RI-4 intended-host qualification is complete and accepted. SR-1 — deterministic document segmentation and retrieval contract — is the selected next bounded phase and is design only.**

## Accepted checkpoints

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`
- RF-2 retrieval: `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`
- First curated real-corpus pilot: `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`
- RI-1 design: `f7f12c04163ecbe3b6143191008cf393726b8def`
- RI-2 governed importer: `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`
- RI-3 final validated code/config/docs checkpoint: `9a167e67200c6bee2b7f4ed7b1dc91224d553390` — CI `34418080815`
- RI-3 final evidence checkpoint: `3d12f205d15c310bce0718c56c0866befccd90ec`
- RI-4 harness checkpoint: `934850d5830d4a5d89ec32b04630435a027e816f` — CI rehearsal `34418809968`
- RI-4 intended-host evidence: `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md` — success
- SR-1 handoff: `docs/architecture/knowledge-core/SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md`

## Accepted foundation

Kernel V1 remains frozen. RF-2 and RI-2 semantics are unchanged.

Stable repository document identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

RI-2 still requires exact manifest-listed SHA-1 Git source objects, explicit lifecycle/authority/classification, manifest chaining, omission safety, exact replay, stale-state rejection, and publication fencing. Repository access remains host-injected and ordinary retrieval clients receive no storage/repository credentials.

RI-3 remains the accepted proof that PostgreSQL/artifact/import/generation state survives reconstruction of the Knowledge Core application in another Python process while the database service itself remains up.

RI-4 extends that evidence through a PostgreSQL container restart with a retained named volume and the same persistent artifact directory on both CI and the intended Windows host.

## RI-4 completion evidence

The fixed RI-4 manifest pins exactly three existing Knowledge Core Markdown documents to source commit `3d12f205d15c310bce0718c56c0866befccd90ec`, with RI-2 explicitly historical/superseded.

The harness creates a loopback-only PostgreSQL 18 container backed by a unique persistent Docker named volume, uses a separate host artifact directory, applies the manifest, restarts PostgreSQL, starts a fresh application process, verifies serving/retrieval/artifacts/provenance, exact-replays, and proves the durable snapshot is unchanged.

### CI rehearsal

Run `34418809968` checked out exact harness checkpoint `934850d5830d4a5d89ec32b04630435a027e816f` and passed:

```text
Alembic through 0010_ri2
Fast: 48 passed, 1 expected historical-fixture skip, 18 deselected
PostgreSQL: 16 passed, 2 expected historical-fixture skips, 49 deselected
RI-4 Docker/PostgreSQL restart harness: passed
Workflow: success
```

### Intended Windows host

The same harness later completed successfully on the intended host with Docker Desktop server `29.7.2`, PostgreSQL `18`, loopback port `55432`, and preserved state under:

`C:\Users\floyd\AppData\Local\KnowledgeCore\ri4-host-qualification-01`

The generated evidence reported:

```text
status: success
postgres_restart_verified: true
application_reconstruction_verified: true
exact_replay_verified: true
current_historical_retrieval_verified: true
artifact_integrity_verified: true
provenance_verified: true
backup_restore_performed: false
```

Snapshot across restart/replay remained exactly:

```text
3 bindings
1 settled receipt
3 observations
3 Resources
3 ResourceVersions
3 search rows
1 text generation
3 verified artifacts
```

The serving generation remained `da8ab02c-8819-43d0-9d39-e3098398c8e1`, and exact replay created no additional durable state.

The durable evidence summary is `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md`.

## Selected next phase — SR-1

The next task is now explicitly selected:

**SR-1 — deterministic document segmentation and retrieval contract**

The motivation is the known granularity limit in RF-2: whole-document retrieval is safe and exact but too coarse for documents containing both current and historical/stale material.

Do **not** manually split documents. The intended design keeps the exact whole `ResourceVersion` canonical and has deterministic Python derive smaller rebuildable retrieval units from it. PostgreSQL remains the baseline lexical retrieval engine.

No AI model is required for canonical storage, deterministic segmentation, or baseline retrieval. A model may only be considered later as optional semantic assistance, not as a source-of-truth dependency.

SR-1 is **design only**. The complete scope, required readings, design questions, non-goals, and stop boundary are in:

`docs/architecture/knowledge-core/SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md`

## Critical boundary

RI-4 is complete only for its bounded restart/recovery scope. It does not qualify:

- machine reboot or Docker Desktop restart across host reboot;
- backup/restore or disaster recovery;
- production credentials/TLS/firewalling/service supervision/filesystem ACLs;
- broad or production corpus import;
- automatic discovery/classification/document-key assignment;
- SHA-256-format Git repositories;
- implemented section/chunk retrieval or extraction/OCR;
- embeddings/vector retrieval or RAG;
- Authority or autonomous execution.

SR-1 does not authorize any of those items either.

## Startup instructions for continuation

1. Work from `architecture/knowledge-core`.
2. Verify branch/HEAD before writing.
3. Read `docs/architecture/knowledge-core/SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md` first.
4. Read every prerequisite named by that handoff.
5. Preserve frozen Kernel/RF-2/RI-2 semantics unless concrete evidence demonstrates a defect.
6. Perform only the SR-1 design task and produce falsifiable SR-2 implementation gates.
7. Stop before implementation.

## Next-task boundary

Define retrieval semantics first, then deterministic segmentation rules, then the derived persistence/index contract, failure/rebuild semantics, and SR-2 acceptance gates.

Do not implement Python, migrations, schema changes, embeddings, RAG, broad corpus import, Authority, or execution during SR-1.

## Stop boundary

**SR-1 is selected but not yet performed. Continue only from `SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md`, complete the design-only record, update durable state, commit, and stop before SR-2 implementation.**
