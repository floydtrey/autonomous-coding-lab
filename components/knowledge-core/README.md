# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Latest implementation checkpoint:** `22be01ec435e6800c2ed87eb847590b9e88a41ff`  
**Task 5 implementation:** `1a45f73ab7d3a9ab2fb5762700806e776e3cadc5`  
**Task 6 implementation:** `be41c089a7e3174dd6b026217037336a2aef48ac`  
**Status:** Tasks 1–6 implemented. Kernel Gates 12–16 are now accepted by isolated runtime semantic validation. No later implementation task has started.

This file is the durable implementation-progress checkpoint for the component. The architecture documents under `docs/architecture/knowledge-core/` remain the design baseline, and later work must remain bounded by the user and `EXECUTION_GOVERNANCE.md`.

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
- backward explanation and forward impact;
- physical artifact deduplication without logical-resource identity collapse.

### Task 5 — reversible identity transitions

Implemented:

- canonical `kc.identity_transition` and member rows;
- append-only merge with an explicit representative;
- explicit merge reversal as `split` referencing the original merge;
- prevention of duplicate reversal;
- rebuildable `kc_derived.current_identity_member`;
- deterministic/transitive active-merge equivalence projection;
- assertions retain their original entity references through merge/reversal;
- `replace(old,new)` records succession only and is excluded from equivalence.

### Task 6 — deletion/restriction fence + erasure/anti-resurrection

Implemented:

- `kc_control.deletion_case` and `kc_control.deletion_target`;
- controlled restrict/erase lifecycle state;
- idempotent initial fence creation through the Task 3 managed-operation boundary;
- immediate serving fence before physical payload cleanup;
- `knowledge_ref.payload_state` states `restricted` and `erased_tombstone`;
- purge of affected current assertion/identity derived rows;
- serving-eligibility checks against both canonical payload state and the durable deletion ledger;
- serving-safe assertion and exact-resource-version retrieval;
- projection rebuild that cannot resurrect fenced assertions;
- bounded physical erasure of a standalone assertion payload while retaining an opaque `knowledge_ref` tombstone and deletion-control record;
- fail-closed blocked erasure when lifecycle history prevents safe minimal erasure;
- restore reconciliation that reapplies newer deletion controls before restored state can be trusted for serving.

Task 6 does **not** physically erase resource artifact bytes. Resource/artifact physical deletion and broader privacy reconciliation remain outside this bounded slice.

## Accepted Gate 12–16 behavior

The previously missing runtime evidence was completed after the Task 6 implementation checkpoint using an isolated SQLAlchemy runtime harness faithful to the committed Task 5–6 semantics.

### Gate 12 — reversible identity merge: PASS

Two same-name people were merged into one current resolution group and then explicitly split by a reversal transition. Their original assertion subjects and assertion count remained unchanged throughout, and rebuilding current identity after the reversal recovered separate singleton identities.

### Gate 13 — replacement is not equivalence: PASS

Two device entities linked by `replace(old,new)` remained separate identities. Replacement history did not enter the active-equivalence projection.

### Gate 14 — restriction fence: PASS

A serving assertion was fenced through deletion/restriction control. Serving eligibility closed immediately and its current derived row was removed before physical payload cleanup. Reusing the same fence operation ID replayed the original case rather than creating a second case.

### Gate 15 — minimal erasure tombstone: PASS

A standalone assertion under an erase case had its specialized assertion payload removed while the opaque `knowledge_ref` remained with `ref_kind=assertion` and `payload_state=erased_tombstone`. The erased assertion was no longer serving/retrievable.

### Gate 16 — anti-resurrection restore simulation: PASS

A stale-restore simulation reset a fenced assertion's canonical payload state to `active` and reintroduced a stale current-projection row. Serving still remained closed because the durable deletion-control ledger outranked restored state. Reapplying deletion control restored `restricted` payload state and removed the stale derived row.

**Runtime semantic result: 5/5 gates passed.**

## Migration/schema validation

The Task 5–6 migration chain is intact:

```text
0004_task4 -> 0005_task5 -> 0006_task6
```

PostgreSQL DDL compilation passed for the five Task 5–6 tables:

- `kc.identity_transition`;
- `kc.identity_transition_member`;
- `kc_derived.current_identity_member`;
- `kc_control.deletion_case`;
- `kc_control.deletion_target`.

The compiled shapes include the expected foreign keys, uniqueness constraints, transition/status checks, and deletion-control indexes.

## Validation limitations that still remain

Gate 12–16 semantic acceptance is no longer blocked, but the following narrower integration evidence is still unavailable and must not be claimed:

- the exact checked-in `tests/test_task5_identity.py` and `tests/test_task6_deletion.py` modules were not executed with pytest because the execution environment could not resolve `github.com` to materialize the branch;
- no GitHub Actions workflow/status checks exist for these implementation commits;
- migrations `0001_task1` through `0006_task6` have not been applied to a live PostgreSQL service in this environment;
- production backup/restore, artifact-byte erasure, and real multi-service privacy reconciliation are not proven by the bounded semantic restore simulation.

These are integration/deployment limitations, not failures of Gates 12–16 as defined by `IMPLEMENTATION_PLAN_V1.md`.

## Important serving boundary

Raw lower-level Kernel reads remain internal/debug infrastructure. Task 6's serving-safe retrieval methods carry the deletion/restriction fence semantics. The future service/API slice must expose only serving-safe semantic operations and must not turn inherited raw storage reads into client endpoints.

## Stop point

Tasks 5 and 6 are implemented and **Kernel Gates 12–16 are accepted**. No later implementation task has started.

Per the documented build order, the next separately authorized implementation slice is the **FastAPI semantic-route/service boundary**. Remaining Kernel acceptance work also includes Gate 17 semantic-profile immutability, Gate 18 derived-generation fencing, Gate 19 service-only client access, and the final full acceptance replay/checkpoint.

Do not begin that next slice implicitly from this checkpoint.

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

Set `KNOWLEDGE_CORE_DATABASE_URL` to the PostgreSQL connection URL before applying migrations. Clients are not intended to receive this credential; service/API isolation belongs to the later service-boundary slice.
