# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Task 9 starting checkpoint:** `6bd4872531c899298754a4409e88ac90f0edec80`  
**Task 9 implementation commits:** `0dac8b8d199a87c2698c06fcebdecd6512a94e9b`, `6d60a960fd3886dde81a9aade4909375623103b3`, `cc2f1ae84fdf543e61441e2f641b915c3089e882`  
**Status:** Tasks 1–9 are implemented. Kernel Gates 12–18 are accepted by bounded runtime semantic validation. Gate 19 and the final Kernel acceptance replay remain unresolved; no later implementation task has started.

The architecture documents under `docs/architecture/knowledge-core/` remain the design baseline. Later work must remain bounded by the user and `EXECUTION_GOVERNANCE.md`.

## Implemented Kernel boundary

### Tasks 1–6

Implemented the canonical typed assertion/history foundation, bitemporal current projection, managed operation/idempotency and stale-writer protection, exact resource-version provenance, reversible identity transitions, and deletion/restriction anti-resurrection fence.

Kernel Gates 12–16 were accepted at checkpoint `e018e86f92d5f504637807bdee78c28852498841` through isolated runtime semantic validation.

### Task 7 — bounded FastAPI semantic service boundary

Implemented the first FastAPI/Pydantic service-only semantic boundary for health/status, entities, assertions, temporal retrieval, correction/reversal, and identity transitions. Exposed mutations use Task 3 managed-operation semantics; serving reads and newly executed serving mutations honor the Task 6 fence. Raw SQL/database credentials and privileged deletion/admin routes are not exposed.

Task 7 deliberately does not expose resource ingestion yet. Exact duplicate re-ingest can be a valid semantic no-op with no new canonical revision, while the current generic managed-operation helper assumes every successful managed operation creates one. That mismatch must be resolved before the resource/provenance HTTP path and Gate 19 are complete.

### Task 8 — semantic profile immutability / Gate 17

Implemented append-only `kc_control.profile_activation`, immutable exact profile revisions, managed profile revision creation/activation, exact assertion semantic resolution through pinned revision refs, and the rule that a material predicate shape change requires a new predicate identity or explicit future migration path.

**Gate 17: accepted.**

### Task 9 — derived-generation staleness/fencing / Gate 18

Implemented:

- `kc_derived.generation`;
- `kc_derived.generation_source`;
- migration `0008_task9_generation_fencing.py` with chain `0007_task8 -> 0008_task9`;
- exact generation lineage through canonical source revision high-water, optional exact profile revision, optional model identity/version/config digest, and exact source refs/revisions;
- explicit generation states `building`, `current`, `stale`, `failed`, `superseded`, `restricted`, and `deletion_pending`;
- a monotonic `generation_sequence` assigned while holding a PostgreSQL transaction advisory lock;
- a PostgreSQL/SQLite partial unique index allowing only one `current` generation per derived kind;
- explicit stale marking when a source/profile change invalidates an earlier generation;
- atomic promotion of a validated builder to `current`;
- explicit `supersedes_generation` lineage when a newer generation replaces an older current generation;
- an out-of-order finish fence: a lower-sequence builder cannot become current after a higher-sequence generation has already settled current;
- late obsolete builders are marked `stale` rather than silently winning;
- idempotent reads of already-current/already-stale generation state;
- focused Task 9 tests authored for the literal Gate 18 sequence, the stronger unmarked-race case, supersession, and exact lineage.

## Gate 18 fencing model

Generation timestamps are descriptive, not the ordering authority for settlement.

The bounded Kernel uses a monotonic sequence allocated under the generation transaction lock:

```text
generation 41 starts
        |
        +--- source/profile changes
        |
generation 42 starts and settles CURRENT
        |
generation 41 finishes late
        |
        +--- sequence 41 < current sequence 42
             => generation 41 becomes STALE
             => generation 42 remains CURRENT
```

This avoids using wall-clock completion order as a race-resolution mechanism.

Promotion also releases the existing partial-unique `current` slot before assigning it to the newer generation inside the same serialized transaction. This ordering is intentional for PostgreSQL uniqueness enforcement.

