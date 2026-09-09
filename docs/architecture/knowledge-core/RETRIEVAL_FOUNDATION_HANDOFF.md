# Knowledge Core — Retrieval / Import Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RI-1 repository-import contract/design complete; RI-2 implementation not started**

## Accepted checkpoints

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`
- RF-1 retrieval design: `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`
- RF-2 retrieval implementation: `479a918762e919851e19fee3b36cc1d95e78f3e8`
- RF-2 CI: run `34371352821` — success
- First curated real-corpus pilot: `40849bd4de261089a030e09677568c3b4cf1a862`
- Real-corpus pilot CI: run `34373589343` — 48 fast + 11 PostgreSQL tests passed
- Pinned-pilot replay fence: `cbbc4f9e89b571f1d6dd7704f68aa393f03f6aa1`
- Replay-fence CI: run `34374450129` — success with intentional historical-fixture skips after source docs changed
- RI-1 design: `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md`

## Retrieval baseline

RF-2 remains accepted and unchanged. It retrieves exact whole `ResourceVersion` units using PostgreSQL full-text search, explicit lifecycle/authority metadata, exact source/version provenance, generation fencing, service-time restriction/deletion eligibility, and a service-only API. Supported indexable content remains strict UTF-8 `text/plain` and `text/markdown`.

The first real-corpus pilot proved RF-2 against ten exact Knowledge Core Markdown blobs from source commit `adb2a48a1e248f24e43550d897eed1b5e300cc26`. Four documents were current and six historical/superseded. No production RF-2 repair was required.

The pilot also proved that mutable current checkout bytes must never be relabeled as an older pinned commit. Historical replay now fails safe/skips if pinned source blobs differ; exact accepted replay evidence remains run `34373589343`.

## RI-1 accepted decisions

RI-1 defines the safe persistent repository-import contract before implementation.

### Stable identity

Path is not document identity.

Each managed repository has an immutable governed `source_repository_key`. Each managed logical document has an immutable explicit `source_document_key`.

The persistent identity binding is:

```text
(source_repository_key, source_document_key) -> Knowledge Core logical Resource ref
```

Consequences:

- same key + changed bytes -> same Resource, new ResourceVersion;
- same key + renamed path + same bytes -> same Resource and ResourceVersion, new path locator/source observation;
- same key + path and bytes both changed -> same Resource only with explicit continuity rationale in the manifest;
- different keys + identical bytes -> distinct logical Resources even if artifact bytes physically deduplicate;
- true replacement uses a new document key and explicit replacement/supersession metadata rather than stealing the old identity.

### Manifest chain

A future importer accepts only an explicit schema-versioned allowlist manifest pinned to an exact Git commit and exact blob IDs.

Each changed manifest names the SHA-256 digest of the previously accepted manifest. Every previously managed document key must appear either as a present entry or an explicit retirement. Silent omission is invalid.

The first implementation history policy is fixed to retain prior exact versions as `superseded` historical retrieval material unless an explicit retirement excludes them.

Retirement is retrieval/import lifecycle only. It is not privacy deletion or canonical erasure.

### Source verification

All Git verification completes before writes:

- exact immutable commit, not branch/tag/HEAD;
- exact manifest path at that commit;
- regular blob object only, not tree/symlink/submodule;
- exact Git blob ID match;
- recomputed Git blob identity from exact commit-object bytes;
- strict UTF-8 and RF-2-supported media type;
- independent artifact SHA-256 during Knowledge Core ingest.

The importer may read only explicit manifest paths/objects. It may not recursively scan, glob, or auto-add repository content.

### Durable import-control concepts

RI-1 requires persistent control state for:

1. repository-document bindings;
2. immutable repository source observations linking manifest/repo/document/commit/path/blob to exact ResourceVersion;
3. immutable import receipts chained by canonical manifest digest and recording resulting text generation.

Exact table names remain RI-2 implementation details.

### Plan/apply protocol

Dry-run produces a deterministic `ImportPlan` and performs no writes. It includes exact source proofs, expected previous manifest/current-generation preconditions, per-document actions, exact next generation source set, and plan digest.

Apply revalidates stale-sensitive source and state preconditions. No new text generation becomes current until the entire manifest settles. A failed/stale import leaves the previously current generation serving. Safely append-only resource/version residue may exist but is not represented as an accepted manifest or current generation.

Reapplying the exact accepted manifest is idempotent and must not create new Resources, ResourceVersions, locators, source observations, receipts, or text generations.

Classification-only changes create no ResourceVersion but do require a new import receipt and new retrieval generation.

## RI-2 acceptance boundary

`REPOSITORY_IMPORT_RI1.md` defines RI2-G1 through RI2-G18. They cover:

- bounded manifest validation;
- verify-all-before-write behavior;
- stable first-import bindings;
- exact replay idempotency;
- content update identity;
- rename-only behavior;
- rename-plus-edit continuity proof;
- duplicate-content identity separation;
- classification-only changes;
- omission fail-closed;
- explicit retirement retain/exclude semantics;
- stale manifest/generation rejection;
- source mutation between plan/apply;
- failed publication non-serving behavior;
- current-generation isolation;
- exact end-to-end provenance;
- service-only credential separation;
- instrumentation proving no broad repository scan.

The controlled fixtures are synthetic Git history plus one tiny pinned real fixture only. No broad ACL/Vera/RiskCardOCR corpus is authorized.

## Explicit non-goals

Do not start any of the following without separate authorization:

- broad or production repository import;
- repository-wide automatic discovery/classification;
- chunking or section-level retrieval;
- PDF/DOCX/HTML extraction or OCR;
- embeddings/vector retrieval;
- LLM summarization/RAG/context assembly;
- ACL/Vera semantic-profile expansion;
- production Authority/credentials/network deployment work;
- autonomous workers/action execution;
- Kernel V1 redesign.

## Startup instructions

For the next retrieval/import task:

1. Work on branch `architecture/knowledge-core`.
2. Read root `AGENTS.md`, `docs/START_HERE.md`, and `docs/CURRENT_STATE.md`.
3. Read:
   - `docs/architecture/knowledge-core/CURRENT_STATE.md`
   - `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`
   - `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
   - `components/knowledge-core/README.md`
4. Verify branch/HEAD before writing.
5. Preserve frozen Kernel V1 and accepted RF-2 behavior.
6. Perform only the separately authorized bounded task.

## Next separately authorized task

### RI-2 — minimal repository import implementation and controlled fixtures

RI-2 may implement only the smallest application/storage/source-reader/test slice necessary to satisfy RI2-G1 through RI2-G18 using synthetic and tiny-real fixtures.

It must stop before broad persistent import, chunking, embeddings, RAG, semantic expansion, Authority, deployment, or execution work.

## Stop boundary

**RI-1 is complete. Do not begin RI-2 until the user explicitly authorizes it.**
