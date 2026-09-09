# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Kernel V1 starting architecture checkpoint:** `dfdaaa45887cb882a05c929a3166981cc0528595`  
**Task 10 checkpoint:** `ea8ff441133329dfc19b631ed0172cdf12561704`  
**Gate 19 validated implementation head:** `2bdbc2a161bd2756fa7139ecefd4ca8b160f148e`  
**Frozen Kernel V1 checkpoint:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**Exact Kernel freeze validation:** GitHub Actions run `34350709966` — **47 passed, 2 upstream warnings**  
**PostgreSQL qualification checkpoint:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**PostgreSQL qualification validation:** GitHub Actions run `34364589918` — **47 fast semantic tests + 5 PostgreSQL qualification tests passed**  
**Retrieval Foundation RF-1 design checkpoint:** `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`  
**Retrieval Foundation RF-2 validated implementation checkpoint:** `479a918762e919851e19fee3b36cc1d95e78f3e8`  
**RF-2 validation:** GitHub Actions run `34371352821` — **47 fast semantic tests + 9 PostgreSQL tests passed**  
**First curated real-corpus pilot checkpoint:** `40849bd4de261089a030e09677568c3b4cf1a862`  
**Real-corpus pilot validation:** GitHub Actions run `34373589343` — **48 fast tests + 11 PostgreSQL tests passed**  
**Status:** **Knowledge Core Kernel V1 remains frozen and accepted; PostgreSQL Qualification, RF-1/RF-2 retrieval foundation, and the first curated real-corpus retrieval pilot are complete. No persistent production corpus has been imported. Awaiting separate authorization for repository-import design.**

This is the branch-specific controlling acceptance record for Knowledge Core. It does not replace repository-wide `docs/CURRENT_STATE.md`. The frozen Kernel boundary remains `9e904f49480055615bb0cf32360dbdc8400e117c`; post-Kernel integration/retrieval/import-pilot work does not reopen its 19 accepted semantic gates.

## Accepted Kernel boundary

Kernel V1 includes:

- canonical revisions and universal knowledge refs;
- immutable/versioned semantic profiles, kinds, and predicates;
- atomic typed assertions and reference-valued relationships;
- append-only correction/reversal history;
- independent world-valid and knowledge-record time;
- conflict-preserving, rebuildable current assertion projection;
- operation IDs, deterministic request digests, idempotent replay, stale-writer protection, and serialized PostgreSQL managed writes;
- exact logical-resource/resource-version identity, immutable SHA-256 artifact storage, locator history, and traversable provenance;
- reversible identity merge/split semantics and replacement-not-equivalence;
- deletion/restriction serving fences, bounded assertion tombstoning, and anti-resurrection reconciliation;
- append-only semantic-profile activation and exact assertion semantic pinning;
- derived-generation lineage plus monotonic out-of-order settlement fencing;
- FastAPI/Pydantic semantic service routes;
- managed exact-resource ingest and serving-safe resource/provenance reads;
- a service-only Gate 19 simulated Vera/ACL client with no database or artifact-store credentials.

Kernel V1 acceptance remains anchored at the exact frozen checkpoint and CI above. Do not redesign these semantics as part of later retrieval/import work unless a concrete regression or design defect is demonstrated.

## Post-Kernel Slice 1 — PostgreSQL Qualification

Durable record:

`docs/architecture/knowledge-core/POSTGRES_QUALIFICATION.md`

PostgreSQL Qualification proved the actual Alembic chain through `0008_task9`, application-layer PostgreSQL use, independent-session stale-writer races, same-operation-ID contention/replay, advisory transaction locking, generation late-finisher fencing, and rollback of partially flushed canonical work.

Exact validation at `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`, run `34364589918`:

```text
Alembic 0001_task1 -> 0008_task9: passed
Fast semantic suite: 47 passed, 5 deselected, 2 upstream warnings
PostgreSQL qualification suite: 5 passed, 47 deselected, 2 upstream warnings
Workflow conclusion: success
```

## Post-Kernel Slice 2 — Retrieval Foundation

### RF-1 — design and falsifiable acceptance plan

Durable design:

`docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`

RF-1 established exact `resource_version_ref` provenance, immutable artifact bytes outside PostgreSQL, PostgreSQL native full-text search, explicit lifecycle/authority metadata, deterministic ranking, derived-generation lineage, mandatory serving-fence enforcement, and a service-only API contract before implementation.

### RF-2 — synthetic PostgreSQL lexical retrieval

Durable completion record:

`docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`

Validated implementation checkpoint:

`479a918762e919851e19fee3b36cc1d95e78f3e8`

RF-2 implements:

- migration `0009_rf2` and `kc_derived.resource_text_search`;
- PostgreSQL `TSVECTOR`, GIN indexing, `websearch_to_tsquery`, `@@`, and `ts_rank_cd`;
- strict UTF-8 `text/plain` and `text/markdown` indexing from exact immutable artifacts;
- no raw decoded document body stored in PostgreSQL;
- exact resource-version plus generation-source lineage;
- explicit lifecycle (`current`, `unknown`, `superseded`) and authority metadata supplied by classification, not inferred from recency/keywords;
- default superseded exclusion with explicit historical inclusion;
- deterministic ranking by lexical score, lifecycle, authority, canonical revision, and exact ref;
- current text-generation-only serving;
- deletion/restriction purge integration plus mandatory service-time resource-version serving eligibility;
- `POST /v1/retrieval/search` behind the existing `X-Knowledge-Caller` boundary;
- exact result provenance without database/artifact-store secrets or internal storage locations.

Exact RF-2 CI run `34371352821` checked out `479a918762e919851e19fee3b36cc1d95e78f3e8` and reported:

```text
Alembic 0001_task1 -> 0009_rf2: passed
Fast semantic suite: 47 passed, 9 deselected, 2 upstream warnings
PostgreSQL suite: 9 passed, 47 deselected, 2 upstream warnings
Workflow conclusion: success
```

## Post-Kernel Slice 3 — first curated real-corpus retrieval pilot

The first real-corpus pilot is complete at:

`40849bd4de261089a030e09677568c3b4cf1a862`

Controlling classification manifest:

`docs/architecture/knowledge-core/REAL_CORPUS_PILOT_MANIFEST.json`

The pilot deliberately used only the ten Markdown documents that existed under `docs/architecture/knowledge-core/` at exact source checkpoint:

`adb2a48a1e248f24e43550d897eed1b5e300cc26`

The manifest pins every path to its exact Git blob SHA and records a human-reviewed classification, retrieval lifecycle, authority rank, supersession note, and a set of known queries before retrieval validation.

### Pilot classification

Four documents were admitted to ordinary current retrieval:

- `CURRENT_STATE.md` — current authoritative;
- `EXECUTION_GOVERNANCE.md` — current authoritative;
- `RETRIEVAL_FOUNDATION_HANDOFF.md` — current authoritative;
- `RETRIEVAL_FOUNDATION_RF2.md` — current authoritative.

Six documents were retained in the same derived generation as explicit `superseded`/historical material:

- `ARCHITECTURE_V1.md` — historical design;
- `DECISIONS.md` — historical/mixed whole-document classification;
- `IMPLEMENTATION_PLAN_V1.md` — completed plan;
- `PHYSICAL_SCHEMA_V1.md` — pre-DDL historical design;
- `POSTGRES_QUALIFICATION.md` — historical qualification evidence;
- `RETRIEVAL_FOUNDATION_RF1.md` — historical design/falsification record.

This classification is explicit. It is not inferred from file age, path, commit order, keyword score, or ingestion order.

### Exact pilot validation

GitHub Actions run `34373589343` checked out exact pilot commit `40849bd4de261089a030e09677568c3b4cf1a862`, applied the existing Alembic chain through `0009_rf2`, and reported:

```text
Fast semantic suite: 48 passed, 11 deselected, 2 upstream warnings
PostgreSQL suite: 11 passed, 48 deselected, 2 upstream warnings
Workflow conclusion: success
```

The additional fast test proves the manifest is exactly bounded to ten unique approved Markdown paths and that every checked-out source byte sequence still matches the Git blob identity recorded from source checkpoint `adb2a48a...`.

The two additional PostgreSQL tests ingest the exact repository document bytes through existing immutable resource/version storage, create one current RF-2 text generation, execute the predeclared known queries, and prove:

- ordinary `Knowledge Core` retrieval exposes exactly the four current documents;
- explicit historical mode can recover all ten documents;
- stale quoted status such as `Kernel implementation not yet started` is not served by default but is recoverable historically;
- the pre-DDL `accepted physical-schema architecture candidate` statement is likewise historical-only;
- current retrieval questions resolve to the intended current state/governance/RF-2 documents;
- each result retains the exact repository, source path, baseline source commit, resource ref, exact resource-version ref, SHA-256 content digest, lifecycle classification, authority rank, and current retrieval generation;
- the same curated generation is accessible through the normal HTTP service boundary with only `X-Knowledge-Caller` and without artifact/database internals.

