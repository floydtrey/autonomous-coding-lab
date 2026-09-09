# Knowledge Core — Retrieval / Import Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **first curated real-corpus retrieval pilot complete — awaiting separate authorization for RI-1 repository-import design**  
**Frozen Kernel V1 checkpoint:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification checkpoint:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-1 design checkpoint:** `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`  
**RF-2 validated implementation checkpoint:** `479a918762e919851e19fee3b36cc1d95e78f3e8`  
**RF-2 CI:** GitHub Actions run `34371352821` — **success**  
**RF-2 completion record:** `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`  
**First real-corpus pilot checkpoint:** `40849bd4de261089a030e09677568c3b4cf1a862`  
**First real-corpus pilot CI:** GitHub Actions run `34373589343` — **success**  
**Pilot classification manifest:** `docs/architecture/knowledge-core/REAL_CORPUS_PILOT_MANIFEST.json`

## Purpose

This file is the durable restart point for Knowledge Core retrieval/import work. A fresh chat should recover state from the repository rather than relying on prior conversation context.

## Accepted baseline

Knowledge Core Kernel V1 remains frozen and accepted. Do not reopen or redesign its 19 accepted gates unless new evidence demonstrates a concrete defect.

Post-Kernel Slice 1 — PostgreSQL Qualification remains accepted. It proved the real Alembic chain through `0008_task9`, PostgreSQL application use, stale-writer serialization, same-operation-ID contention/replay, advisory-lock blocking, generation late-finisher fencing, and transactional rollback.

RF-1 — Retrieval design and falsifiable acceptance plan — is accepted in:

`docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`

RF-2 — synthetic-first PostgreSQL lexical retrieval implementation — is complete and recorded in:

`docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`

The first bounded real-corpus retrieval pilot is also complete. It validates RF-2 against exact repository Markdown rather than synthetic strings while deliberately avoiding production persistence or corpus expansion.

## RF-2 accepted behavior

RF-2 implements the smallest deterministic lexical retrieval foundation designed in RF-1:

- exact `resource_version_ref` is the retrieval unit;
- supported content is strict UTF-8 `text/plain` and `text/markdown` only;
- immutable artifact bytes remain outside PostgreSQL;
- `kc_derived.resource_text_search` stores a rebuildable `tsvector` projection and approved source metadata;
- PostgreSQL full-text retrieval uses fixed `english` configuration, `websearch_to_tsquery`, `@@`, and `ts_rank_cd`;
- a GIN index supports the text vector;
- text generations reuse `kc_derived.generation` / `generation_source` with `derived_kind='text'`;
- lifecycle (`current`, `unknown`, `superseded`) and source authority are explicit classification metadata, not inferred from recency, keywords, or paths;
- default search excludes superseded rows while explicit historical search can include them;
- ranking is deterministic: lexical score, lifecycle, authority rank, canonical revision, then exact ref;
- every returned result contains exact logical-resource/version/digest/source/generation provenance;
- normal retrieval uses only the current settled text generation;
- deletion/restriction purges derived lexical rows and service-time `resource_version_serving_eligible()` remains mandatory defense in depth;
- normal clients use `POST /v1/retrieval/search` with `X-Knowledge-Caller` and receive no database or artifact-store credentials/paths.

## Exact RF-2 validation

GitHub Actions run `34371352821` validated exact implementation commit:

`479a918762e919851e19fee3b36cc1d95e78f3e8`

Evidence:

```text
Alembic 0001_task1 -> 0009_rf2: passed
Fast semantic suite: 47 passed, 9 deselected, 2 upstream warnings
PostgreSQL suite: 9 passed, 47 deselected, 2 upstream warnings
Workflow conclusion: success
```

See `RETRIEVAL_FOUNDATION_RF2.md` for RF2-G1 through RF2-G14 gate disposition.

## First curated real-corpus pilot — complete

### Exact source boundary

The pilot used only the ten Markdown files present in:

`docs/architecture/knowledge-core/`

at exact source checkpoint:

`adb2a48a1e248f24e43550d897eed1b5e300cc26`

The checked-in `REAL_CORPUS_PILOT_MANIFEST.json` records every exact path and Git blob SHA plus explicit classification, retrieval lifecycle, authority rank, supersession note, and the known retrieval questions used for acceptance.

No path was discovered by a broad scanner and no file outside the manifest was ingested.

### Classification disposition

Ordinary/current retrieval includes exactly four sources:

- `CURRENT_STATE.md`;
- `EXECUTION_GOVERNANCE.md`;
- `RETRIEVAL_FOUNDATION_HANDOFF.md`;
- `RETRIEVAL_FOUNDATION_RF2.md`.

Historical mode additionally preserves six explicit superseded sources:

