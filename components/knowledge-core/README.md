# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Current task:** Knowledge Core Kernel Task 6 — deletion/restriction fence + erasure/anti-resurrection  
**Starting Task 6 checkpoint:** `0811be71bf5fc7abc0deba53e45937fcabcd8ad0`  
**Task 6 implementation commit:** `be41c089a7e3174dd6b026217037336a2aef48ac`  
**Status:** Tasks 1–4 checkpointed; Task 5 and Task 6 implemented but their focused runtime acceptance gates remain unresolved; no later task started

This file is the durable implementation-progress checkpoint for the component. The
architecture documents under `docs/architecture/knowledge-core/` remain the design
baseline. Later work must remain bounded by the user and
`EXECUTION_GOVERNANCE.md`.

## Execution-sequence note

The prior Task 5 checkpoint explicitly stopped before Task 6 because Gates 12–13
had not been runtime-executed. The user's next current instruction explicitly said
to start Task 6. Under the repository authority order, that current instruction
authorized this bounded Task 6 implementation.

That authorization **does not retroactively mark Task 5 accepted**. Gates 12–13
remain validation debt and must be run before any final Kernel acceptance claim.

## Implemented Kernel boundary

### Task 1 — foundation + typed assertion + correction/undo

Implemented:

- component/database foundation;
- canonical revision and universal reference records;
- minimal immutable semantic profile/kind/predicate foundations;
- entities and typed scalar/reference assertions;
- append-only assertion correction and explicit reversal.

### Task 2 — bitemporal history + current projection

Implemented:

- independent world-valid and knowledge-record time;
- historical-belief reconstruction;
- late correction without rewriting prior belief;
- lifecycle-aware current assertion selection;
- unresolved conflict preservation;
- rebuildable `kc_derived.current_assertion`.

### Task 3 — operation/idempotency + stale-writer protection

Implemented:

- `kc_control.operation`;
- stable operation IDs/request digests;
- idempotent settled replay;
- stale revision rejection without unintended canonical mutation;
- PostgreSQL transaction-scoped serialization for managed writes.

### Task 4 — resource/artifact ingest + exact-version provenance

Implemented:

- logical resources and exact resource versions;
- historical mutable locators;
- immutable SHA-256 content-addressed artifacts;
- exact-version provenance;
- backward explanation/forward impact;
- physical deduplication without logical identity collapse.

### Task 5 — identity transitions

Implemented in code:

- canonical identity transitions and members;
- append-only merge;
- explicit merge reversal as split;
- rebuildable current identity projection;
- replacement as succession, never equivalence;
- deterministic projection rebuild.

Task 5 focused tests exist but have not been runtime-executed in the available
environment.

### Task 6 — deletion/restriction fence + erasure/anti-resurrection

Implemented in code:

- `kc_control.deletion_case`;
- `kc_control.deletion_target`;
- action types `restrict`, `erase`, and schema-reserved
  `retention_exception`;
- controlled case states and per-target reconciliation state;
- idempotent initial fence creation through the Task 3 managed-operation boundary;
- immediate serving fence before physical payload cleanup;
- `knowledge_ref.payload_state` use of architecture-defined `restricted` and
  `erased_tombstone`;
- purge of affected current-assertion and current-identity derived rows;
- serving-eligibility checks that consult both durable deletion control and
  canonical payload state;
- serving-safe assertion reads;
- serving-safe exact resource-version reads, including fencing through a
  restricted logical resource parent;
- serving-safe current assertion projection and historical-belief retrieval;
- projection rebuild that cannot resurrect fenced assertions;
- minimal physical assertion erasure that removes the specialized
  `kc.assertion`/`kc.assertion_value` payload while retaining the opaque
  `kc.knowledge_ref` tombstone and deletion-control record;
- fail-closed erasure blocking when the assertion participates in assertion
  lifecycle transitions;
- restore reconciliation that reapplies the newer deletion-control ledger before
  serving/rebuild state is trusted.

Task 6 deliberately does **not** implement FastAPI routes, real Authority,
embeddings, Vera, ACL integration, production backup orchestration, or later Kernel
features.

## Task 6 semantic conventions

### Fence first

Restriction/erasure is not ordinary assertion supersession. The control sequence is:

```text
deletion/restriction request
        |
        v
kc_control fence becomes authoritative
        |
        +--> serving eligibility closes immediately
        +--> affected derived rows are removed
        |
        v
optional specialized payload reconciliation/erasure
```

A physical erasure failure leaves the case `blocked`, which remains an active
serving fence. Failure to complete cleanup therefore does not reopen access.

### Serving versus raw Kernel internals

Task 6 adds serving-safe reads/projections rather than pretending that raw
storage/debug methods are authorization-aware APIs. The future service-only API
must call the serving-safe path and must not expose inherited raw Kernel reads as
client retrieval endpoints.

### Minimal erasure tombstone

The bounded Gate 15 implementation physically erases a standalone assertion
payload only. It retains:

- opaque `knowledge_ref.ref_id`;
- physical `ref_kind`;
- creation/control identity needed for referential integrity;
- `payload_state = erased_tombstone`;
- deletion-control state.

The erased assertion value and assertion semantic row are no longer retrievable.

Task 6 does not yet physically erase resource artifacts. Logical resources can be
fenced from serving, but artifact-byte erasure/reconciliation is a later privacy
implementation concern and must not be assumed complete.

### Anti-resurrection

Serving eligibility consults the higher-durability deletion-control ledger itself,
not only a mutable restored `payload_state`. Therefore a simulated stale restore
that makes canonical/derived rows look active again remains non-serving before
reconciliation. `reapply_deletion_control_before_serving()` then restores canonical
payload-state fencing and removes stale derived rows.

## Task 6 focused tests authored

`tests/test_task6_deletion.py` contains six focused cases:

1. assertion restriction disappears from current/serving retrieval before payload
   cleanup;
2. fencing a logical resource hides its exact resource version from serving reads;
3. minimal assertion erasure leaves only an opaque erased tombstone/control state;
4. stale restored canonical/derived state cannot outrank the newer deletion ledger;
5. an identical fence retry replays one deletion case rather than duplicating it;
6. rebuilding the current projection cannot resurrect a fenced assertion.

## Validation checkpoint

Validation actually performed in this session:

- starting remote branch HEAD verified as
  `0811be71bf5fc7abc0deba53e45937fcabcd8ad0`;
- Task 6 source/migration/test strings passed Python syntax compilation before
  commit;
- committed Task 6 application logic was reread for fail-open/fail-closed behavior;
- Task 6 deletion-control table shapes compiled successfully to PostgreSQL DDL in
  an isolated SQLAlchemy check;
- implementation diff from the Task 5 checkpoint is one commit ahead and zero
  behind before this documentation commit;
- GitHub exposes no workflow run for implementation commit `be41c089`;
- an attempted local clone for real test execution failed because the execution
  environment could not resolve `github.com`.

### Validation not completed

The focused Task 6 tests were **authored but not runtime-executed** in this
session. A live PostgreSQL service was also unavailable.

This checkpoint therefore does **not** claim:

- Gate 12 or Gate 13 runtime acceptance for Task 5;
- Gate 14, Gate 15, or Gate 16 runtime acceptance for Task 6;
- `pytest` execution of `test_task5_identity.py` or `test_task6_deletion.py`;
- Alembic application of migrations `0001_task1` through `0006_task6` to a running
  PostgreSQL database;
- production backup/restore anti-resurrection proof.

## Known bounded limitations

- Task 5 runtime validation remains unresolved.
- Task 6 runtime validation remains unresolved.
- Task 6 implements physical erasure only for a bounded standalone assertion case.
- Resource/artifact bytes are not physically erased by Task 6.
- Initial fence creation is managed/idempotent; later internal restriction-settle
  and assertion-erasure reconciliation methods are not separate external
  operation-ID APIs.
- Raw lower-level Kernel reads remain internal/debug paths and are not a serving
  authorization boundary.
- No real Authority decision service is implemented here.

## Stop point

Task 6 implementation is checkpointed, but **Task 6 is not acceptance-validated
and no later task has started.**

The next permitted action is:

> Run the focused Task 5 and Task 6 tests plus migration validation. Record Gates
> 12–16 as accepted only if that evidence passes.

Do not make a final Kernel acceptance claim or begin another implementation slice
while these validation debts remain unresolved unless the user explicitly directs
another bounded override.

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
