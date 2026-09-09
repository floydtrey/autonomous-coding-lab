# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1 checkpoint:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification checkpoint:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**Retrieval Foundation RF-1 design checkpoint:** `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`  
**Retrieval Foundation RF-2 implementation checkpoint:** `479a918762e919851e19fee3b36cc1d95e78f3e8`  
**RF-2 CI:** run `34371352821` — 47 fast + 9 PostgreSQL tests passed  
**First curated real-corpus pilot:** `40849bd4de261089a030e09677568c3b4cf1a862`  
**Pilot CI:** run `34373589343` — 48 fast + 11 PostgreSQL tests passed  
**Pinned historical-pilot replay fence:** `cbbc4f9e89b571f1d6dd7704f68aa393f03f6aa1`  
**Replay-fence CI:** run `34374450129` — success  
**RI-1 design:** `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md`  
**Status:** **Kernel V1 remains frozen; PostgreSQL qualification, RF-1, RF-2, the first real-corpus pilot, and RI-1 repository-import design are complete. RI-2 implementation is not started. No broad or production corpus has been imported.**

This is the branch-specific controlling state for Knowledge Core. Earlier detailed evidence remains in the named durable records and exact commits/runs above; this page records the accepted current boundary rather than duplicating every historical gate.

## Accepted Kernel boundary

Kernel V1 remains frozen and accepted. Its semantic invariants include canonical revision history, versioned semantic profiles, typed assertions, bitemporal history, exact Resource/ResourceVersion identity, immutable artifact storage, provenance, reversible identity transitions, deletion/restriction serving fences, idempotent operations, stale-writer protection, derived-generation fencing, and service-only APIs.

Do not redesign Kernel V1 unless a concrete defect is demonstrated.

## PostgreSQL qualification

`POSTGRES_QUALIFICATION.md` records real PostgreSQL validation of the Alembic chain through `0008_task9`, stale-writer races, same-operation replay/contention, advisory locking, generation late-finisher fencing, and transaction rollback.

## Retrieval Foundation RF-1 / RF-2

`RETRIEVAL_FOUNDATION_RF1.md` is the accepted design/falsification record.

`RETRIEVAL_FOUNDATION_RF2.md` is the accepted implementation/completion record. RF-2 provides:

- PostgreSQL full-text retrieval through `kc_derived.resource_text_search`;
- exact whole-ResourceVersion retrieval units;
- strict UTF-8 `text/plain` and `text/markdown` indexing;
- explicit `current` / `unknown` / `superseded` lifecycle metadata;
- explicit authority ranking metadata;
- deterministic lexical ordering;
- exact repository/path/source-version/digest/generation result provenance;
- current-generation-only normal serving;
- deletion/restriction purge plus service-time eligibility fencing;
- service-only HTTP access with no database or artifact-store credentials exposed.

RF-2 production code did not require repair during the first real-corpus pilot.

## First curated real-corpus pilot

The exact ten-document Knowledge Core Markdown corpus at source commit `adb2a48a1e248f24e43550d897eed1b5e300cc26` was classified before ingest using `REAL_CORPUS_PILOT_MANIFEST.json`.

Four sources were ordinary/current retrieval material and six were historical/superseded. Exact source Git blob identities, retrieval expectations, and provenance were validated in CI run `34373589343`.

The pilot exposed two durable lessons:

1. whole-document lifecycle classification is safe but coarse when a document contains both still-valid design material and stale operational framing;
2. historical source bytes must never be replaced with current checkout bytes while retaining old commit provenance.

The replay fence at `cbbc4f9...` therefore skips the historical acceptance replay if pinned files no longer match their baseline Git blobs; run `34374450129` validates that fail-safe behavior.

## RI-1 — repository import contract and falsifiable acceptance design

Durable design:

`docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md`

RI-1 is complete as design only.

### Stable import identity

Repository path and content hash are not logical document identity.

