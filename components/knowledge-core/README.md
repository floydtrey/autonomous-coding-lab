# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Task 10 starting checkpoint:** `9a338a024dc1cd5fcf01366fe3dad8311d58311c`  
**Task 10 implementation commits:** `61ac18619b1c40b9b258362312762dc1c5a8f385`, `8db4394e6e05fb7ed012e0dc33001f7f43fe88f6`, `b673cfdf7d6e82303fafc97f0c80341ec2688b6e`  
**Status:** Tasks 1–10 are implemented. Gates 12–18 remain accepted. The resource-ingest operation-model blocker required for Gate 19 is resolved and the resource/provenance HTTP path is now implemented. Gate 19 and the final 19-gate replay remain unresolved.

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

The physical schema already allowed this outcome because `kc_control.operation.result_revision_id` is nullable. Task 10 therefore requires no new migration; the blocker was application settlement logic rather than table shape.

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

Task 10 preserves this ordering:

1. operation ledger validates/replays the settled operation;
2. no new resource mutation occurs;
3. HTTP response construction applies current Task 6 serving eligibility;
4. restricted resource/version content remains unavailable.

Likewise, assertion explanation filters out evidence versions that are now restricted, while forward impact for a restricted resource version fails closed.

## Task 10 validation

A bounded local SQLAlchemy semantic harness passed the operation-model sequence:

1. first exact ingest creates a resource version and canonical revision;
2. exact duplicate ingest under a new operation ID settles `committed` with `result_revision_id = NULL`;
3. the canonical revision high-water remains unchanged for that no-op;
4. retry of the same no-op operation returns the same resource version without another mutation;
5. reuse of that operation ID with different bytes is rejected;
6. the same exact version plus a previously unseen locator creates a canonical revision and non-null operation result revision;
7. replay followed by current serving-fence evaluation prevents a later-restricted result from being disclosed.

**Task 10 blocker result: PASS.**

Focused repository coverage in `tests/test_task10_resource_api.py` additionally exercises the actual intended HTTP contract for:

- service-only logical resource creation and exact-version ingest;
- no-op operation settlement/replay;
- exact evidence linking, backward explanation, and forward impact;
- absence of artifact backend/key disclosure;
- restriction after settlement followed by ingest replay;
- explanation filtering and impact fail-closed behavior.

Review also found one expected cross-task regression: the old Task 7 test asserted that `/v1/resources/ingest` was absent. That assertion was intentionally valid before Task 10 made resource writes safe. Commit `b673cfdf7d6e82303fafc97f0c80341ec2688b6e` updates the test to preserve the actual invariant—no deletion/admin/raw privileged routes—while recognizing the now-managed resource route.

GitHub exposes no Actions workflow run for the Task 10 implementation head.

### Validation not claimed

This checkpoint does **not** claim:

- execution of the exact checked-in `tests/test_task10_resource_api.py` from a materialized full repository checkout;
- execution of the complete checked-in Task 1–10 pytest suite;
- live PostgreSQL application of migrations `0001_task1` through `0008_task9`;
- live PostgreSQL operation/no-op integration;
- Gate 19 acceptance;
- final 19-gate Kernel acceptance.

The local execution runtime still has neither working DNS nor outbound connectivity to GitHub, so the branch cannot be cloned there. GitHub connector access is used for durable repository reads/writes.

## Existing accepted gates

- Gates 12–16: accepted at checkpoint `e018e86f92d5f504637807bdee78c28852498841`.
- Gate 17: accepted at checkpoint `6bd4872531c899298754a4409e88ac90f0edec80`.
- Gate 18: accepted at checkpoint `9a338a024dc1cd5fcf01366fe3dad8311d58311c`.

## Remaining Kernel work

The next separately authorized bounded slice is now:

1. **Gate 19 — service-only client acceptance replay** through FastAPI/TestClient or real loopback HTTP;
2. if Gate 19 passes, perform the final 19-gate Kernel replay/checkpoint and freeze the Kernel boundary;
3. retain live PostgreSQL migration/integration validation as an explicit environment-dependent deployment/integration item if it still cannot be executed here.

Earlier bounded limitations also remain:

- Task 6 physically erases only the bounded standalone assertion case, not resource artifact bytes;
- production backup/restore and multi-service privacy reconciliation remain unproven;
- real authentication/TLS/firewall behavior and the real Authority service are not implemented;
- generation IDs are not yet attached to every historical derived projection family;
- raw lower-level Kernel methods remain internal/debug infrastructure and must not be exposed as client APIs.

## Stop point

Task 10 is implemented and the resource operation-model blocker is resolved. **Gate 19 has not started.**

Do not add Vera/ACL domain features, embeddings, Authority implementation, or production deployment expansion before the Kernel acceptance boundary is closed.

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
