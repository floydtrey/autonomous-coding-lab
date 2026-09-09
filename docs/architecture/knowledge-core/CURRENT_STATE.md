# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-1 design:** `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`  
**RF-2 implementation:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**First real-corpus pilot:** `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`  
**RI-1 design:** `f7f12c04163ecbe3b6143191008cf393726b8def`  
**RI-2 validated implementation:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**RI-2 completion:** `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md`  
**Status:** **Kernel V1 remains frozen. PostgreSQL qualification, RF-2 retrieval, the curated real-corpus pilot, RI-1 import design, and RI-2 minimal governed repository import are complete. No broad or production corpus has been imported.**

This is the controlling branch-specific state. Detailed historical evidence remains in the named records and exact CI runs.

## Accepted retrieval/import foundation

Kernel V1 remains frozen. RF-2 continues to provide exact whole-ResourceVersion PostgreSQL lexical retrieval, explicit lifecycle/authority metadata, deterministic ranking, current-generation-only serving, exact provenance, and serving-time restriction/deletion fences.

The first curated real-corpus pilot remains accepted at its pinned source checkpoint. Historical replay intentionally skips once checkout bytes diverge from that pinned corpus rather than relabeling changed bytes with old provenance.

## RI-2 governed repository import

RI-1 design is `REPOSITORY_IMPORT_RI1.md`. RI-2 implementation/completion is `REPOSITORY_IMPORT_RI2.md`.

Stable logical document identity is:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Path and content digest are not logical identity.

Migration `0010_ri2` adds `kc_control.repository_document_binding`, `repository_import_receipt`, and `repository_source_observation` while canonical content remains in existing Resource/ResourceVersion storage and retrieval publication remains in RF-2 generations.

Manifest V2 is an explicit allowlist. It requires exact governed repository identity, exact 40-character SHA-1 source commit/blob IDs, explicit active entries/retirements, lifecycle/authority/classification metadata, and chaining to the previous accepted manifest digest. Silent omission fails closed.

All listed sources are verified before writes. Apply revalidates source/state. The concrete Git adapter is server-configured, reads only exact manifest-listed regular blobs, uses argv subprocess calls with `shell=False`, and is qualified for SHA-1 Git repositories only. SHA-256-format Git repository support is not claimed.

Validated updates include content edit, rename-only, rename+edit continuity, duplicate-byte identity separation, classification-only metadata changes, explicit retirement retain/exclude, stale source/manifest rejection, failed-publication isolation/retry, exact replay idempotency, and exact import/source/resource/version/generation provenance.

Ordinary `create_app()` remains repository-import-incapable. Import capability requires `create_repository_import_app()` with host-injected governed readers. Client schemas expose no repository root/credentials, database URL, or artifact-store internals.

## Exact RI-2 validation

Checkpoint `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`, GitHub Actions run `34416061086`:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2: passed
Fast: 48 passed, 1 intentional historical-pilot skip, 17 deselected
PostgreSQL: 15 passed, 2 intentional historical-pilot skips, 49 deselected
Workflow: success
```

RI2-G1 through RI2-G18 all passed; see `REPOSITORY_IMPORT_RI2.md`.

## Current limitations / unclaimed capability

Knowledge Core does not yet claim:

- broad or production-scale persistent repository import;
- automatic repository discovery/classification/document-key assignment/rename heuristics;
- SHA-256 Git repository support;
- separately qualified reactivation-after-retirement semantics;
- canonical replacement/supersedes relationships beyond accepted manifest metadata;
- an import-specific semantic bootstrap profile name instead of the existing resource foundation bootstrap `resource-test`;
- chunking/section retrieval, PDF/DOCX/HTML extraction/OCR, embeddings/vector search, or RAG;
- production repository credential/network deployment;
- Authority, autonomous execution, or production backup/restore qualification.

## Durable restart point

Read before the next import task:

- `CURRENT_STATE.md`
- `REPOSITORY_IMPORT_RI1.md`
- `REPOSITORY_IMPORT_RI2.md`
- `RETRIEVAL_FOUNDATION_HANDOFF.md`
- `RETRIEVAL_FOUNDATION_RF2.md`
- `EXECUTION_GOVERNANCE.md`
- `components/knowledge-core/README.md`

Verify branch/HEAD before writing.

## Next separately authorized task

### RI-3 — tiny persistent operational import pilot

Candidate only: one human-approved Manifest V2, a very small Knowledge Core documentation set, deliberately configured persistent local PostgreSQL/artifact storage, plan/apply, service/process restart, exact accepted-manifest replay, current/historical retrieval, and provenance verification. Stop after recording findings.

RI-3 must not introduce automatic discovery or broaden into ACL/Vera/RiskCardOCR import, chunking, embeddings, RAG, semantic expansion, Authority, or execution.

## Stop boundary

**RI-2 is complete. Do not begin RI-3 without separate user authorization.**
