# RI-4 Intended-Host Qualification Evidence

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Qualification:** RI-4 local-host persistence / recovery  
**Harness checkpoint:** `934850d5830d4a5d89ec32b04630435a027e816f`  
**Source corpus commit:** `3d12f205d15c310bce0718c56c0866befccd90ec`  
**Manifest digest:** `160b4ba2966305108a1a381a5996c93d8c22cced36fe2fa4baa99d9e6a554927`  
**Intended-host result:** **SUCCESS**

## Host execution

The intended Windows host ran:

```powershell
python tools\ri4_host_qualification.py `
  --repository-root ..\.. `
  --state-root "$env:LOCALAPPDATA\KnowledgeCore\ri4-host-qualification-01"
```

The state root was:

`C:\Users\floyd\AppData\Local\KnowledgeCore\ri4-host-qualification-01`

The qualification used Docker Desktop server version `29.7.2`, PostgreSQL image `postgres:18`, and loopback port `55432`.

The generated evidence reported start time `2026-09-10T00:43:57.612890+00:00` and completion time `2026-09-10T00:45:09.369242+00:00`.

The intended-host run intentionally did **not** use `--cleanup`; its evidence file, artifact directory, stopped PostgreSQL container, and named Docker volume were preserved for review.

## Acceptance fields

The generated `RI4_HOST_QUALIFICATION_EVIDENCE.json` reported:

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

All required RI-4 intended-host acceptance booleans therefore passed.

## Durable state across restart and replay

Before PostgreSQL restart/recovery and after exact manifest replay, the persistent snapshot remained:

```text
bindings: 3
generations: 1
locators: 3
observations: 3
receipts: 1
resource_versions: 3
resources: 3
search_rows: 3
```

The serving text generation remained exactly:

`da8ab02c-8819-43d0-9d39-e3098398c8e1`

The import receipt remained `settled` and exact replay reused the original receipt rather than creating additional durable state.

## Retrieval behavior

Current retrieval for `application process persistence` returned the current RI-3 completion document and current Knowledge Core state document from the same text generation.

Default retrieval for `operational receipt status transitions` returned no result because the RI-2 completion document was explicitly superseded.

Historical retrieval for the same query returned only `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md` with lifecycle `superseded` and source version `3d12f205d15c310bce0718c56c0866befccd90ec`.

This confirms current/historical serving separation remained intact after PostgreSQL restart and application reconstruction.

## Exact provenance and artifact integrity

All three manifest sources retained exact repository-import provenance and independently verified SHA-256 artifacts:

- `CURRENT_STATE.md` -> document key `kc-current-state-ri4`, Git blob `16555df9ac80ec739dcf5cf2a5937d14c176b06b`;
- `REPOSITORY_IMPORT_RI3.md` -> document key `kc-ri3-completion-ri4`, Git blob `f4b7f1a56086660741521b938d7c9e9304ee514e`;
- `REPOSITORY_IMPORT_RI2.md` -> document key `kc-ri2-completion-ri4`, Git blob `bc12a15dbac70e1ba538e313ce87dfed41b9e831`.

Every provenance record reported `artifact_verified: true` before and after restart/replay.

## RI-4 disposition

The intended-host run closes the only acceptance item that remained after the successful CI rehearsal `34418809968`.

RI-4 is therefore **accepted complete** for the scope it claimed:

- PostgreSQL container restart with a retained Docker named volume;
- reconstruction of the Knowledge Core application in a new Python process;
- reuse of the same persistent artifact directory;
- current/historical RF-2 retrieval continuity;
- exact repository-import receipt replay;
- exact provenance and SHA-256 artifact integrity across restart.

RI-4 still does **not** claim machine-reboot persistence, Docker Desktop restart across a host reboot, backup/restore, disaster recovery, production credentials/TLS/firewalling/service supervision/filesystem ACL qualification, broad corpus import, automatic discovery/classification, chunking, embeddings/RAG, Authority, or autonomous execution.

## Stop boundary

This document records completion evidence only. It does not authorize any capability beyond the accepted RI-4 scope.