- `ARCHITECTURE_V1.md`;
- `DECISIONS.md`;
- `IMPLEMENTATION_PLAN_V1.md`;
- `PHYSICAL_SCHEMA_V1.md`;
- `POSTGRES_QUALIFICATION.md`;
- `RETRIEVAL_FOUNDATION_RF1.md`.

### Exact pilot validation

GitHub Actions run `34373589343` validated exact pilot commit:

`40849bd4de261089a030e09677568c3b4cf1a862`

Evidence:

```text
Alembic 0001_task1 -> 0009_rf2: passed
Fast semantic suite: 48 passed, 11 deselected, 2 upstream warnings
PostgreSQL suite: 11 passed, 48 deselected, 2 upstream warnings
Workflow conclusion: success
```

The new fast test verifies the ten-document manifest, exact baseline commit, exact path set, current/superseded counts, and every source Git blob identity.

The two new PostgreSQL tests ingest the exact real Markdown bytes into ephemeral Knowledge Core storage, build one current text generation, execute the predeclared known queries, and verify exact repository/path/commit/digest/resource-version/generation provenance. They also verify the same curated generation through the normal HTTP service-only boundary.

The pilot passed without modification to RF-2 production code.

## Material finding — mixed-status documents

Whole-resource-version classification is safe but coarse.

`ARCHITECTURE_V1.md` and `DECISIONS.md` contain substantial still-valid architecture/decision content while also retaining stale operational statements such as `Kernel implementation not yet started` or obsolete next-task instructions. RF-2 has no section/chunk lifecycle layer, so marking those files `current` would allow stale instructions into ordinary retrieval.

The pilot therefore marks both whole documents `superseded`. This safely suppresses stale operational text but also hides still-valid sections from default retrieval.

Do not infer a fix. A later separately authorized task may choose document refresh/splitting, section-level classification, or a chunk/extraction design. Until then, whole-document manifest classification is intentionally fail-safe.

## Why broad repository/document import remains deferred

Do **not** copy all ACL, Vera, RiskCardOCR, benchmark, research, or legacy documentation into Knowledge Core.

The first real-corpus pilot proves that curated lifecycle classification can protect ordinary retrieval, but it does not establish a safe persistent repository-import/update protocol. A broad import would still leave unresolved questions about stable logical-resource identity across commits, path rename/move, duplicate bytes, deletion, re-import idempotency, manifest evolution, and exact source verification.

## Next separately authorized task

### RI-1 — repository import contract and falsifiable acceptance design

RI-1 is **not started** and requires separate authorization.

RI-1 should be design/acceptance only. It should define the smallest safe contract for later persistent import of an approved manifest, including:

1. exact repository/commit/path/blob identity checks before ingest;
2. stable mapping from approved source identity to logical Knowledge Core `Resource` identity;
3. exact version creation when source bytes change without trusting mutable path alone;
4. rename/move semantics distinct from duplicate-content semantics;
5. explicit lifecycle/authority classification validation rather than inference;
6. re-run/idempotency behavior for an unchanged manifest;
7. changed-manifest behavior and text-generation replacement without old/current mixing;
8. deletion/removal/supersession handling;
9. bounded dry-run/fail-closed behavior that cannot silently scan or ingest unapproved paths;
10. service-only/credential separation requirements;
11. synthetic and tiny-real fixtures that falsify the import identity/update contract before implementation.

RI-1 must not implement a broad importer, persist a production corpus, add chunking, embeddings, RAG, or expand into ACL/Vera semantics.

## Explicit non-goals still in force

Do not begin any of the following without separate authorization:

- persistent/bulk repository import;
- repository-wide documentation review in one task;
- broad directory scanning/import discovery;
- PDF/DOCX/HTML extraction, OCR, or arbitrary binary parsing;
- chunking or section-level retrieval;
- embeddings/vector retrieval;
- LLM summarization/RAG;
- ACL-specific semantic profiles;
- Vera-specific semantic profiles;
- Authority implementation;
- autonomous workers or action execution;
- Kernel V1 redesign;
- production deployment/security/backup expansion.

## Startup instructions for the next Knowledge Core retrieval/import chat

Before changing anything:

1. Work from branch `architecture/knowledge-core`.
2. Read:
   - `docs/architecture/knowledge-core/CURRENT_STATE.md`
   - `docs/architecture/knowledge-core/POSTGRES_QUALIFICATION.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
   - `docs/architecture/knowledge-core/REAL_CORPUS_PILOT_MANIFEST.json`
   - `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
   - `components/knowledge-core/README.md`
3. Verify the current branch/HEAD before writing.
4. Inspect current resource/retrieval/generation code only if implementation is in scope.
5. Preserve the frozen Kernel boundary and exact-version provenance.
6. Perform only the separately authorized bounded task and stop.

## Stop boundary

**The first curated real-corpus pilot is complete. Stop here. Do not begin RI-1, persistent import, broader corpus expansion, chunking, embeddings, RAG, semantic-profile expansion, Authority, or execution work without separate authorization.**
