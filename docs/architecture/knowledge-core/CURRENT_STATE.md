# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-2 retrieval:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**First curated real-corpus pilot:** `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`  
**RI-1 design:** `f7f12c04163ecbe3b6143191008cf393726b8def`  
**RI-2 governed importer:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**RI-3 application-process persistence:** final validated checkpoint `9a167e67200c6bee2b7f4ed7b1dc91224d553390` — CI `34418080815`  
**RI-3 final evidence-only checkpoint:** `3d12f205d15c310bce0718c56c0866befccd90ec`  
**RI-4 host harness:** `934850d5830d4a5d89ec32b04630435a027e816f` — CI rehearsal `34418809968`  
**RI-4 record:** `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI4.md`  
**Status:** **Kernel V1 remains frozen. RF-2, RI-2, and RI-3 are accepted. RI-4 restart qualification is implemented and reproduced in CI, but intended-host evidence is still required before RI-4 can be marked complete. No broad or production corpus has been imported.**

This is the controlling branch-specific state.

## Accepted foundation

Stable governed repository document identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

RF-2 remains exact whole-ResourceVersion PostgreSQL lexical retrieval with explicit lifecycle/authority metadata, deterministic ranking, current-generation-only serving, exact provenance, and serving-time restriction/deletion fences.

RI-2 remains the accepted repository-import implementation: exact SHA-1 Git source verification, explicit Manifest V2 allowlists, manifest chaining, omission safety, stable edit/rename identity, explicit retirement, stale source/state rejection, generation publication fencing, exact replay, and service-only repository access.

RI-3 proves that accepted import/generation/artifact state survives complete reconstruction of the Knowledge Core application in a separate Python process while the same PostgreSQL database and artifact directory remain intact.

## RI-4 — local-host persistence/recovery qualification

RI-4 adds no production Knowledge Core module. The new qualification harness is:

- `components/knowledge-core/tools/ri4_host_qualification.py`
- `components/knowledge-core/tools/ri4_host_phase.py`
- `docs/architecture/knowledge-core/RI4_HOST_QUALIFICATION_MANIFEST.json`

The RI-4 manifest pins exactly three Markdown files at source commit `3d12f205d15c310bce0718c56c0866befccd90ec`: current `CURRENT_STATE.md`, current `REPOSITORY_IMPORT_RI3.md`, and historical/superseded `REPOSITORY_IMPORT_RI2.md`.

The harness creates an isolated loopback-only PostgreSQL 18 qualification container with a unique persistent Docker volume and an explicit artifact directory outside the source repository. It applies the fixed manifest in one application process, restarts PostgreSQL while retaining the volume, constructs a second application process, verifies current/historical retrieval, SHA-256 artifacts, exact provenance, same generation, and exact replay, and writes a durable evidence JSON. Backup/restore is deliberately excluded.

## Exact RI-4 CI rehearsal

Harness checkpoint `934850d5830d4a5d89ec32b04630435a027e816f`, GitHub Actions run `34418809968`:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2: passed
Fast: 48 passed, 1 expected historical-fixture skip, 18 deselected
PostgreSQL: 16 passed, 2 expected historical-fixture skips, 49 deselected
RI-4 restart qualification harness: passed
Workflow: success
```

The RI-4 harness step used Docker server `28.0.4` and reported:

```text
postgres_restart_verified: true
application_reconstruction_verified: true
exact_replay_verified: true
current_historical_retrieval_verified: true
artifact_integrity_verified: true
provenance_verified: true
backup_restore_performed: false
```

Persistent snapshot before and after restart/replay remained:

```text
3 document bindings
1 settled receipt
3 source observations
3 Resources
3 ResourceVersions
3 RF-2 search rows
1 text generation
3 verified SHA-256 artifacts
```

This validates the harness and restart semantics in CI. It does **not** substitute for the intended-host run.

## Intended-host acceptance still required

RI-4 remains open until `ri4_host_qualification.py` succeeds on the intended local host against a new explicit state directory outside the repository and the resulting `RI4_HOST_QUALIFICATION_EVIDENCE.json` is reviewed.

The exact command and acceptance fields are recorded in `REPOSITORY_IMPORT_RI4.md`.

## Current limitations / unclaimed capability

Knowledge Core still does not claim:

- completed RI-4 intended-host qualification;
- machine reboot or Docker Desktop restart across host reboot;
- backup/restore or disaster recovery;
- production credentials, TLS, firewalling, service supervision, startup policy, or filesystem ACL qualification;
- broad/production corpus import or automatic discovery/classification/document-key assignment;
- SHA-256-format Git repository support;
- chunking/section retrieval, PDF/DOCX/HTML extraction/OCR, embeddings/vector search, or RAG;
- Authority integration or autonomous execution.

## Durable restart point

Read before continuing RI-4:

- `docs/architecture/knowledge-core/CURRENT_STATE.md`
- `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI3.md`
- `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI4.md`
- `docs/architecture/knowledge-core/RI4_HOST_QUALIFICATION_MANIFEST.json`
- `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
- `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
- `components/knowledge-core/README.md`

Verify branch/HEAD before writing.

## Next permitted action

Run the recorded RI-4 host qualification once on the intended machine, preserve its evidence and persistent qualification stores, review the evidence, then mark RI-4 complete if every recorded acceptance field passes.

Do not begin backup/restore, production deployment, broad corpus import, automatic discovery/classification, chunking, embeddings/RAG, Authority, or execution.

## Stop boundary

**RI-4 is not yet complete. The harness and CI rehearsal are complete; intended-host evidence is the only authorized next step.**
