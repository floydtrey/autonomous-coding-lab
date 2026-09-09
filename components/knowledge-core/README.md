# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Current task:** Knowledge Core Kernel Task 5 — reversible identity merge/split + replacement-not-equivalence  
**Starting Task 5 checkpoint:** `d02954fe63bd08a4eb55885d407de56d0186f05a`  
**Task 5 implementation commit:** `1a45f73ab7d3a9ab2fb5762700806e776e3cadc5`  
**Status:** Tasks 1–4 checkpointed; Task 5 implemented but Gate 12–13 runtime validation is still pending; Task 6 not started

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
- historical-belief queries;
- late correction without rewriting prior belief;
- lifecycle-aware current assertion selection;
- unresolved conflict preservation;
- deterministic rebuildable `kc_derived.current_assertion`.

### Task 3 — operation/idempotency + stale-writer protection

Implemented:

- `kc_control.operation` control ledger;
- stable operation IDs and request digests;
- idempotent settled replay;
- stale revision rejection without unintended canonical mutation;
- PostgreSQL transaction-scoped serialization for managed writes.

### Task 4 — resource/artifact ingest + exact-version provenance

Implemented:

- logical resources and exact resource versions;
- historical mutable locators;
- immutable SHA-256 content-addressed artifact storage;
- exact-version provenance;
- backward explanation and forward impact traversal;
- physical deduplication without logical-resource identity collapse.

### Task 5 — identity transitions

Implemented in code:

- canonical `kc.identity_transition` records anchored by `OCCURRENCE`;
- canonical `kc.identity_transition_member` rows with governed member roles;
- rebuildable `kc_derived.current_identity_member` projection;
- separate `identity-test` semantic profile with `person`, `device`, `identity_resolution`, and `has_name` test vocabulary;
- append-only `merge` transitions with an explicit representative;
- explicit merge reversal as a new `split` transition whose `reverses_transition_ref` points to the original merge;
- prevention of applying a second reversal to the same merge;
- deterministic current-equivalence group IDs from active merge membership;
- singleton fallback semantics when an entity has no active equivalence transition;
- transitive active-merge projection using connected components;
- `replace(old,new)` transitions recorded as succession history only;
- explicit exclusion of `replace` from the equivalence projection;
- identity history retrieval without rewriting entity or assertion foreign keys;
- deterministic destruction/rebuild behavior for the current identity projection.

Task 5 deliberately does **not** implement deletion/restriction, FastAPI routes, Authority, embeddings, Vera integration, ACL integration, or later Kernel features.

## Task 5 semantic conventions

### Merge versus stored assertions

A merge does not rewrite assertions from one entity ref onto another entity ref. Canonical assertions retain their original subjects. Current equivalence is represented only by the rebuildable identity projection.

### Reversal

Task 5 represents merge undo as an explicit canonical transition:

```text
MERGE(A, B; representative=A)
SPLIT(A, B; reverses=<merge transition>)
```

The original merge remains historical evidence. Rebuilding current identity state ignores a merge that has an explicit reversal, so A and B return to separate singleton identities unless another active equivalence transition still connects them.

Task 5 implements `split` only as the explicit reversal form needed by Gate 12; it does not introduce a general arbitrary partitioning API.

### Replacement is not equivalence

A replacement records succession:

```text
old device --replace--> new device
```

It does not place the two devices in the same resolution group and does not make historical assertions about the old device become assertions about the new device. This is the bounded Gate 13 rule.

The physical schema reserves the accepted identity transition codes `resolve_same`, `resolve_different`, `merge`, `split`, `replace`, and `reassign_identifier`, but Task 5 application methods implement only the Gate 12–13 operations: merge, merge reversal/split, and replace.

## Task 5 focused tests authored

`tests/test_task5_identity.py` contains five focused cases covering:

1. two same-name people merge into one current resolution group while both original assertions remain unchanged, then explicit reversal restores separate identities;
2. the same merge cannot be reversed twice;
3. a device replacement remains succession history and never becomes current equivalence;
4. current identity projection destruction/rebuild is deterministic;
5. invalid merge/replacement shapes are rejected.

## Task 5 validation checkpoint

Validation actually available in this session:

- remote starting HEAD verified as `d02954fe63bd08a4eb55885d407de56d0186f05a`;
- committed Task 5 diff reviewed against `PHYSICAL_SCHEMA_V1.md` and Kernel Gates 12–13;
- migration `0005_task5` and SQLAlchemy identity model were checked for field/constraint consistency;
- implementation diff is one commit ahead and zero behind the Task 4 checkpoint before this documentation commit;
- GitHub exposes no workflow run and no commit status checks for implementation commit `1a45f73`.

### Validation not completed

The focused Task 5 tests were **authored but not runtime-executed in this session**. The available GitHub connection provides repository reads/writes but no code-execution environment, and the local runtime could not reach GitHub to materialize this branch for test execution.

A live PostgreSQL service was also not available. Therefore this checkpoint does **not** claim:

- Gate 12 or Gate 13 acceptance has passed at runtime;
- `pytest` execution of `test_task5_identity.py`;
- Alembic application of migrations `0001_task1` through `0005_task5` to a running PostgreSQL database;
- live PostgreSQL identity-projection behavior.

The code review did not reveal a blocking identity-model contradiction, but the Kernel implementation plan explicitly says acceptance gates must pass before advancing.

## Known bounded limitations

- Task 5 identity mutation methods are lower-level Kernel operations and are not yet exposed through the future FastAPI/service-only boundary.
- They are not yet wrapped in dedicated Task 3 operation-ID/idempotency request methods; the later service mutation path must preserve the managed-operation requirements rather than expose unguarded writes.
- `resolve_same`, `resolve_different`, and `reassign_identifier` are schema-reserved codes only in this slice.
- The identity projection is derived and must be rebuilt after identity-transition changes; it is not canonical truth.

## Stop point

Task 5 implementation is checkpointed, but **Task 5 is not yet acceptance-validated and Task 6 has not been started.**

The next permitted action is:

> Run the focused Task 5 identity tests and migration validation for Gates 12–13. If they pass, record Task 5 as accepted before beginning Task 6.

The next separately authorized implementation slice after that validation is expected to be:

> **Knowledge Core Kernel Task 6: deletion/restriction semantic fence + erasure/anti-resurrection behavior for Gates 14–16.**

Do not begin Task 6 while Gate 12–13 validation remains unresolved.

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
