# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Completed task:** Knowledge Core Kernel Task 2 — bitemporal history + current projection  
**Starting Task 2 checkpoint:** `3d8e5e91d3f427a4ad841f58b4d3e597907dd949`  
**Task 2 implementation commit:** `2f163f08190ab3b3b90681e5b99110202203959c`  
**Status:** Tasks 1 and 2 implemented; Task 3 not started

This file is the durable implementation-progress checkpoint for the component. The
architecture documents under `docs/architecture/knowledge-core/` remain the design
baseline; later work must still be separately bounded by the user and
`EXECUTION_GOVERNANCE.md`.

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
- late correction that changes reconstructed world history without rewriting the
  earlier recorded belief;
- lifecycle-aware current selection across correction and reversal transitions;
- conflict preservation when multiple assertions remain simultaneously current;
- deterministic conflict-group identity for unresolved current conflicts;
- `kc_derived.current_assertion` as a disposable projection;
- destruction and deterministic rebuild of that projection from canonical records.

Task 2 does **not** implement operation/idempotency records, stale-writer protection,
resources/provenance, identity resolution, deletion/restriction, FastAPI routes,
Authority, embeddings, Vera, or ACL integration.

## Task 2 physical-schema note

`PHYSICAL_SCHEMA_V1.md` described world validity using candidate `valid_during
TSTZRANGE` storage and explicitly allowed first-DDL column splits. Task 2 implements
the same semantic interval as typed `valid_from` / `valid_to` `TIMESTAMPTZ` columns
plus `world_time_precision`.

The interval is half-open: the lower bound is inclusive and the upper bound is
exclusive. This is a physical representation choice inside the already accepted
KC-D023 flexibility; it does not change the architecture rule that world time and
knowledge-record time are independent.

## Task 2 validation checkpoint

Validation performed before this durable checkpoint:

- isolated Task 2 semantic cases: **5 passed**;
- Task 1 + Task 2 compatibility harness: **9 passed**;
- new Python module/migration syntax checks: passed;
- Alembic `0002_task2` PostgreSQL offline DDL render: passed;
- GitHub Actions for implementation commit `2f163f0`: no workflow run existed.

The five Task 2 cases prove:

1. a late correction can establish an earlier world-valid fact while a
   historical-belief query before the correction still reconstructs the old belief;
2. two unresolved assertions can both remain current and receive one deterministic
   conflict group instead of manufacturing a single truth;
3. correction changes the current projection without overwriting the original
   assertion, and reversal returns the projection to the original assertion;
4. deleting the complete current projection and rebuilding it produces identical
   semantic rows and conflict identities;
5. naive or inverted world-valid intervals are rejected.

### Validation limitation

The execution environment still did not provide a live PostgreSQL server. Therefore
this checkpoint does **not** claim that migrations `0001_task1` + `0002_task2` were
applied against a running PostgreSQL instance, and it does not claim a repository-side
CI run. The offline PostgreSQL migration render succeeded and the bounded semantic
compatibility harness succeeded.

A live PostgreSQL migration/integration gate should be performed before later work
relies on PostgreSQL-specific runtime behavior.

## Stop point

Task 2 is complete at this checkpoint. **Task 3 has not been started.**

The next separately authorized task is:

> **Knowledge Core Kernel Task 3: operation/idempotency + stale-writer protection.**

That task should implement only the next concurrency/retry boundary needed for Kernel
gates 10 and 11. Do not begin resources/provenance or later Kernel areas implicitly.

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

Set `KNOWLEDGE_CORE_DATABASE_URL` to the PostgreSQL connection URL before applying
migrations. Clients are not intended to receive this credential; service/API
isolation is implemented in a later bounded task.
