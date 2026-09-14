# Knowledge Core Repository Import RI-2 — Completion Record

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**RI-1 design checkpoint:** `f7f12c04163ecbe3b6143191008cf393726b8def`  
**RI-2 validated implementation checkpoint:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`  
**Exact RI-2 CI:** GitHub Actions run `34416061086` — **success**  
**Historical status:** **RI-2 complete. Minimal governed repository import was implemented and validated with synthetic fixtures plus one tiny exact real-Git-object fixture.**  
**Post-acceptance clarification:** **2026-09-10 — A→B→A exact-version reuse and later section-projection observation lineage clarified by `KC-D025`; historical RI-2 qualification remains accepted.**

## Post-acceptance clarification — do not reinterpret historical evidence

The original RI-2 phrases “content edit ... creates one new ResourceVersion” and `G5 edit -> same Resource/new ResourceVersion` described the tested case in which the edited bytes were a **previously unseen exact representation**.

They do not override the accepted content-addressed uniqueness of exact versions. For the same logical Resource:

- previously unseen exact bytes/digest -> create one new `ResourceVersion`;
- exact bytes/digest already represented by any prior version -> reuse that existing `ResourceVersion`;
- therefore A → B → A reuses A's original exact version on the final A observation;
- the final A still records a new governed source observation/manifest receipt and may publish a new retrieval generation;
- the historical RI-2 CI run is **not** retroactively claimed to have tested A → B → A. That is a required regression case for later work.

For section retrieval, `KC-D025` and audit-amended `SECTION_RETRIEVAL_SR1.md` further require complete retrieval-generation lineage to identify the exact governed observation/classification snapshot used for lifecycle/source projection. RI-2 already stores immutable `repository_source_observation` records; the later SR-2 implementation must bind those governed inputs correctly. This clarification does not change the result of RI-2's historical whole-document qualification.

## Scope completed

RI-2 implemented the RI-1 repository-import contract required by its original RI2-G1 through RI2-G18 scope. Kernel V1 and RF-2 retrieval semantics remained unchanged at that checkpoint.

Implemented:

- `knowledge_core/domain/repository_import.py` — source proof, action, plan, and receipt snapshots;
- `knowledge_core/application/repository_source.py` — narrow repository-reader protocol and exact-object Git adapter;
- `knowledge_core/application/repository_import.py` — Manifest V2 validation, deterministic plan/apply, source revalidation, stable bindings, update/retirement semantics, retry reconciliation, and generation publication;
- `knowledge_core/storage/repository_import_models.py` — durable import-control state;
- import-capable service schemas/application boundary;
- migration `0010_ri2`;
- `tests/test_ri2_repository_import.py` — controlled historical acceptance matrix.

## Durable import state

Migration `0010_ri2` adds:

1. `kc_control.repository_document_binding` — stable `(source_repository_key, source_document_key) -> Resource` identity;
2. `kc_control.repository_import_receipt` — manifest chain, plan digest, source commit, status, accepted manifest JSON, resulting text generation;
3. `kc_control.repository_source_observation` — exact manifest/repository/document/commit/path/Git-blob observation tied to one Resource and exact ResourceVersion with retrieval classification metadata.

A later observation may validly point to a ResourceVersion used by an older observation when the exact content recurs.

## Accepted behavior

### Exact bounded source access

The importer receives server-configured `RepositorySourceReader` instances keyed by governed repository identity. A client cannot supply repository roots/credentials or request recursive traversal/globbing.

The concrete `GitRepositorySourceReader` resolves only manifest-listed exact commit/path objects through argv-based `git` calls with `shell=False`, accepts only regular blobs (`100644`/`100755`), and reads exact blob bytes.

RI-2 intentionally supports SHA-1 Git repositories only. Manifest commit/blob IDs and the adapter require exact 40-character lowercase SHA-1 object IDs. Git blob identity is recomputed from exact bytes before Knowledge Core ingest. SHA-256-format Git repository support is not claimed.

### Manifest V2 and verify-before-write

The implementation enforces schema version, governed repository key/locator, exact source commit, prior manifest digest, fixed history policy, explicit active entries/retirements, normalized non-glob paths, supported text media, explicit lifecycle/authority/classification/rationale, and exact Git blob IDs.

Duplicate keys/paths, traversal/globs, unsupported media, missing classification, stale manifest chains, source/blob mismatch, unsupported Git object types, and non-SHA-1 IDs fail closed.

`plan_repository_import()` verifies the allowlist before import/canonical writes. `apply_repository_import()` replans/reverifies source/state before applying.

### Stable identity and updates — clarified

- first import creates one stable binding per governed document key;
- exact accepted-manifest replay creates no new Resource, ResourceVersion, locator, observation, receipt, or text generation;
- content change to a previously unseen exact representation preserves Resource identity and creates one new ResourceVersion;
- return to an exact representation already present for the same Resource reuses that existing ResourceVersion while creating the new governed observation/receipt/generation required by the changed manifest;
- rename-only preserves Resource and exact ResourceVersion and records the new locator/source observation;
- rename plus source-content change requires explicit continuity rationale; exact-version creation versus reuse follows content-addressed identity;
- distinct document keys remain distinct Resources even when bytes are identical;
- classification-only changes reuse the exact ResourceVersion but publish a new receipt/generation;
- silent omission of a previously managed key fails closed;
- retirement `retain` keeps the last accepted version as superseded historical retrieval material;
- retirement `exclude` removes that document from the new retrieval generation without erasing canonical history.

### Publication and retry

A new import is not accepted until its text generation settles current. The historical suite injects failure after safe canonical work but before generation publication; the previous current generation remains serving. Exact retry reconciles binding/version/observation residue instead of duplicating it.

### Service boundary

Normal `create_app()` remains repository-import-incapable. The import-capable service exists only when the host supplies governed repository readers and retains `/v1/retrieval/search`. Client-visible schemas/results contain no DB URLs, artifact paths/keys, repository roots, or credentials.

## Historical RI2-G1 through RI2-G18 disposition

The original RI-2 run passed the following cases:

- G1 bounded schema/path/media/classification validation — passed
- G2 verify all listed sources before writes — passed
- G3 stable first-import bindings — passed
- G4 exact replay idempotency — passed
- G5 previously unseen content edit -> same Resource/new ResourceVersion — passed
- G6 rename-only -> same Resource/version + locator — passed
- G7 rename+edit requires continuity rationale — passed
- G8 identical bytes across different keys do not merge identity — passed
- G9 classification-only update creates no ResourceVersion — passed
- G10 omission fails closed — passed
- G11 explicit retirement retain/exclude — passed
- G12 stale manifest/state rejection — passed
- G13 source mutation after plan rejected — passed
- G14 failed publication remains non-serving; retry reconciles — passed
- G15 exactly one current text generation after update — passed
- G16 exact source/import/resource/version/generation provenance — passed
- G17 service-only credential separation — passed
- G18 instrumentation proves no unlisted repository read — passed

**A → B → A was not one of those historical fixtures and is not relabeled as passed.** The content-addressed implementation already searches for a matching prior version, but later work must preserve this behavior with an explicit regression test when the amended section-retrieval contract is aligned.

## Exact historical validation

GitHub Actions run `34416061086` checked out exact implementation checkpoint `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2: passed
Fast suite: 48 passed, 1 intentional historical-pilot skip, 17 deselected, 2 upstream warnings
PostgreSQL suite: 15 passed, 2 intentional historical-pilot skips, 49 deselected, 2 upstream warnings
Workflow conclusion: success
```

This remains valid historical evidence for the cases it ran.

## Relationship to audit-amended SR-1

RI-2 established the durable observation records that contain source commit/path/blob, exact ResourceVersion, classification, lifecycle, authority, and rationale.

Audit-amended SR-1 separates:

```text
structural segmentation
    = exact ResourceVersion + structural profile

