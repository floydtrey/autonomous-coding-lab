# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Task 10 starting checkpoint:** `9a338a024dc1cd5fcf01366fe3dad8311d58311c`  
**Status:** Tasks 1–9 are accepted through Gate 18. Task 10 resolves the managed resource no-op/API blocker required before Gate 19. Gate 19 and the final 19-gate replay are not yet claimed.

## Task 10 — managed resource no-op + resource/provenance HTTP boundary

Task 7 correctly deferred resource ingestion because exact duplicate re-ingest can be a valid semantic no-op with no new canonical revision, while the generic Task 3 managed-operation helper previously treated every successful operation without a new `kc.revision` as an invariant failure.

Task 10 resolves that mismatch without weakening ordinary write guarantees.

### Explicit no-op capability

`OperationKnowledgeKernel._execute_operation()` now accepts an explicit `allow_no_canonical_revision` flag that defaults to `False`.

- ordinary managed writes remain strict and still fail if they unexpectedly create no canonical revision;
- only a semantic operation whose contract explicitly permits a canonical no-op may opt in;
- exact duplicate resource-version re-ingest is the first such operation.

A successful exact duplicate ingest with no new locator therefore settles:

```text
kc_control.operation.status = committed
kc_control.operation.result_revision_id = NULL
canonical kc.revision high-water = unchanged
```

The operation still records stable request digest and replay metadata, so retry remains deterministic.

If the same exact resource version gains a new locator observation, that is not a no-op. The locator occurrence creates a canonical revision and the operation receives a non-null `result_revision_id`.

### Resource service application boundary

`ResourceServiceKnowledgeKernel` adds service-safe wrappers around the existing Task 4 resource/provenance semantics:

- managed logical-resource creation;
- managed exact-version ingest;
- managed assertion-evidence linking;
- serving-safe logical resource/version reads;
- serving-safe assertion explanation;
- serving-safe exact-version forward impact.

New mutations check Task 6 serving fences inside the managed operation action. Settled operation replay remains an execution-ledger fact; current serving eligibility is evaluated separately before an HTTP result is returned.

### Resource/provenance HTTP routes

The bounded v1 service now includes:

```text
POST /v1/resources
POST /v1/resources/ingest
GET  /v1/resource-versions/{resource_version_ref}
POST /v1/assertions/{assertion_ref}/evidence
GET  /v1/assertions/{assertion_ref}/explain
GET  /v1/resources/{resource_version_ref}/impact
```

Resource version responses expose semantic/version metadata only. Internal artifact backend names and artifact keys are deliberately absent from response schemas/OpenAPI.

### Replay and privacy fence ordering

A previously settled ingest operation may be retried after its resource/version is later restricted. The ledger must not execute the mutation again, but it also must not become a route around current privacy policy.

Task 10 therefore preserves this ordering:

1. operation ledger validates/replays the settled operation;
2. no new resource mutation occurs;
3. HTTP response construction applies current Task 6 serving eligibility;
4. restricted resource/version content remains unavailable.

Likewise, assertion explanation filters out evidence versions that are now restricted, while forward impact for a restricted resource version fails closed.

## Task 10 focused validation authored

`tests/test_task10_resource_api.py` covers:

1. first exact ingest creates a canonical resource version;
2. exact duplicate ingest with a new operation ID settles committed with `result_revision_id = NULL`;
3. canonical revision high-water does not advance on that no-op;
4. retry of the same no-op operation replays the identical resource version;
5. materially different reuse of the same operation ID is rejected;
6. adding a previously unseen locator to the same exact version creates a canonical revision;
7. service-only resource creation, ingest, evidence linking, explanation, and forward impact preserve exact-version lineage;
8. artifact backend/key details are absent from the HTTP contract;
9. after a later restriction fence, a settled ingest replay cannot re-expose the resource version;
10. explanation omits the restricted evidence version and impact fails closed.

## Existing accepted gates

- Gates 12–16: accepted at checkpoint `e018e86f92d5f504637807bdee78c28852498841`.
- Gate 17: accepted at checkpoint `6bd4872531c899298754a4409e88ac90f0edec80`.
- Gate 18: accepted at checkpoint `9a338a024dc1cd5fcf01366fe3dad8311d58311c`.

## Validation limitations

This Task 10 checkpoint must not claim more than is actually executed.

The local runtime still cannot resolve `github.com`, so an exact full repository checkout and checked-in pytest execution remain unavailable unless that environment changes. Live PostgreSQL migration/integration testing also remains outstanding.

Task 10 requires no new database migration because `kc_control.operation.result_revision_id` was already nullable by design; the blocker was application-layer settlement logic, not physical schema shape.

## Remaining Kernel work

After Task 10 is validated/checkpointed, the remaining bounded Kernel work is:

1. **Gate 19 — service-only client acceptance replay** across the required Kernel behaviors through FastAPI/TestClient or loopback HTTP;
2. final 19-gate acceptance/checkpoint;
3. live PostgreSQL migration/integration validation when an execution environment is available.

No Vera/ACL domain features, embeddings, Authority implementation, or production deployment expansion belongs in Task 10.

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
