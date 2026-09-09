# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Task 7 starting checkpoint:** `e018e86f92d5f504637807bdee78c28852498841`  
**Task 7 implementation commits:** `d82c80925c9359bd75373cc2a619fd7d0da1f66b`, `91707a5e43c0ab9046c5e918c949bbbab45256a4`, `07d5ea7d6bf225c20184342d5c1d72218166c81b`  
**Status:** Tasks 1–7 are implemented. Kernel Gates 12–16 remain accepted. Task 7 establishes the first bounded FastAPI/Pydantic semantic service boundary, but Gate 19 and the final Kernel acceptance replay are not yet complete.

The architecture documents under `docs/architecture/knowledge-core/` remain the design baseline. Later work must remain bounded by the user and `EXECUTION_GOVERNANCE.md`.

## Implemented Kernel boundary

### Task 1 — foundation + typed assertion + correction/undo

Implemented canonical revisions/refs, immutable semantic foundations, entities, typed assertions, append-only correction, and explicit reversal.

### Task 2 — bitemporal history + current projection

Implemented independent world/knowledge time, historical belief, conflict preservation, lifecycle-aware current selection, and rebuildable `kc_derived.current_assertion`.

### Task 3 — operation/idempotency + stale-writer protection

Implemented `kc_control.operation`, stable operation IDs/request digests, idempotent settled replay, stale revision rejection, and PostgreSQL managed-write serialization.

### Task 4 — exact resources/provenance

Implemented logical resources, exact resource versions, historical locators, immutable SHA-256 artifacts, exact-version provenance, backward explanation, and forward impact.

### Task 5 — identity transitions

Implemented append-only merge, explicit split reversal, replacement-not-equivalence, and rebuildable current identity projection.

### Task 6 — deletion/restriction fence

Implemented durable restriction/erasure control, serving fences, bounded assertion tombstoning, fail-closed blocked erasure, and anti-resurrection reconciliation.

Kernel Gates 12–16 were accepted at checkpoint `e018e86f92d5f504637807bdee78c28852498841` through isolated runtime semantic validation.

### Task 7 — bounded FastAPI semantic service boundary

Implemented:

- FastAPI/Pydantic dependencies in the component package;
- a versioned HTTP boundary under `knowledge_core/api/`;
- application-layer `ServiceKnowledgeKernel` so HTTP handlers do not query SQL directly;
- required `X-Knowledge-Caller` context for `/v1/*` semantic operations;
- `/health` without semantic caller context;
- `/v1/status` exposing service/API/current-revision state without exposing PostgreSQL credentials;
- operation-managed entity creation;
- operation-managed assertion append/correction;
- operation-managed assertion transition reversal;
- operation-managed identity merge/replace/reversal;
- stale-writer mapping to HTTP 409;
- operation-ID reuse/in-progress/failure mapping to HTTP 409;
- restricted knowledge mapping to an opaque HTTP 404;
- serving-safe entity/assertion/current/history/belief reads;
- deletion-fence checks on newly executed service mutations;
- deterministic replay of already-settled operations even if the target is restricted later;
- FastAPI `TestClient` acceptance-test coverage authored for the bounded route surface;
- explicit exclusion of unmanaged privileged/admin mutation routes.

The HTTP layer does not import or query SQLAlchemy tables. SQL/storage behavior remains behind the application/kernel boundary.

## Task 7 exposed route surface

The first bounded route set is:

```text
GET  /health
GET  /v1/status

POST /v1/entities
GET  /v1/entities/{ref}

POST /v1/assertions
GET  /v1/assertions/{ref}
POST /v1/assertions/{ref}/correct
POST /v1/transitions/{ref}/reverse

GET  /v1/knowledge/current
GET  /v1/knowledge/history
GET  /v1/knowledge/belief

POST /v1/identity/merge
POST /v1/identity/replace
POST /v1/identity/transitions/{ref}/reverse
```

Exact route names remain subordinate to the semantic contract in `IMPLEMENTATION_PLAN_V1.md`.

## Service safety conventions

### Caller context is identification, not Authority

`X-Knowledge-Caller` supplies caller identity context to the current kernel operation ledger. Task 7 does **not** implement authentication or the real Authority service. Deployment must not treat this header alone as authorization.

`/v1/status` explicitly reports `authority_mode = external-not-implemented`.

### Serving reads are deletion-aware

Client-facing entity/assertion/current/history/belief paths use Task 6 serving eligibility rather than raw lower-level storage/debug reads.

