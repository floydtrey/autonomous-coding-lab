# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Completed task:** Knowledge Core Kernel Task 3 — operation/idempotency + stale-writer protection  
**Starting Task 3 checkpoint:** `d37589c344272240b83e608f7abe2aef40eab358`  
**Task 3 implementation commits:** `992078ed592a3029708a3cc1e664fd961643c641`, `b0b0158758afb0d1824ebc6cc23fa40aa1f9e0e7`  
**Status:** Tasks 1–3 implemented; Task 4 not started

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
- settled replay for an identical operation ID/request without a second canonical mutation;
- rejection when an operation ID is reused for a materially different request or caller;
- optimistic `expected_revision` preconditions for state-dependent correction;
- durable `conflict` control state for stale writes without appending a canonical revision or transition;
- repeatable stale-conflict response on retry;
- one PostgreSQL transaction-scoped advisory lock for every Task 3 managed canonical write, so a global revision precondition cannot be invalidated by another managed write between check and commit;
- focused managed write paths for assertion append and assertion correction.

Task 3 does **not** implement resources/artifacts/provenance, identity resolution, deletion/restriction, FastAPI routes, Authority, embeddings, Vera, ACL integration, or later Kernel features.

The pre-existing lower-level Task 1/2 mutation methods remain available as internal kernel/test infrastructure. Task 3 proves the managed operation boundary for the Gate 10/11 assertion cases; the later service/API task must route external semantic mutation requests through the managed operation path rather than exposing unguarded database writes.

## Task 3 validation checkpoint

Validation performed before this durable checkpoint:

- isolated Task 3 operation-control semantic harness: **4/4 passed**;
- PostgreSQL `kc_control.operation` DDL compilation: passed;
- committed focused Task 3 tests cover stale-writer rejection, identical append retry, operation-ID payload mismatch, and idempotent correction replay;
- GitHub Actions for commit `b0b0158`: no workflow run existed.

The four isolated Task 3 cases prove:

1. an identical operation retry returns the original settled result and does not append another canonical revision;
2. reusing an operation ID with a different payload is rejected without changing canonical state;
3. a stale expected revision settles only a `kc_control.operation` conflict record and appends no canonical revision;
4. retrying that identical stale operation reproduces the same settled conflict instead of attempting a mutation again.

### Concurrency review correction

The first Task 3 implementation serialized only writes that carried an explicit stale precondition. Review identified that this was insufficient for a global revision precondition because another managed write could advance the revision between check and commit. Commit `b0b0158` corrected the design: **all managed Task 3 canonical writes acquire the same PostgreSQL transaction advisory lock**, and state-dependent writes compare `expected_revision` while holding that lock.

### Validation limitation

The execution environment still did not provide a live PostgreSQL server or a repository-side CI run. Therefore this checkpoint does **not** claim that migrations `0001_task1` through `0003_task3` were applied against a running PostgreSQL instance, and it does not claim live multi-session PostgreSQL concurrency proof.

A live PostgreSQL migration/integration/concurrency gate should be performed before later work relies on PostgreSQL-specific runtime locking behavior.

## Stop point

Task 3 is complete at this checkpoint. **Task 4 has not been started.**

The next separately authorized task from the Kernel build order is:

> **Knowledge Core Kernel Task 4: resource/artifact ingest + exact-version provenance.**

That task should cover only the resource/artifact/provenance boundary needed for Kernel gates 7 and 8. Do not begin identity transitions, deletion/restriction, FastAPI service routes, Authority, embeddings, Vera, ACL integration, or later Kernel areas implicitly.

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
