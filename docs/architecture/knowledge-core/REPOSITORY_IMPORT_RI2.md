# Knowledge Core Repository Import RI-2 — Completion Record

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**RI-1 design checkpoint:** `f7f12c04163ecbe3b6143191008cf393726b8def`  
**RI-2 validated implementation checkpoint:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`  
**Exact RI-2 CI:** GitHub Actions run `34416061086` — **success**  
**Status:** **RI-2 complete. Minimal governed repository import is implemented and validated with synthetic fixtures plus one tiny exact real-Git-object fixture. No broad or production corpus has been imported.**

## Scope completed

RI-2 implements only the RI-1 repository-import contract required to satisfy RI2-G1 through RI2-G18. Kernel V1 and RF-2 retrieval semantics remain unchanged.

Implemented:

- `knowledge_core/domain/repository_import.py` — source proof, action, plan, and receipt snapshots;
- `knowledge_core/application/repository_source.py` — narrow repository-reader protocol and exact-object Git adapter;
- `knowledge_core/application/repository_import.py` — Manifest V2 validation, deterministic plan/apply, source revalidation, stable bindings, update/retirement semantics, retry reconciliation, and generation publication;
- `knowledge_core/storage/repository_import_models.py` — durable import-control state;
- `knowledge_core/api/repository_import_schemas.py` and `repository_import_app.py` — explicitly import-capable service surface;
- migration `0010_ri2`;
- `tests/test_ri2_repository_import.py` — controlled acceptance matrix.

## Durable import state

Migration `0010_ri2` adds:

1. `kc_control.repository_document_binding` — stable `(source_repository_key, source_document_key) -> Resource` identity;
2. `kc_control.repository_import_receipt` — manifest chain, plan digest, source commit, status, accepted manifest JSON, resulting text generation;
3. `kc_control.repository_source_observation` — exact manifest/repository/document/commit/path/Git-blob observation tied to one Resource and exact ResourceVersion with retrieval classification metadata.

## Accepted behavior

### Exact bounded source access

The importer receives server-configured `RepositorySourceReader` instances keyed by governed repository identity. A client cannot supply repository roots or credentials and cannot request recursive traversal/globbing.

The concrete `GitRepositorySourceReader` resolves only manifest-listed exact commit/path objects through argv-based `git` calls with `shell=False`, accepts only regular blobs (`100644`/`100755`), and reads exact blob bytes.

RI-2 intentionally supports **SHA-1 Git repositories only**. Manifest commit/blob IDs and the concrete adapter both require exact 40-character lowercase SHA-1 object IDs. Git blob identity is recomputed independently from the exact bytes before Knowledge Core ingest. SHA-256-format Git repository support is not claimed.

### Manifest V2 and verify-before-write

The implementation enforces schema version, governed repository key/locator, exact source commit, previous accepted manifest digest, fixed history policy, explicit active entries, explicit retirements, normalized non-glob paths, supported text media, explicit lifecycle/authority/classification/rationale, and exact Git blob IDs.

Duplicate keys/paths, traversal/globs, unsupported media, missing classification, stale manifest chains, source/blob mismatch, symlink/submodule/tree objects, and non-SHA-1 object IDs fail closed.

`plan_repository_import()` verifies the full allowlist before any import/canonical write. `apply_repository_import()` replans/reverifies source/state before applying.

### Stable identity and updates

- first import creates one stable binding per governed document key;
- exact accepted-manifest replay creates no new Resource, ResourceVersion, locator, observation, receipt, or text generation;
- content edit preserves Resource identity and creates one new ResourceVersion;
- rename-only preserves Resource and exact ResourceVersion and records the new locator/source observation;
- rename plus edit requires explicit continuity rationale;
- distinct document keys remain distinct Resources even when bytes are identical;
- classification-only changes reuse the exact ResourceVersion but publish a new receipt/generation;
- silent omission of any previously managed key fails closed;
- retirement `retain` keeps the last accepted version as superseded historical retrieval material;
- retirement `exclude` removes that document from the new retrieval generation without erasing canonical history.

### Publication and retry

A new import is not accepted until its RF-2 text generation settles current. The suite injects failure after append-only canonical work but before generation publication; the previous current generation remains serving. Exact retry reconciles existing binding/version/observation residue instead of duplicating it.

### Service boundary

Ordinary `create_app()` remains repository-import-incapable. `create_repository_import_app()` exists only when the host supplies governed repository readers and adds:

- `POST /v1/repository-import/plan`
- `POST /v1/repository-import/apply`

while retaining `/v1/retrieval/search`. Client-visible schemas/results contain no database URLs, artifact paths/keys, repository roots, or repository credentials.

## RI2-G1 through RI2-G18

All RI-1 gates passed:

- G1 bounded schema/path/media/classification validation — **passed**
- G2 verify all listed sources before writes — **passed**
- G3 stable first-import bindings — **passed**
- G4 exact replay idempotency — **passed**
- G5 edit -> same Resource/new ResourceVersion — **passed**
- G6 rename-only -> same Resource/version + locator — **passed**
- G7 rename+edit requires continuity rationale — **passed**
- G8 identical bytes across different keys do not merge identity — **passed**
- G9 classification-only update creates no ResourceVersion — **passed**
- G10 omission fails closed — **passed**
- G11 explicit retirement retain/exclude — **passed**
- G12 stale manifest/state rejection — **passed**
- G13 source mutation after plan rejected — **passed**
- G14 failed publication remains non-serving; retry reconciles — **passed**
- G15 exactly one current text generation after update — **passed**
- G16 exact source/import/resource/version/generation provenance — **passed**
- G17 service-only credential separation — **passed**
- G18 instrumentation proves no unlisted repository read — **passed**

## Exact validation

GitHub Actions run `34416061086` checked out exact implementation checkpoint `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2: passed
Fast suite: 48 passed, 1 intentional historical-pilot skip, 17 deselected, 2 upstream warnings
PostgreSQL suite: 15 passed, 2 intentional historical-pilot skips, 49 deselected, 2 upstream warnings
Workflow conclusion: success
```

The historical-pilot skips are the existing pinned RF-2 real-corpus replay fence and are unrelated to RI-2 correctness.

## Known limitations / unqualified edges

RI-2 does not claim:

- SHA-256-format Git repository support;
- automatic repository discovery/classification/document-key assignment/rename heuristics;
- broad ACL/Vera/RiskCardOCR/research/legacy import;
- production-scale persistent corpus deployment;
- chunking/section-level lifecycle, PDF/DOCX/HTML extraction/OCR, embeddings, or RAG;
- separately qualified reactivation-after-retirement semantics;
- canonical replacement/supersedes relationships beyond accepted manifest metadata;
- an import-specific semantic bootstrap profile name (RI-2 reuses the existing resource foundation bootstrap currently named `resource-test`);
- immutable database rows for operational receipt status transitions; receipts progress through applying/failed/settled while a settled manifest digest is the accepted replay identity;
- production repository credential/network deployment, Authority, autonomous execution, or production backup/restore qualification.

## Next separately authorized task

Candidate RI-3: **tiny persistent operational import pilot** using one human-approved Manifest V2 and only a small Knowledge Core documentation set, deliberately configured persistent local PostgreSQL/artifact storage, process/service restart, exact replay, current/historical retrieval, and exact provenance verification.

Do not add automatic discovery or expand to broad ACL/Vera/RiskCardOCR import. Chunking, embeddings, RAG, semantic expansion, Authority, and execution remain separate future tasks.

## Stop boundary

**RI-2 is complete. Do not begin RI-3 or broader/persistent corpus import without separate user authorization.**