Restricted items are returned as unavailable instead of exposing their underlying raw payload.

### New writes versus settled replays

Serving-fence checks are performed inside the managed operation action.

This matters because:

- a **new** write against a restricted target must fail closed;
- an **already-committed** operation retry must replay its previously settled result without executing a new mutation.

The initial Task 7 implementation placed some fence checks before the operation ledger replay decision. Review identified that this could break Task 3 idempotent replay after a later restriction. Commit `91707a5e43c0ab9046c5e918c949bbbab45256a4` moves those checks behind the replay boundary; `07d5ea7d6bf225c20184342d5c1d72218166c81b` adds the regression case.

## Resource/provenance HTTP boundary intentionally deferred

Task 7 does **not** expose `/v1/resources/ingest`, provenance-write, deletion/admin, or generic database routes.

This is deliberate, not an accidental omission.

The current Task 3 `_execute_operation()` helper assumes that every successful managed semantic mutation creates a canonical `kc.revision`.

Task 4 intentionally defines an exact resource re-ingest with no new locator as a semantic no-op:

- same logical resource;
- same exact bytes/digest;
- no new locator observation;
- no new `resource_version`;
- no canonical revision advance.

A thin HTTP wrapper around `ingest_resource_version()` would therefore conflict with the current generic managed-operation invariant on that valid no-op path.

Before exposing resource ingestion, a later bounded task must define and test operation-ledger semantics for successful no-canonical-mutation results (or refactor resource ingest into an equivalent safe transaction model). Do not bypass the operation ledger simply to add the route.

This issue must also be resolved before the final Gate 19/full acceptance replay can claim the complete semantic API path.

## Task 7 validation performed

Validation actually performed for this checkpoint:

- all new Task 7 Python source/test strings compiled successfully;
- FastAPI/Pydantic/TestClient dependencies are available in the execution environment;
- isolated API contract smoke test passed:
  - `/health` -> 200;
  - missing caller context on `/v1/status` -> 400;
  - caller-scoped `/v1/status` -> 200;
  - status reported `database_credentials_exposed = false`;
  - generated OpenAPI contained the intended 14 bounded route paths;
- isolated application-service smoke test passed for managed entity dispatch and restriction rejection;
- replay/fence regression smoke passed:
  - a committed correction replay returned the identical settled transition after the target was later restricted;
  - a new correction against the restricted target raised `KnowledgeRestrictedError`;
- Task 7 committed test module contains four focused HTTP test groups covering service-only access, idempotent writes/stale conflict/fencing, managed identity operations, and absence of unmanaged resource/admin routes;
- final Task 7 implementation diff from `e018e86` is three commits ahead and zero behind before this documentation checkpoint;
- the diff is confined to six Knowledge Core files/paths;
- GitHub exposes no Actions workflow run for implementation head `07d5ea7d6bf225c20184342d5c1d72218166c81b`.

### Validation not claimed

This checkpoint does **not** claim:

- execution of the exact checked-in `tests/test_task7_api.py` against a materialized full repository checkout;
- a live PostgreSQL FastAPI integration run;
- real authentication/TLS/firewall behavior;
- real Authority-service authorization;
- resource/provenance mutation over HTTP;
- Gate 19 acceptance;
- final 19-gate Kernel acceptance.

The execution environment still cannot resolve GitHub from its local runtime, so the full component checkout cannot be materialized there for exact pytest execution. The GitHub connector itself was used for repository reads/writes.

## Existing deployment limitations

The following earlier limitations remain:

- migrations `0001_task1` through `0006_task6` have not been applied to a live PostgreSQL service in this environment;
- Task 6 physically erases only the bounded standalone assertion case, not resource artifact bytes;
- production backup/restore and multi-service privacy reconciliation remain unproven;
- raw lower-level Kernel methods remain internal/debug infrastructure and must not be exposed directly by future client APIs.

## Stop point

Task 7 is implemented and checkpoint-ready. **No Task 8 work has started.**

Remaining Kernel acceptance work includes:

1. Gate 17 — semantic profile immutability;
2. Gate 18 — derived-generation staleness/fencing;
3. completing the resource/provenance managed HTTP path without weakening operation semantics;
4. Gate 19 — service-only acceptance replay through FastAPI/TestClient or loopback HTTP;
5. the final 19-gate Kernel replay/checkpoint.

The next separately authorized implementation slice should remain bounded to the next unresolved Kernel gate(s), rather than adding Vera/ACL domain features, embeddings, or Authority implementation.

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
