# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Completed task:** Knowledge Core Kernel Task 4 — resource/artifact ingest + exact-version provenance  
**Starting Task 4 checkpoint:** `0ca7951ac114890b6a755e0fc2d40992829d97d9`  
**Task 4 implementation commit:** `8cfd8199e0497dca401de1515b459f68abf15976`  
**Task 4 hardening/cleanup commits:** `0ed0710a822e8f38ec8aa78acb553c0fc241c69d`, `664e287e74086472b6d278f1e2909d4615473f9d`, `d9fcd2042bb1c27ec0f57c4589541fb833992e57`, `24e0a709e678a80b0fcea5d89e83a0df69e4059c`  
**Status:** Tasks 1–4 implemented; Task 5 not started

This file is the durable implementation-progress checkpoint for the component. The architecture documents under `docs/architecture/knowledge-core/` remain the design baseline; later work must still be separately bounded by the user and `EXECUTION_GOVERNANCE.md`.

## Implemented Kernel boundary

### Task 1 — foundation + typed assertion + correction/undo

Implemented:

- component/package and database foundation;
- canonical revision and universal reference records;
- minimal semantic profile/kind/predicate foundations;
- entities and typed scalar/reference assertions;
- append-only assertion correction;
- explicit correction reversal/undo.

### Task 2 — bitemporal history + current projection

Implemented:

- independent world-valid and knowledge-record time;
- timezone-aware half-open world intervals `[valid_from, valid_to)`;
- historical-belief queries using both world time and knowledge cutoff;
- late correction without rewriting earlier recorded belief;
- lifecycle-aware current selection across correction and reversal transitions;
- conflict preservation when multiple assertions remain simultaneously current;
- deterministic conflict-group identity;
- disposable/rebuildable `kc_derived.current_assertion` projection.

### Task 3 — operation/idempotency + stale-writer protection

Implemented:

- `kc_control.operation` control ledger;
- stable UUID operation identities and deterministic request digests;
- canonical revision binding through `kc.revision.operation_id`;
- settled replay for identical operation retries;
- rejection of materially different operation-ID reuse;
- optimistic revision preconditions for state-dependent correction;
- durable stale-write conflict state without unintended canonical mutation;
- one PostgreSQL transaction-scoped advisory lock across Task 3 managed canonical writes.

### Task 4 — resource/artifact ingest + exact-version provenance

Implemented:

- canonical `kc.resource`, `kc.resource_version`, `kc.resource_locator`, and `kc.provenance_link` records;
- universal `resource` and `resource_version` reference kinds;
- a separate minimal `resource-test` semantic profile so Task 4 does not silently mutate the earlier `core-test` profile revision;
- local immutable SHA-256 content-addressed artifact storage outside PostgreSQL;
- digest/size/backend/key metadata in PostgreSQL while exact artifact bytes remain in the artifact backend;
- resource-version uniqueness scoped to `(logical resource, digest algorithm, digest)` rather than global semantic merging;
- physical artifact deduplication without merging distinct logical resource identities;
- ingestion occurrences and historical locator observations pinned to exact resource versions;
- stable re-ingest of an already-known exact version without inventing a second version;
- recording of a newly observed locator for an existing exact version without inventing a new version;
- typed provenance links using the governed `supports_claim` relation revision;
- assertion evidence links that target an exact `RESOURCE VERSION`, never a mutable path/URL locator;
- backward assertion explanation to the exact consumed evidence version;
- forward impact traversal from an exact resource version to dependent assertion refs;
- rejection of an ordinary domain reference predicate attempting to masquerade as provenance.

Task 4 deliberately does **not** implement identity transitions, deletion/restriction, FastAPI routes, Authority, embeddings, Vera integration, ACL integration, or later Kernel features.

## Task 4 semantic conventions

For the bounded Gate 7/8 slice, provenance uses this direction:

```text
dependent assertion --supports_claim--> exact resource version
```

The mutable locator is historical observation metadata on the logical resource/version. It is never substituted for the exact version in provenance. This lets the same indexed provenance links support both:

- backward explanation: assertion -> exact evidence version;
- forward impact: exact evidence version -> dependent assertion(s).

Identical bytes may share one physical SHA-256 artifact key across logical resources, but each logical resource retains its own semantic `resource_version` ref. Physical deduplication therefore does not collapse provenance, ownership, or resource identity.

## Task 4 validation checkpoint

Validation performed before this durable checkpoint:

- Task 4 Python source syntax pre-check: passed;
- local SHA-256 artifact-store commit/read/verify harness: passed;
- Task 4 SQLAlchemy resource/provenance models created successfully under isolated SQLite schema translation;
- the same Task 4 SQLAlchemy tables/indexes compiled successfully to PostgreSQL DDL;
- isolated SQLite Task 4 semantic harness: passed for distinct mutable-path versions, exact-byte retrieval, backward explanation, forward impact, and locator history;
- isolated negative/re-ingest harness: passed for stable exact re-ingest and rejection of a non-provenance domain relation;
- committed focused Task 4 tests contain six cases covering the Gate 7/8 behaviors and the two review edge cases;
- GitHub Actions for the final Task 4 implementation head before checkpoint: no workflow run existed.

The bounded validation proves the intended Task 4 semantics, but it is not a claim of a complete repository-side CI run.

### Validation and implementation limitations

The execution environment still did not provide a live PostgreSQL service, so this checkpoint does **not** claim that migrations `0001_task1` through `0004_task4` were applied to a running PostgreSQL database. It also does not claim a live artifact-filesystem/PostgreSQL crash-recovery test.

Artifact bytes are committed to the immutable content-addressed backend before the corresponding canonical database mutation settles. If a database transaction fails after the artifact commit, an unreachable immutable artifact blob can remain. That cannot make canonical provenance point to incorrect bytes, but explicit orphan/reconciliation tooling is not implemented in Task 4 and must not be assumed to exist.

A live PostgreSQL migration/integration gate remains required before relying on PostgreSQL-specific runtime behavior in later deployment work.

## Stop point

Task 4 is complete at this checkpoint. **Task 5 has not been started.**

The next separately authorized task from the Kernel build order is:

> **Knowledge Core Kernel Task 5: identity transitions — reversible identity merge/split semantics + replacement-not-equivalence.**

That task should cover only the identity boundary needed for Kernel Gates 12 and 13. Do not begin deletion/restriction, FastAPI service routes, Authority, embeddings, Vera, ACL integration, or later Kernel areas implicitly.

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

Set `KNOWLEDGE_CORE_DATABASE_URL` to the PostgreSQL connection URL before applying migrations. Clients are not intended to receive this credential; service/API isolation is implemented in a later bounded task.
