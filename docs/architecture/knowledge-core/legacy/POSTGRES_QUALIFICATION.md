# Knowledge Core PostgreSQL Qualification

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Validated implementation checkpoint:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**GitHub Actions evidence:** run `34364589918` — **success**  
**Status:** **Post-Kernel Slice 1 — PostgreSQL Qualification complete.**

This is a post-Kernel integration qualification. It does not reopen or alter the frozen Kernel V1 semantic acceptance checkpoint `9e904f49480055615bb0cf32360dbdc8400e117c`.

## Purpose

Kernel V1 was accepted primarily through deterministic SQLite-backed semantic tests plus service-boundary acceptance. The intended canonical datastore is PostgreSQL, so this slice validates the behavior that SQLite cannot establish: real migrations, PostgreSQL transaction/advisory locking, independent-session races, uniqueness contention, and rollback behavior.

## Local laptop qualification

A real PostgreSQL 18.6 server was installed under Ubuntu/WSL2 and reached from Windows Python 3.12.10 through `127.0.0.1:5432`.

The following were proven against a fresh dedicated `knowledge_core_test` database:

1. Psycopg authenticated from the Knowledge Core Windows virtual environment.
2. Alembic reported repository head `0008_task9`.
3. The empty database had no current Alembic revision before upgrade.
4. `alembic upgrade head` applied the complete chain:
   - `0001_task1`
   - `0002_task2`
   - `0003_task3`
   - `0004_task4`
   - `0005_task5`
   - `0006_task6`
   - `0007_task8`
   - `0008_task9`
5. `alembic current` then reported `0008_task9 (head)`.
6. A real application-layer smoke run through `engine_from_environment()` bootstrapped the core semantic profile, created an entity, and committed a managed assertion operation successfully on PostgreSQL.

No database credential is recorded in the repository.

## Dedicated PostgreSQL qualification suite

`components/knowledge-core/tests/test_postgres_qualification.py` contains five PostgreSQL-only tests. They use separate SQLAlchemy sessions/connections and a migrated real PostgreSQL database.

The suite proves:

1. **Competing stale writers:** two writers begin from the same canonical revision; exactly one commits and the other settles as deterministic `STALE_REVISION`, with one correction transition.
2. **Same operation-ID race:** two independent sessions submit the same operation ID and payload concurrently; PostgreSQL's primary-key constraint admits one operation row and the loser replays the committed canonical result, leaving one operation, one operation-linked revision, and one assertion.
3. **Canonical advisory-lock serialization:** a managed write is observed in `pg_locks` waiting on the PostgreSQL transaction-scoped canonical advisory lock before it is allowed to proceed.
4. **Generation late-finisher fencing:** a newer generation holds/settles through the real PostgreSQL generation lock while an older independent-session finisher waits; the newer generation becomes the sole current generation and the older finisher is fenced/staled.
5. **Transactional rollback:** a forced failure after canonical rows have been flushed rolls the transaction back completely; revision/assertion/operation counts remain unchanged and no partial operation row survives.

The PostgreSQL test fixture truncates only Knowledge Core application schemas (`kc`, `kc_control`, `kc_derived`) between cases and leaves the Alembic migration state intact.

## CI wiring

`.github/workflows/knowledge-core.yml` now provisions an ephemeral `postgres:18` service, applies the actual Alembic migration chain, and runs the fast semantic and PostgreSQL qualification suites separately.

Exact CI at `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`, run `34364589918`:

```text
Alembic migrations: 0001_task1 -> 0008_task9 succeeded
Fast semantic suite: 47 passed, 5 deselected, 2 upstream warnings
PostgreSQL qualification suite: 5 passed, 47 deselected, 2 upstream warnings
Workflow conclusion: success
```

The PostgreSQL server log contains the expected duplicate-key error from the intentional same-operation-ID race. That error is part of the test: the application handles the losing insert by rolling back that attempt and replaying the single committed result.

## What this slice closes

The following earlier integration gaps are now materially qualified:

- application of migrations `0001_task1` through `0008_task9` to real PostgreSQL;
- PostgreSQL-specific canonical advisory-lock behavior;
- independent-session stale-writer serialization;
- independent-session operation-ID uniqueness contention/replay;
- independent-session generation late-finisher fencing;
- PostgreSQL transactional rollback of partially flushed canonical work.

## Still unclaimed

This qualification does **not** claim:

- production authentication, TLS, firewall/network policy, or Authority-service implementation;
- production backup/restore orchestration or multi-service privacy reconciliation;
- physical erasure of resource artifact bytes beyond the already bounded assertion-erasure behavior;
- generation IDs attached to every historical derived-family row;
- separate-OS-process deployment orchestration (the concurrency qualification uses separate PostgreSQL sessions/connections inside one test process);
- Vera domain features, ACL domain profiles, embeddings/vector search, autonomous workers, or action execution.

The independent-session tests validate the database transaction/locking semantics that protect concurrent clients. A future deployment test may add separate OS processes if process-boundary orchestration itself becomes material.

## Stop boundary

**Stop after PostgreSQL qualification.** Do not begin retrieval, ACL semantic-profile work, Authority implementation, embeddings, or Vera integration as part of this slice.

The next post-Kernel slice must be separately authorized.