complete lifecycle/source retrieval projection
    = structural segments
    + exact governed observation/classification snapshot
    + retrieval-projection profile
```

That is a later section-retrieval requirement. The pre-audit SR-2 candidate does not yet qualify it and must be aligned separately. No RI-2 production/runtime fix is performed by this documentation clarification.

## Known limitations / unqualified edges

RI-2 does not claim:

- SHA-256-format Git repository support;
- automatic repository discovery/classification/document-key assignment/rename heuristics;
- broad ACL/Vera/RiskCardOCR/research/legacy import;
- production-scale persistent corpus deployment;
- section-level lifecycle qualification under the later amended SR-1 contract;
- explicit historical A → B → A acceptance-test coverage at the RI-2 checkpoint;
- PDF/DOCX/HTML extraction/OCR, embeddings, or RAG;
- separately qualified reactivation-after-retirement semantics;
- canonical replacement/supersedes relationships beyond accepted manifest metadata;
- production repository credential/network deployment, Authority, autonomous execution, or production backup/restore qualification.

## Current precedence

For present section-retrieval work, read `CURRENT_STATE.md`, `DECISIONS.md` / `KC-D025`, and audit-amended `SECTION_RETRIEVAL_SR1.md` before using this completion record as guidance. This document remains the historical RI-2 completion evidence, with the exact-version clarification above.

## Stop boundary

**RI-2 remains accepted for its historical bounded scope. This documentation clarification does not apply SR-2 runtime/test fixes and does not authorize broad import, embeddings, RAG, Authority, or execution.**