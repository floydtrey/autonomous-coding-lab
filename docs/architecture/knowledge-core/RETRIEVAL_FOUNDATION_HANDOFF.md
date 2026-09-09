# Knowledge Core — Retrieval Foundation Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RF-2 complete — awaiting separate authorization for any real-corpus/import work**  
**Frozen Kernel V1 checkpoint:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification checkpoint:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-1 design checkpoint:** `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`  
**RF-2 validated implementation checkpoint:** `479a918762e919851e19fee3b36cc1d95e78f3e8`  
**RF-2 CI:** GitHub Actions run `34371352821` — **success**  
**RF-2 completion record:** `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`

## Purpose

This file is the durable restart point for Knowledge Core Retrieval Foundation work. A fresh chat should recover state from the repository rather than relying on prior conversation context.

## Accepted baseline

Knowledge Core Kernel V1 remains frozen and accepted. Do not reopen or redesign its 19 accepted gates unless new evidence demonstrates a concrete defect.

Post-Kernel Slice 1 — PostgreSQL Qualification remains accepted. It proved the real Alembic chain through `0008_task9`, PostgreSQL application use, stale-writer serialization, same-operation-ID contention/replay, advisory-lock blocking, generation late-finisher fencing, and transactional rollback.

RF-1 — Retrieval design and falsifiable acceptance plan — is accepted in:

`docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`

RF-2 — synthetic-first PostgreSQL lexical retrieval implementation — is complete and recorded in:

`docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`

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

The PostgreSQL tests include the five prior PostgreSQL qualification tests plus four RF-2 test functions whose assertions cover RF2-G1 through RF2-G14. See `RETRIEVAL_FOUNDATION_RF2.md` for gate-by-gate disposition.

## Why bulk repository/document import remains deferred

Do **not** copy all ACL, Vera, RiskCardOCR, benchmark, research, or legacy documentation into Knowledge Core.

The repository corpus contains current authoritative documentation, supporting material, historical records, superseded designs, completed plans, research/evidence, temporary handoffs/debug notes, and duplicates/renames. Indiscriminate ingestion would undermine the explicit lifecycle/authority model that RF-2 was built to test.

The later **Knowledge Import Campaign** still needs bounded repository-by-repository review and classification before ingestion.

## Candidate next separately authorized task

### Small curated real-corpus pilot

This is **not started** and is not authorized by this handoff alone.

When separately authorized, the next retrieval/import slice should remain bounded and begin with classification before ingestion:

1. select one bounded repository/document area;
2. inventory a small candidate set rather than the whole monorepo;
3. classify each document as current authoritative, current supporting, historical/superseded, research/evidence, temporary/debug, duplicate/renamed, or excluded;
4. record exact repository/path/commit or source-version provenance;
5. map current/superseded relationships explicitly;
6. approve a small ingest batch (roughly tens of documents, not hundreds/thousands);
7. ingest only supported text/Markdown material unless a separate extraction task is authorized;
8. define known questions/expected sources before retrieval testing;
9. validate the RF-2 retrieval behavior against that approved real corpus;
10. stop before expansion.

If real-corpus work exposes a concrete defect in RF-2, repair that defect as a bounded retrieval task instead of hiding it by importing more material.

## Explicit non-goals still in force

Do not begin any of the following without separate authorization:

- bulk repository import;
- repository-wide documentation review in one task;
- PDF/DOCX/HTML extraction, OCR, or arbitrary binary parsing;
- chunking;
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
   - `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
   - `components/knowledge-core/README.md`
3. Verify the current branch/HEAD before writing.
4. Inspect current resource/retrieval/generation/deletion/API code if implementation is in scope.
5. Preserve the frozen Kernel boundary and exact-version provenance.
6. Perform only the separately authorized bounded task and stop.

## Stop boundary

**RF-2 is complete. Stop here. Do not begin real-corpus ingestion, embeddings, RAG, semantic-profile expansion, Authority, or execution work without separate authorization.**
