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
**Status:** **Knowledge Core Kernel V1 remains frozen and accepted; PostgreSQL Qualification, RF-1 retrieval design, and RF-2 synthetic PostgreSQL lexical retrieval are complete. Awaiting separate authorization for any real-corpus/import slice.**

This is the branch-specific controlling acceptance record for Knowledge Core. It does not replace repository-wide `docs/CURRENT_STATE.md`. The frozen Kernel boundary remains `9e904f49480055615bb0cf32360dbdc8400e117c`; post-Kernel integration/retrieval work does not reopen its 19 accepted semantic gates.

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

RF-1 established the synthetic-first PostgreSQL lexical design without changing code. Core decisions include exact `resource_version_ref` provenance, immutable artifact bytes outside PostgreSQL, PostgreSQL native full-text search, explicit lifecycle/authority metadata, deterministic ranking, derived-generation lineage, mandatory serving-fence enforcement, and a service-only API contract. RF2-G1 through RF2-G14 defined the falsifiable acceptance gates before implementation.

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

The nine PostgreSQL tests are the five previously accepted PostgreSQL qualification tests plus four RF-2 test functions covering RF2-G1 through RF2-G14. The RF-2 corpus proves unsupported-media exclusion, current-vs-superseded conflict handling, explicit historical retrieval, multi-source authority tie-breaking, deterministic total ordering, exact provenance, stale-index serving-fence defense, service-only client access, hidden storage internals, bounded blank/irrelevant behavior, explicit lifecycle classification, and current-generation-only retrieval.

The existing duplicate-operation-key log entry remains an intentional part of the same-operation-ID PostgreSQL race qualification and did not fail the workflow.

## Current retrieval boundary

RF-2 is a retrieval foundation, not a complete knowledge-import/RAG system.

Current accepted limitations:

- retrieval is PostgreSQL-only;
- only strict UTF-8 `text/plain` and `text/markdown` are indexable;
- search is whole-resource-version lexical retrieval, not chunk retrieval;
- lifecycle/currentness and source authority must be supplied by an approved classification/import process;
- lexical rank is not truth, authorization, or execution authority;
- only a synthetic corpus has been qualified;
- no real repository documentation has been imported as part of RF-2.

## Explicitly unclaimed / remaining integration debt

The accepted Kernel, PostgreSQL qualification, and RF-2 retrieval foundation do **not** claim:

- curated or bulk real-document import;
- repository-wide ACL/Vera/RiskCardOCR documentation classification;
- PDF/DOCX/HTML extraction, OCR, or arbitrary binary parsing;
- chunking;
- embeddings/vector retrieval;
- LLM summarization/RAG;
- ACL-specific semantic profiles;
- Vera-specific semantic profiles;
- production authentication, TLS, firewall/network policy, or real Authority-service implementation;
- production backup/restore orchestration or multi-service privacy reconciliation;
- physical erasure of resource artifact bytes beyond the bounded accepted erasure semantics;
- autonomous workers or action execution;
- production process-boundary deployment qualification.

## Next separately authorized retrieval/import slice

Do not start automatically.

The next sensible retrieval step is a **small curated real-corpus pilot** following the Knowledge Import Campaign shape already recorded in the retrieval handoff:

1. select one bounded repository/document area;
2. inventory and classify a small candidate set;
3. identify authoritative/current/supporting/historical/superseded/research/temporary/duplicate/excluded material;
4. record exact repository/path/commit or source-version provenance;
5. map supersession explicitly;
6. approve only a small text/Markdown ingest batch;
7. define known questions and expected sources before testing;
8. validate RF-2 retrieval against that real corpus;
9. stop before broader expansion.

A real-corpus defect should be repaired as a bounded retrieval task rather than hidden by importing more data.

## Durable restart point

For the next Knowledge Core retrieval/import chat, read:

- `CURRENT_STATE.md`
- `POSTGRES_QUALIFICATION.md`
- `RETRIEVAL_FOUNDATION_RF1.md`
- `RETRIEVAL_FOUNDATION_RF2.md`
- `RETRIEVAL_FOUNDATION_HANDOFF.md`
- `EXECUTION_GOVERNANCE.md`
- `components/knowledge-core/README.md`

Then verify branch/HEAD and perform only the separately authorized bounded task.

## Stop boundary

**RF-2 is complete. Do not begin real-corpus import, embeddings, RAG, ACL/Vera semantic expansion, Authority implementation, production deployment, or execution work without separate authorization.**