Derived generation lifecycle is rebuild/control state, not canonical semantic truth. It therefore uses generation fencing rather than pretending every derived-state transition is a new canonical knowledge revision.

## Gate 18 validation performed

Bounded runtime semantic validation passed:

1. create an old derived generation from source/profile revision 1;
2. mark the old generation stale after the source/profile state changes;
3. create a new generation against the newer canonical/profile state;
4. settle the new generation current;
5. attempt to finish the old stale generation and verify it cannot replace the new current generation;
6. independently start two builders without explicitly staling the older one, settle the newer one first, and verify the older late finisher is automatically fenced stale;
7. settle a newer generation over an older current generation and verify the older row becomes `superseded` with explicit supersession lineage;
8. verify exact source/profile/model/config lineage remains attached to the generation.

**Gate 18 semantic result: PASS.**

Additional validation performed:

- all new Task 9 source/migration/test files passed Python syntax compilation before commit;
- an isolated SQLAlchemy runtime harness passed the literal Gate 18 sequence and stronger out-of-order race case;
- PostgreSQL DDL compilation passed for `kc_derived.generation`, `kc_derived.generation_source`, their lineage/index constraints, and the partial unique current-generation index;
- final Task 9 implementation diff from `6bd48725` is three commits ahead and zero behind before this documentation checkpoint;
- the implementation diff is confined to seven Knowledge Core paths;
- GitHub exposes no Actions workflow run for implementation head `cc2f1ae84fdf543e61441e2f641b915c3089e882`.

### Validation not claimed

This checkpoint does **not** claim:

- execution of the exact checked-in `tests/test_task9_generations.py` from a materialized repository checkout; the local runtime still cannot resolve `github.com`;
- live PostgreSQL application of migrations `0001_task1` through `0008_task9`;
- a real concurrent multi-process PostgreSQL race test;
- generation IDs already attached to every existing current/assertion/identity projection row;
- Gate 19 acceptance;
- final 19-gate Kernel acceptance.

The current Gate 18 slice proves generation lifecycle/fencing and lineage control. Individual derived families can adopt the generation ID as they are moved onto generation-managed rebuilds; that adoption must preserve the fencing rules rather than create an alternate currentness mechanism.

## Task 9 bounded implementation decision

The physical schema already required generation fencing but did not define a race-safe total order for competing builders. Task 9 records the following bounded implementation rule:

> **Derived-generation promotion uses a monotonic generation sequence, not wall-clock completion time, as the settlement fence.** PostgreSQL generation creation/promotion is serialized with a transaction advisory lock, and a partial unique index permits one current generation per bounded `derived_kind`. A generation with a lower sequence may never replace a higher-sequence generation that has already settled current.

This is an implementation strengthening of KC-D015/KC-D018 and `PHYSICAL_SCHEMA_V1.md`; it does not make derived state canonical truth.

## Existing unresolved Kernel work

The following work remains before a final Kernel checkpoint:

1. resolve safe managed-operation semantics for a successful **no-canonical-mutation** resource re-ingest;
2. expose the resource/provenance semantic HTTP path only after that operation model is safe;
3. **Gate 19 — service-only client acceptance replay** through FastAPI/TestClient or real loopback HTTP;
4. full 19-gate replay/checkpoint;
5. live PostgreSQL migration/integration validation when an execution environment is available.

Earlier bounded deployment/privacy limitations also remain:

- Task 6 physically erases only the bounded standalone assertion case, not resource artifact bytes;
- production backup/restore and multi-service privacy reconciliation remain unproven;
- real authentication/TLS/firewall behavior and the real Authority service are not implemented;
- raw lower-level Kernel methods remain internal/debug infrastructure and must not be exposed as client APIs.

## Stop point

Task 9 is implemented and **Gate 18 is accepted**. No Gate 19 / later implementation work has started.

The next separately authorized bounded slice should resolve the resource-ingest operation-model mismatch required for the complete service-only Gate 19 path, then perform Gate 19 acceptance. Do not add Vera/ACL domain features, embeddings, or Authority implementation as part of that slice.

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