A managed repository has a stable governed `source_repository_key`; each logical document has a stable explicit `source_document_key`. The persistent binding is:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource ref
```

This lets edits and renames preserve document identity while preventing two different documents with identical bytes from being merged.

### Exact source proof

A later importer must verify the entire manifest before writes using exact immutable Git commit/path/blob identity and exact object bytes. Working-tree substitution, symbolic branch identity, symlink/submodule/tree entries, path traversal, unsupported media, and blob mismatch fail closed.

The importer may read only manifest-listed Git objects/paths. No recursive scan, glob, or automatic repository discovery is part of RI-1.

### Manifest chain and omission safety

Every later accepted manifest names the exact SHA-256 digest of the previously accepted manifest. Every previously managed document key must either remain present or appear in an explicit retirement entry. Omission alone cannot retire, delete, or supersede a source.

Retirement controls retrieval membership/history only; it is not privacy erasure.

### Update semantics

- unchanged same manifest: exact idempotent replay, no new canonical/derived records;
- same key + changed bytes: same Resource, new ResourceVersion;
- same key + rename only: same Resource/ResourceVersion, new locator/source observation;
- same key + rename plus content change: requires explicit continuity rationale, then same Resource + new ResourceVersion;
- different keys + identical bytes: distinct logical Resources;
- classification-only update: no new ResourceVersion, but new accepted import receipt and text generation;
- true document replacement: new document key plus explicit replacement/supersession metadata.

The first implementation history policy is fixed to retain prior exact versions as `superseded` historical sources unless an explicit retirement excludes them.

### Plan/apply and publication fence

Dry-run must be non-mutating and deterministic. Apply must revalidate manifest/source/generation preconditions.

No new retrieval generation becomes current until the complete manifest settles. If apply fails or becomes stale, the previous current generation remains serving. Append-only intermediate resource/version records, if any, do not constitute an accepted import.

### Persistent control concepts selected

RI-1 requires durable state for:

- repository-document identity bindings;
- immutable repository source observations tied to exact ResourceVersion;
- immutable import receipts chained by canonical manifest digest and recording resulting text generation.

Exact schema/table names are deferred to RI-2.

### RI-2 falsification gates

RI-1 defines RI2-G1 through RI2-G18 covering bounded manifest validation, verify-all-before-write behavior, binding stability, exact replay idempotency, edit/rename/duplicate-content semantics, classification-only updates, explicit retirement, stale manifest/source rejection, failed-publication isolation, exact provenance, service-only credential separation, and instrumentation proving no broad repository scan.

Synthetic Git history plus one tiny explicitly pinned real fixture are the only authorized acceptance corpus shape for RI-2.

## Current limitations / unclaimed capability

Knowledge Core still does **not** claim:

- a working persistent repository importer;
- production/broad ACL, Vera, RiskCardOCR, research, or legacy corpus ingestion;
- automatic repository discovery or document classification;
- chunking or section-level lifecycle;
- PDF/DOCX/HTML extraction or OCR;
- embeddings/vector retrieval;
- LLM summarization/RAG/context assembly;
- ACL/Vera semantic-profile expansion;
- production Authority implementation;
- production repository/network credential deployment;
- autonomous workers or action execution.

## Durable restart point

For repository-import work, read:

- `CURRENT_STATE.md`
- `REPOSITORY_IMPORT_RI1.md`
- `RETRIEVAL_FOUNDATION_HANDOFF.md`
- `RETRIEVAL_FOUNDATION_RF2.md`
- `EXECUTION_GOVERNANCE.md`
- `components/knowledge-core/README.md`

Then verify branch/HEAD before writing.

## Next separately authorized task

### RI-2 — minimal repository import implementation and controlled fixtures

RI-2 may implement only what is required to satisfy RI2-G1 through RI2-G18 using synthetic and tiny-real fixtures. It must not expand into broad production import, chunking, embeddings, RAG, semantic expansion, Authority, deployment, or execution.

## Stop boundary

**RI-1 is complete. Do not begin RI-2 without separate user authorization.**
