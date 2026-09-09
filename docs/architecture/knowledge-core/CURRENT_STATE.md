# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Kernel V1 starting architecture checkpoint:** `dfdaaa45887cb882a05c929a3166981cc0528595`  
**Task 10 checkpoint:** `ea8ff441133329dfc19b631ed0172cdf12561704`  
**Gate 19 validated implementation head:** `2bdbc2a161bd2756fa7139ecefd4ca8b160f148e`  
**Frozen Kernel V1 checkpoint:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**Exact freeze validation:** GitHub Actions run `34350709966` — **47 passed, 2 upstream deprecation warnings**  
**PostgreSQL qualification implementation checkpoint:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**PostgreSQL qualification validation:** GitHub Actions run `34364589918` — **47 fast semantic tests passed + 5 PostgreSQL qualification tests passed**  
**Retrieval Foundation RF-1 design:** `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`  
**Status:** **Knowledge Core Kernel V1 remains frozen and accepted; Post-Kernel Slice 1 — PostgreSQL Qualification is complete; Retrieval Foundation RF-1 design/acceptance is complete. Awaiting separate authorization for RF-2 implementation.**

This file is the branch-specific controlling acceptance record for Knowledge Core. It does not replace the repository-wide `docs/CURRENT_STATE.md`, which records the accepted state of `main` and other ACL work. The frozen Kernel implementation boundary remains `9e904f49480055615bb0cf32360dbdc8400e117c`; post-Kernel test/CI/documentation work does not reopen or alter its 19-gate semantic acceptance.

## Accepted Kernel boundary

The V1 Kernel includes:

- canonical revisions and universal knowledge refs;
- immutable/versioned semantic profiles, kinds, and predicates;
- atomic typed assertions and reference-valued relationships;
- append-only correction/reversal history;
- independent world-valid and knowledge-record time;
- rebuildable current assertion projection with conflict preservation;
- operation IDs, deterministic request digests, idempotent replay, stale-writer protection, and serialized PostgreSQL managed writes;
- exact logical-resource/resource-version identity, immutable SHA-256 artifact storage, locator history, and traversable provenance;
- reversible identity merge/split semantics and replacement-not-equivalence;
- deletion/restriction serving fences, bounded assertion tombstoning, and anti-resurrection reconciliation;
- append-only semantic-profile activation and exact assertion semantic pinning;
- derived-generation lineage plus monotonic out-of-order settlement fencing;
- FastAPI/Pydantic semantic service routes for normal client operations;
- managed exact-resource ingest including explicit successful no-canonical-mutation replay;
- a serving-safe current-identity query required for client-side identity semantics;
- a service-only Gate 19 simulated Vera/ACL client with no database or artifact-store credentials.

## Gate 19 acceptance

Gate 19 uses `tests/test_task11_gate19_service_only.py` and the existing Task 1–10 suites.

The simulated client has only:

- an HTTP/TestClient transport;
- `X-Knowledge-Caller` identification context.

It does not possess or import:

- SQLAlchemy sessions;
- PostgreSQL/database URLs;
- `KNOWLEDGE_CORE_DATABASE_URL`;
- artifact-store objects or artifact paths;
- direct SQL/storage repositories.

The normal client HTTP replay covers the externally observable portions of typed assertions, relationships, correction/reversal, bitemporal reads, conflict preservation, stale writes, idempotent retries, exact resource provenance, identity merge/split/replacement, privacy serving fences, and semantic-profile pinning. Privileged privacy reconciliation, profile administration, and generation settlement remain server/control-plane concerns and are deliberately absent from the Vera/ACL client API.

## Exact Kernel validation

A branch-local GitHub Actions workflow installs the exact checked-in component on a clean Ubuntu runner using Python 3.12.

Workflow run `34350296337` validated the Gate 19 implementation head `2bdbc2a161bd2756fa7139ecefd4ca8b160f148e`. After the freeze documentation was committed, workflow run `34350709966` validated the exact frozen Kernel checkpoint `9e904f49480055615bb0cf32360dbdc8400e117c`:

```text
47 passed, 2 warnings
```

The two warnings are upstream TestClient/Starlette deprecation warnings and are not semantic failures.

## Gate disposition

- Gates 1–11: covered by the original foundation/temporal/operation/resource acceptance suites and included in the final exact 47-test replay.
- Gates 12–16: accepted and replayed through final checked-in component tests; service-observable identity/privacy behavior is also exercised by Gate 19.
- Gate 17: semantic profile immutability accepted and included in the final suite; Gate 19 verifies old/new assertion revision pinning through the HTTP client while profile activation remains server-side administration.
- Gate 18: derived generation fencing accepted and included in the final suite; Gate 19 verifies that generation administration remains absent from the normal client surface while the server-side fence still rejects an obsolete late finisher.
- Gate 19: **accepted** through FastAPI/TestClient service-only replay and exact repository CI.

## Post-Kernel Slice 1 — PostgreSQL Qualification

This slice is recorded in `docs/architecture/knowledge-core/POSTGRES_QUALIFICATION.md`.

Local laptop validation used Windows Python 3.12.10 with PostgreSQL 18.6 running under Ubuntu/WSL2. A fresh dedicated database accepted the complete Alembic chain from no revision through `0008_task9 (head)`, and an application-layer smoke operation succeeded through `engine_from_environment()`.

