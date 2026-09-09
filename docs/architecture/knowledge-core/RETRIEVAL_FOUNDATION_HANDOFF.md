# Knowledge Core — Retrieval / Import Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RI-4 restart qualification harness is implemented and CI-rehearsed successfully. RI-4 remains open pending one intended-host qualification run.**

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

## Accepted foundation

Kernel V1 remains frozen. RF-2 and RI-2 semantics are unchanged.

Stable repository document identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

RI-2 still requires exact manifest-listed SHA-1 Git source objects, explicit lifecycle/authority/classification, manifest chaining, omission safety, exact replay, stale-state rejection, and publication fencing. Repository access remains host-injected and ordinary retrieval clients receive no storage/repository credentials.

RI-3 remains the accepted proof that PostgreSQL/artifact/import/generation state survives reconstruction of the Knowledge Core application in another Python process while the database service itself remains up.

## RI-4 current state

RI-4 is deliberately a qualification harness, not production deployment.

Files added at `934850d5830d4a5d89ec32b04630435a027e816f`:

- `components/knowledge-core/tools/ri4_host_qualification.py`
- `components/knowledge-core/tools/ri4_host_phase.py`
- `docs/architecture/knowledge-core/RI4_HOST_QUALIFICATION_MANIFEST.json`

The Knowledge Core workflow also runs the host harness as a CI rehearsal.

The fixed manifest pins exactly three existing Knowledge Core Markdown documents to `3d12f205d15c310bce0718c56c0866befccd90ec`, with RI-2 explicitly historical/superseded.

The harness creates a loopback-only PostgreSQL 18 container backed by a unique persistent Docker named volume, uses a separate host artifact directory, applies the manifest, restarts PostgreSQL, starts a fresh application process, verifies serving/retrieval/artifacts/provenance, exact-replays, and proves the durable snapshot is unchanged.

No production Knowledge Core Python was modified.

## Exact CI evidence

Run `34418809968` checked out exact harness checkpoint `934850d5830d4a5d89ec32b04630435a027e816f` and passed:

```text
Alembic through 0010_ri2
Fast: 48 passed, 1 expected historical-fixture skip, 18 deselected
PostgreSQL: 16 passed, 2 expected historical-fixture skips, 49 deselected
RI-4 Docker/PostgreSQL restart harness: passed
Workflow: success
```

The RI-4 step reported all of these true:

```text
postgres_restart_verified
application_reconstruction_verified
exact_replay_verified
current_historical_retrieval_verified
artifact_integrity_verified
provenance_verified
```

`backup_restore_performed` remained false.

Snapshot across restart/replay:

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

## Critical boundary

The successful CI rehearsal is not the intended-host qualification.

RI-4 is still open until the same script succeeds on the intended host and its generated `RI4_HOST_QUALIFICATION_EVIDENCE.json` is reviewed.

Do not mark RI-4 complete based only on GitHub Actions.

## Intended-host command

From `components/knowledge-core`, after installing `.[test]` and with Docker Desktop/Engine running:

```powershell
python tools\ri4_host_qualification.py `
  --repository-root ..\.. `
  --state-root "$env:LOCALAPPDATA\KnowledgeCore\ri4-host-qualification-01"
```

Use a brand-new empty state path outside the Git repository. Do **not** pass `--cleanup` on the intended host; preserve the stopped qualification container/volume and evidence until review.

## Startup instructions for continuation

1. Work from `architecture/knowledge-core`.
2. Verify branch/HEAD before writing.
3. Read:
   - `docs/architecture/knowledge-core/CURRENT_STATE.md`
   - `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI4.md`
   - `docs/architecture/knowledge-core/RI4_HOST_QUALIFICATION_MANIFEST.json`
   - `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
4. Do not redesign RI-2/RF-2 or broaden the corpus.
5. The only authorized continuation is intended-host RI-4 execution/evidence review.

## Explicit non-goals

No backup/restore, host-reboot qualification, production deployment/security hardening, production corpus, automatic discovery/classification, SHA-256 Git support, chunking/extraction/OCR, embeddings/RAG, Authority, or autonomous execution is authorized by RI-4.

## Stop boundary

**Stop after preparing/reviewing the intended-host RI-4 evidence. Do not begin another phase without separate user authorization.**