No RF-2 production code repair was required. The synthetic design survived the first real-document corpus unchanged.

### Material finding — whole-document granularity is safe but coarse

The pilot exposed a real import-quality issue rather than a retrieval defect.

`ARCHITECTURE_V1.md` and `DECISIONS.md` contain substantial still-useful architecture/decision material, but they also contain stale whole-document operational framing such as `Kernel implementation not yet started` or obsolete next-task instructions. RF-2 currently retrieves at exact whole-resource-version granularity, so it cannot mark one section current and another section superseded.

For safety, the pilot classified those entire documents as historical/superseded. That prevents stale instructions from ordinary retrieval, but it also reduces recall of still-valid material inside them.

Do **not** silently solve this by adding chunking. A later task may choose among document refresh/splitting, section-level classification, or a separately designed chunk/extraction stage. Until then, manifest-level whole-document classification remains fail-safe.

## Current retrieval/import boundary

The accepted system now proves synthetic and small curated real-corpus lexical retrieval, but it is not yet a persistent repository-import system or RAG stack.

Current accepted limitations:

- retrieval is PostgreSQL-only;
- only strict UTF-8 `text/plain` and `text/markdown` are indexable;
- search is whole-resource-version lexical retrieval, not chunk retrieval;
- lifecycle/currentness and source authority must be supplied by an approved classification/import process;
- lexical rank is not truth, authorization, or execution authority;
- the real-corpus pilot uses ephemeral CI PostgreSQL/artifact storage and does not establish a persistent production corpus;
- there is no accepted general repository-import identity/update contract yet.

## Explicitly unclaimed / remaining integration debt

The accepted Kernel, PostgreSQL qualification, RF-2 foundation, and first real-corpus pilot do **not** claim:

- persistent repository/document import into a deployed Knowledge Core database;
- a general repository manifest/import/update command;
- repository-wide ACL/Vera/RiskCardOCR documentation classification;
- path rename/move handling across import runs;
- logical-resource identity reuse across repository revisions;
- PDF/DOCX/HTML extraction, OCR, or arbitrary binary parsing;
- chunking or section-level lifecycle classification;
- embeddings/vector retrieval;
- LLM summarization/RAG;
- ACL-specific semantic profiles;
- Vera-specific semantic profiles;
- production authentication, TLS, firewall/network policy, or real Authority-service implementation;
- production backup/restore orchestration or multi-service privacy reconciliation;
- autonomous workers or action execution;
- production process-boundary deployment qualification.

## Next separately authorized retrieval/import task

Do not start automatically.

### RI-1 — repository import contract and falsifiable acceptance design

Before persisting a real corpus, define the smallest safe import/update contract for an approved manifest. RI-1 should be design/acceptance only and answer at least:

- how an approved repository/path/blob/commit maps to stable Knowledge Core logical `Resource` identity;
- how later exact versions of the same logical document are detected without trusting mutable path alone;
- how rename/move, duplicate content, deletion, and explicit supersession are represented;
- how manifest lifecycle/authority classification is validated rather than inferred;
- how re-running the same manifest is idempotent;
- how a changed manifest creates a new exact resource version and a new text generation without mixing old/current generations;
- how source Git identity is checked before artifact ingest;
- how dry-run/fail-closed behavior prevents accidental broad scans or unapproved files;
- how service clients remain database/artifact-credential free;
- which controlled fixtures falsify identity/update/supersession behavior before a persistent import utility is implemented.

RI-1 must not implement chunking, embeddings, RAG, broad repository scanning, or production deployment.

## Durable restart point

For the next Knowledge Core retrieval/import chat, read:

- `CURRENT_STATE.md`
- `POSTGRES_QUALIFICATION.md`
- `RETRIEVAL_FOUNDATION_RF1.md`
- `RETRIEVAL_FOUNDATION_RF2.md`
- `RETRIEVAL_FOUNDATION_HANDOFF.md`
- `REAL_CORPUS_PILOT_MANIFEST.json`
- `EXECUTION_GOVERNANCE.md`
- `components/knowledge-core/README.md`

Then verify branch/HEAD and perform only the separately authorized bounded task.

## Stop boundary

**The first curated real-corpus pilot is complete. Do not begin RI-1, persistent import, broader corpus expansion, chunking, embeddings, RAG, ACL/Vera semantic expansion, Authority implementation, production deployment, or execution work without separate authorization.**
