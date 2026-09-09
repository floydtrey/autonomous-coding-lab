# Knowledge Core

This component contains the bounded Knowledge Core Kernel plus accepted post-Kernel PostgreSQL/retrieval validation slices.

## Current state

**Branch:** `architecture/knowledge-core`  
**Task 10 checkpoint:** `ea8ff441133329dfc19b631ed0172cdf12561704`  
**Gate 19 validated implementation head:** `2bdbc2a161bd2756fa7139ecefd4ca8b160f148e`  
**Final frozen Kernel V1 checkpoint:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**Final Kernel CI:** GitHub Actions run `34350709966` — **47 passed, 2 upstream deprecation warnings**  
**PostgreSQL qualification checkpoint:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-2 validated implementation checkpoint:** `479a918762e919851e19fee3b36cc1d95e78f3e8`  
**First curated real-corpus pilot checkpoint:** `40849bd4de261089a030e09677568c3b4cf1a862`  
**Latest pilot CI:** GitHub Actions run `34373589343` — **48 fast tests + 11 PostgreSQL tests passed**  
**Status:** **Kernel V1 remains frozen and accepted. Real PostgreSQL qualification, synthetic lexical RF-2, and the first ten-document curated real-corpus retrieval pilot are complete. No persistent production corpus is imported.**

The controlling acceptance record is `docs/architecture/knowledge-core/CURRENT_STATE.md`. The retrieval/import restart point is `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`. The first real-corpus classification is pinned in `docs/architecture/knowledge-core/REAL_CORPUS_PILOT_MANIFEST.json`.

## Accepted Kernel capabilities

The bounded V1 Kernel includes:

- canonical revisions and universal knowledge refs;
- immutable/versioned semantic profiles, kinds, and predicates;
- typed scalar/reference assertions;
- append-only correction and explicit reversal;
- independent world-valid and knowledge-record time;
- conflict-preserving historical/current retrieval;
- rebuildable current projections;
- operation IDs, deterministic request digests, idempotent replay, stale-write protection, and serialized PostgreSQL managed writes;
- exact resource versions, immutable SHA-256 artifact storage, mutable locator history, and traversable provenance;
- reversible identity merge/split plus replacement-not-equivalence;
- deletion/restriction serving fences, bounded assertion erasure, and anti-resurrection reconciliation;
- append-only semantic-profile activation with assertions pinned to exact semantic revisions;
- derived-generation lineage and monotonic out-of-order settlement fencing;
- a FastAPI/Pydantic semantic service boundary;
- managed resource/provenance HTTP operations, including explicit successful no-canonical-mutation exact re-ingest;
- a serving-safe current-identity read for normal service clients.

## Gate 19 — service-only client acceptance

`tests/test_task11_gate19_service_only.py` defines a simulated Vera/ACL client whose entire capability is:

```text
HTTP/TestClient transport
X-Knowledge-Caller identification context
```

The client possesses no SQLAlchemy session, database URL, PostgreSQL connection string, `KNOWLEDGE_CORE_DATABASE_URL`, artifact-store object, artifact path, or direct storage repository.

Normal client semantics are exercised through FastAPI/TestClient for typed assertions, reference relationships, correction/reversal, bitemporal belief, conflict preservation, stale writes, idempotent retries, exact resource provenance, identity merge/split/replacement, privacy-serving behavior, and semantic-profile pinning.

Privileged privacy reconciliation, profile administration, and derived-generation settlement remain server/control-plane concerns.

## Post-Kernel PostgreSQL qualification

A dedicated PostgreSQL 18 workflow now applies the real Alembic chain and exercises transaction/concurrency behavior that SQLite cannot establish.

Checkpoint `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`, run `34364589918`, proved:

- migrations through `0008_task9` on PostgreSQL;
- competing stale-writer serialization;
- same-operation-ID contention/replay;
- PostgreSQL advisory-lock blocking;
- generation late-finisher fencing;
- transactional rollback after partially flushed canonical work.

That PostgreSQL qualification remains accepted and is replayed in later component CI.

## RF-2 lexical retrieval

RF-2 adds PostgreSQL-native whole-resource-version lexical retrieval without changing canonical resource/provenance meaning.

Accepted behavior includes:

- `kc_derived.resource_text_search` via migration `0009_rf2`;
- `TSVECTOR` + GIN;
- fixed English `websearch_to_tsquery`, `@@`, and `ts_rank_cd`;
- exact strict UTF-8 `text/plain` / `text/markdown` artifact indexing;
- explicit current/unknown/superseded lifecycle and authority metadata;
- deterministic ranking and current-generation-only serving;
- service-time deletion/restriction eligibility;
- `POST /v1/retrieval/search` behind `X-Knowledge-Caller`;
- exact logical-resource/version/digest/source/generation provenance in results;
- no database or artifact-store internals in the normal client contract.

RF-2 exact validation at `479a918762e919851e19fee3b36cc1d95e78f3e8`, run `34371352821`:

```text
47 fast semantic tests passed
9 PostgreSQL tests passed
```

## First curated real-corpus pilot

The first real-document validation uses the exact ten Markdown files under `docs/architecture/knowledge-core/` at source checkpoint `adb2a48a1e248f24e43550d897eed1b5e300cc26`.

`REAL_CORPUS_PILOT_MANIFEST.json` pins every file to an exact Git blob and explicitly classifies four documents as current and six as superseded/historical before ingest. The pilot ingests only those approved paths into ephemeral PostgreSQL/artifact storage, builds one RF-2 text generation, and runs predeclared known queries.

Exact validation at `40849bd4de261089a030e09677568c3b4cf1a862`, run `34373589343`:

```text
48 fast tests passed
11 PostgreSQL tests passed
```

The pilot required no RF-2 production-code repair.

A material limitation was exposed: whole-document classification cannot preserve current sections inside a document that also contains stale operational sections. The pilot safely marks mixed files such as `ARCHITECTURE_V1.md` and `DECISIONS.md` historical rather than allowing stale instructions into default retrieval. Chunking/section-level classification is not yet authorized or implemented.

## Explicit limitations / integration debt

Current acceptance does **not** claim:

- a persistent deployed repository/document corpus;
- a general repository-import/update command or stable import identity contract;
- repository-wide ACL/Vera/RiskCardOCR classification;
- path rename/move handling across import revisions;
- PDF/DOCX/HTML extraction or OCR;
- chunking/section-level retrieval;
- embeddings/vector search;
- LLM RAG/summarization;
- production authentication, TLS, firewall policy, or real Authority-service implementation;
- production backup/restore orchestration or multi-service privacy reconciliation;
- autonomous workers or action execution.

The next separately authorized retrieval/import task is RI-1: design a falsifiable safe repository-import/update contract before implementing persistent import. See the controlling handoff for scope.

## Development

Python 3.12+ is required.

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

Alembic configuration is rooted in this component:

```powershell
alembic upgrade head
```

Set `KNOWLEDGE_CORE_DATABASE_URL` before applying PostgreSQL migrations. Client applications must never receive that credential.

## Stop boundary

Do not begin RI-1, persistent/broad corpus import, chunking, embeddings/RAG, Authority implementation, Vera/ACL semantic expansion, or production deployment without separate authorization.
