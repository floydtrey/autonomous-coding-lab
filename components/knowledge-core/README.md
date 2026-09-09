# Knowledge Core

This component contains the frozen Knowledge Core Kernel plus accepted PostgreSQL, lexical-retrieval, curated real-corpus, and governed repository-import slices.

## Current state

**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-2 lexical retrieval:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**First curated real-corpus pilot:** `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`  
**RI-1 repository-import design:** `f7f12c04163ecbe3b6143191008cf393726b8def`  
**RI-2 governed repository-import implementation:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**Status:** **Kernel V1 remains frozen. Minimal governed repository import is implemented and qualified. No broad or production corpus is imported.**

Controlling state is `docs/architecture/knowledge-core/CURRENT_STATE.md`; RI-2 completion is `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md`.

## Accepted foundation

Kernel V1 provides canonical/versioned knowledge semantics, exact Resource/ResourceVersion identity, immutable SHA-256 artifacts, provenance, operation idempotency/stale-write protection, deletion/restriction fences, identity transitions, generation fencing, and service-only APIs.

RF-2 provides PostgreSQL whole-ResourceVersion lexical retrieval through `kc_derived.resource_text_search` with strict UTF-8 text/Markdown, explicit lifecycle/authority metadata, deterministic ranking, current-generation-only serving, exact result provenance, and deletion/restriction serving fences.

## RI-2 governed repository import

Stable document identity is:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Path and content hash are not logical identity.

Migration `0010_ri2` adds:

- `kc_control.repository_document_binding`;
- `kc_control.repository_import_receipt`;
- `kc_control.repository_source_observation`.

Manifest V2 is an explicit fail-closed allowlist chained to the previously accepted manifest. All listed source objects are verified before writes; silent omission of a managed document key is invalid; retirements are explicit retain/exclude retrieval dispositions.

The concrete `GitRepositorySourceReader` is server-configured and reads only exact manifest-listed regular blobs. RI-2 supports **SHA-1 Git repositories only**: exact 40-character lowercase commit/blob IDs with independent Git blob identity recomputation from exact bytes. There is no recursive discovery, globbing, or client-supplied repository root/credential.

Validated behavior includes exact replay idempotency, content edits, rename-only, rename+edit continuity, duplicate-byte identity separation, classification-only changes, explicit retirement, stale source/manifest rejection, failed-publication isolation/retry, generation isolation, and exact source/import/resource/version/generation provenance.

The ordinary `create_app()` remains repository-import-incapable. `create_repository_import_app()` adds `/v1/repository-import/plan` and `/v1/repository-import/apply` only when the host injects governed source readers. Client-visible contracts do not expose database URLs, artifact internals, repository roots, or repository credentials.

## Exact RI-2 validation

Checkpoint `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`, run `34416061086`:

```text
PostgreSQL 18
Alembic 0001_task1 -> 0010_ri2: passed
Fast: 48 passed, 1 intentional historical-pilot skip, 17 deselected
PostgreSQL: 15 passed, 2 intentional historical-pilot skips, 49 deselected
Workflow: success
```

RI2-G1 through RI2-G18 are recorded in `REPOSITORY_IMPORT_RI2.md`.

## Explicit limitations / debt

Current acceptance does not claim broad/production corpus import; automatic discovery/classification/document-key assignment/rename heuristics; SHA-256-format Git repository support; chunking/section retrieval; PDF/DOCX/HTML extraction/OCR; embeddings/RAG; production repository credential/network deployment; Authority; or autonomous execution.

Reactivation-after-retirement is not separately qualified. Replacement/supersedes metadata remains in accepted manifest metadata rather than a new canonical semantic relationship. RI-2 also reuses the existing resource bootstrap whose stable profile name remains `resource-test`; production semantic naming is future hardening.

## Development

Python 3.12+:

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

PostgreSQL migrations:

```powershell
alembic upgrade head
```

Set `KNOWLEDGE_CORE_DATABASE_URL` before applying migrations. Client applications must never receive that credential.

## Next boundary

The next separately authorized candidate is **RI-3 — tiny persistent operational import pilot**: one human-approved Manifest V2, a very small Knowledge Core documentation set, deliberately configured persistent local PostgreSQL/artifact storage, process/service restart, exact replay, retrieval, and provenance verification.

Do not broaden into automatic repository import, ACL/Vera/RiskCardOCR corpus ingestion, chunking, embeddings/RAG, Authority, or execution without separate authorization.
