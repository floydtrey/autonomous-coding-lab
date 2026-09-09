# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-1 design:** `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`  
**RF-2 implementation:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**First curated real-corpus pilot:** `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`  
**RI-1 design:** `f7f12c04163ecbe3b6143191008cf393726b8def`  
**RI-2 validated implementation:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**RI-3 pilot implementation:** `de77c2707b283b9765ebde1a369a8da78a5a847c` — CI `34417659798`  
**RI-3 completion:** `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI3.md`  
**Status:** **Kernel V1 remains frozen. RF-2 retrieval, RI-2 governed repository import, and RI-3 application-process persistence/replay qualification are complete. No broad or production corpus has been imported.**

This is the controlling branch-specific state. Detailed historical evidence remains in the named records and exact CI runs.

## Accepted retrieval/import foundation

Kernel V1 remains frozen. RF-2 provides exact whole-ResourceVersion PostgreSQL lexical retrieval, explicit lifecycle/authority metadata, deterministic ranking, current-generation-only serving, exact provenance, and serving-time restriction/deletion fences.

RI-2 provides stable governed repository document identity:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Manifest V2 remains an explicit fail-closed allowlist with exact SHA-1 Git source proofs, explicit lifecycle/classification/authority, manifest chaining, omission safety, plan/apply stale-state validation, replay idempotency, update/rename semantics, explicit retirement, and generation publication fencing. Ordinary `create_app()` remains import-incapable; import requires host-injected governed source readers.

## RI-3 — tiny persistent operational pilot

RI-3 did not modify production Knowledge Core Python. It qualifies existing RI-2/RF-2 behavior under persistent PostgreSQL plus filesystem-artifact state across complete application reconstruction.

The fixed manifest is `RI3_PERSISTENT_PILOT_MANIFEST.json`, pinned to source commit `3e675f0ffb584d6b270e0a7c52428c74a5496be3`. It contains exactly three Markdown sources:

- `CURRENT_STATE.md` — current, authority rank 1;
- `REPOSITORY_IMPORT_RI2.md` — current, authority rank 5;
- `REPOSITORY_IMPORT_RI1.md` — superseded historical, authority rank 20.

The first Python process planned/applied the manifest and persisted exactly three bindings, one settled receipt, three source observations, three Resources, three ResourceVersions, three RF-2 search rows, and three SHA-256 artifact files.

A second independent Python process then reconstructed the engine/session factory, artifact store, Git reader, import app, and client against the same stores. Before replay it served the same generation and reproduced current/historical retrieval. Exact replay returned the same receipt and left the durable snapshot unchanged.

Current-only retrieval excluded RI-1. Explicit `include_superseded=true` retrieval exposed RI-1 with the exact pinned source commit/path/version provenance.

## Exact RI-3 validation

Checkpoint `de77c2707b283b9765ebde1a369a8da78a5a847c`, GitHub Actions run `34417659798`:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2: passed
Fast: 48 passed, 1 expected historical-fixture skip, 18 deselected
PostgreSQL: 16 passed, 2 expected historical-fixture skips, 49 deselected
Workflow: success
```

The extra PostgreSQL test is the RI-3 two-process persistence/replay qualification. Existing pinned RF-2 historical-fixture skips are intentional and unrelated.

Because RI-3 pins an immutable historical source commit, Knowledge Core CI retains full local Git history (`fetch-depth: 0`) so that exact source remains available as the branch advances. The importer itself remains restricted to exact manifest-listed paths and does not recursively scan or auto-import the repository.

## Current limitations / unclaimed capability

Knowledge Core does not yet claim:

- PostgreSQL server/container restart or host reboot persistence qualification;
- production service/process supervision, filesystem paths/permissions, secrets, TLS/firewalling, or repository credential deployment;
- backup/restore or disaster-recovery qualification;
- broad or production-scale persistent repository import;
- automatic repository discovery/classification/document-key assignment/rename heuristics;
- production approval of the RI-3 three-document pilot classification as a broader corpus policy;
- SHA-256-format Git repository support;
- separately qualified reactivation-after-retirement semantics;
- canonical replacement/supersedes relationships beyond accepted manifest metadata;
- chunking/section retrieval, PDF/DOCX/HTML extraction/OCR, embeddings/vector search, or RAG;
- Authority integration or autonomous execution.

## Durable restart point

Read before the next import task:

- `CURRENT_STATE.md`
- `REPOSITORY_IMPORT_RI1.md`
- `REPOSITORY_IMPORT_RI2.md`
- `REPOSITORY_IMPORT_RI3.md`
- `RI3_PERSISTENT_PILOT_MANIFEST.json`
- `RETRIEVAL_FOUNDATION_HANDOFF.md`
- `RETRIEVAL_FOUNDATION_RF2.md`
- `EXECUTION_GOVERNANCE.md`
- `components/knowledge-core/README.md`

Verify branch/HEAD before writing.

## Next separately authorized task

### RI-4 — local-host persistence/recovery qualification

Candidate only: use a tiny explicitly reviewed manifest with deliberately persistent PostgreSQL and artifact locations on the intended host. Prove application/service reconstruction and PostgreSQL/service restart against the same stores, exact replay, current/historical retrieval, artifact integrity, and provenance. Add backup/restore only if separately authorized.

RI-4 must stop before broad ACL/Vera/RiskCardOCR/research import, automatic discovery/classification, chunking, embeddings/RAG, Authority, or autonomous execution.

## Stop boundary

**RI-3 is complete. Do not begin RI-4 without separate user authorization.**