The checked-in qualification suite `tests/test_postgres_qualification.py` then exercised a real PostgreSQL 18 service in GitHub Actions using separate database sessions/connections. It proves:

- one-winner/one-stale behavior for competing writers sharing one expected revision;
- same-operation-ID primary-key contention with replay of one canonical result;
- observed blocking on the canonical PostgreSQL advisory transaction lock;
- newer-generation settlement fencing an older independent-session late finisher;
- complete transaction rollback after partially flushed canonical work is forced to fail.

Exact CI evidence at `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`, workflow run `34364589918`:

```text
Alembic 0001_task1 -> 0008_task9: passed
Fast semantic suite: 47 passed, 5 deselected, 2 upstream warnings
PostgreSQL qualification suite: 5 passed, 47 deselected, 2 upstream warnings
Workflow conclusion: success
```

The workflow now provisions ephemeral PostgreSQL 18, applies the real migration chain, runs the fast SQLite-backed semantic suite separately, and then runs the PostgreSQL-only qualification suite.

## Post-Kernel Slice 2 — Retrieval Foundation

RF-1 — **Retrieval design and falsifiable acceptance plan** — is complete as documentation only.

The durable design is:

`docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`

RF-1 inspected the existing exact resource/version/provenance model, artifact-store boundary, deletion serving fences, derived-generation lifecycle, application service layer, and HTTP resource API. The accepted direction is a synthetic-first PostgreSQL native lexical/full-text projection keyed to exact `resource_version_ref` values and backed by existing derived-generation lineage.

Key RF-1 decisions:

- retrieval indexes exact supported text resource versions, not mutable paths or logical-resource identity alone;
- raw artifact bytes remain outside PostgreSQL;
- PostgreSQL `tsvector`/GIN plus native full-text query/ranking is the intended lexical mechanism;
- the derived retrieval projection reuses `kc_derived.generation` / `generation_source` and remains rebuildable rather than canonical truth;
- current/superseded lifecycle and source-authority ranking metadata are explicit; retrieval must not infer them from recency or keyword score;
- default retrieval excludes superseded material while preserving explicit historical access;
- every result retains exact logical-resource/version/digest/generation provenance;
- existing resource-version serving eligibility remains mandatory so stale search rows cannot bypass restriction/deletion fences;
- normal clients query through a service-only HTTP contract with no database or artifact-store credentials;
- the synthetic acceptance corpus and RF2-G1 through RF2-G14 define falsifiable expected behavior before any real repository import.

RF-1 changed no retrieval code, migrations, component tests, canonical schema, or real knowledge data.

### Next separately authorized task

**RF-2 — Implement the synthetic-first PostgreSQL lexical retrieval foundation exactly against `RETRIEVAL_FOUNDATION_RF1.md`.**

RF-2 should be separately authorized. It must remain bounded to the derived lexical table/index, generation builder/query, service contract, deletion-fence integration, and synthetic PostgreSQL acceptance gates. It must stop before curated real-corpus ingestion, bulk documentation import, embeddings, RAG/summarization, ACL/Vera semantic expansion, or production deployment work.

## Explicitly unclaimed / remaining integration debt

Kernel acceptance, PostgreSQL qualification, and RF-1 design do **not** claim:

- an implemented retrieval endpoint/index/migration;
- production authentication, TLS, firewall/network policy, or the real Authority service;
- production backup/restore orchestration or multi-service privacy reconciliation;
- physical erasure of resource artifact bytes beyond the bounded assertion-erasure behavior;
- generation IDs attached to every historical derived-family row;
- separate-OS-process deployment orchestration (the PostgreSQL concurrency qualification uses independent sessions/connections inside one pytest process);
- curated or bulk real-document import;
- Vera domain features, ACL domain profiles, embeddings/vector search, autonomous workers, or action execution.

The former gaps around live PostgreSQL migration application, advisory-lock behavior, independent-session stale-write races, operation-ID contention/replay, generation late-finisher fencing, and transactional rollback are closed at the database-integration level. Retrieval remains design-only until RF-2 is separately authorized and implemented.

## Recommended next bounded slices

Do not combine these into one task. Select one separately:

1. **RF-2 synthetic lexical retrieval implementation** — implement and validate the accepted RF-1 PostgreSQL retrieval design without real repository import.
2. **First real ACL semantic profile** — only after the retrieval/storage boundary is satisfactory, define a small versioned ACL vocabulary for projects, tasks, evidence, decisions, dependencies, and outcomes. Do not import Worker Lab execution authority into Knowledge Core.
3. **Authority-service boundary** — implement/validate the external Authority service contract separately if authorization becomes the higher priority. Knowledge Core should consume decisions, not become Authority.
4. **Production deployment qualification** — only when deployment becomes relevant, add process-boundary orchestration, authentication/TLS/network policy, backup/restore, and operational recovery validation.
5. **Later Vera profile/integration** — defer until the generic infrastructure and ACL path have proven the Kernel under real use.

## Stop boundary

**Stop after RF-1 documentation/acceptance design. Do not begin RF-2 implementation, real-document ingestion, embeddings, ACL/Vera semantic expansion, Authority implementation, or production deployment work without separate authorization.**
