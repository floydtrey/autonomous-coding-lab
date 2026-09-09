# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Task 8 starting checkpoint:** `cf0e3703a2fa762147b0f86cc6a3f2dbddd84c08`  
**Task 8 implementation commit:** `c9dc15332183d05a39f37b338fa2a2459404a851`  
**Status:** Tasks 1–8 are implemented. Kernel Gates 12–17 are accepted by bounded runtime semantic validation. Gate 18 and Gate 19 remain unresolved; no later implementation task has started.

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

Implemented the first FastAPI/Pydantic service-only semantic boundary for health/status, entities, assertions, temporal retrieval, correction/reversal, and identity transitions. Exposed mutations use Task 3 managed-operation semantics; serving reads and newly executed serving mutations honor the Task 6 fence. Raw SQL/database credentials and privileged deletion/admin routes are not exposed.

The Task 7 review also found and fixed a fence/idempotency ordering bug: serving-fence checks now run inside the managed operation action so a settled retry remains deterministic after later restriction, while a new write against a restricted target still fails closed.

Task 7 intentionally does not expose resource ingestion yet because an exact duplicate re-ingest can be a valid semantic no-op with no new canonical revision, while the current generic managed-operation helper assumes every successful managed operation creates one. That operation-model mismatch must be resolved before the resource/provenance HTTP path and Gate 19 are complete.

### Task 8 — semantic profile immutability / Gate 17

Implemented:

- `kc_control.profile_activation` as append-only operational activation history;
- migration `0007_task8_profile_immutability.py` with chain `0006_task6 -> 0007_task8`;
- managed/idempotent creation of a new exact semantic profile revision from a source revision;
- carried-forward kind/predicate identities with **new exact revision refs** pinned to the new profile revision;
- managed/idempotent activation of a profile revision for new writes;
- current active-profile selection from the latest activation event rather than mutating an old profile snapshot;
- explicit assertion-semantic resolution through the assertion’s pinned profile/predicate revision refs;
- managed creation of a new semantic predicate identity for a material meaning change;
- an application invariant that rejects changing the currently modeled material predicate shape (`scalar` versus `reference`) under the same predicate identity;
- focused Gate 17 test coverage for revision activation, old-assertion semantic preservation, new-write use of revision 2, material meaning change, and operation replay.

## Gate 17 semantic conventions

### Activation is operational state, not semantic mutation

`semantic_profile_revision` remains an exact immutable semantic snapshot. Activation does not change the revision row and does not rewrite assertions.

The operational history is:

```text
profile revision 1 --activation event--> current for new writes
profile revision 2 --activation event--> current for new writes
```

The latest activation event selects the revision used by callers that ask for the active revision. Older activation events remain in `kc_control.profile_activation`.

### Assertions remain pinned to the semantics they were written under

An assertion stores both:

- `profile_revision_ref`;
- `predicate_revision_ref`.

Activating revision 2 therefore does not reinterpret a revision-1 assertion. Resolution follows the exact stored revision refs, not the current activation pointer.

### Material predicate meaning change requires a new identity

The current Kernel physically models predicate meaning only to the bounded extent needed by the first gates, including `value_shape` (`scalar` or `reference`). A change between those shapes is treated as material.

Task 8 rejects appending such a changed shape under the same `semantic_predicate` identity and requires a new predicate identity (or a future explicit governed migration path). This implements the Gate 17 rule without pretending the current small Kernel already models every future semantic dimension such as cardinality, inference flags, or rich validation schema.

## Gate 17 validation performed

Runtime semantic validation passed the bounded Gate 17 scenarios:

1. activate profile revision 1;
2. create an assertion under revision 1;
3. create revision 2 by carrying forward the same semantic identities into new exact kind/predicate revisions;
4. activate revision 2;
5. verify the old assertion still resolves exactly under revision 1 semantics;
6. create a new assertion under revision 2 and verify it resolves under revision 2 while sharing the unchanged predicate identity;
7. attempt to change `has_name` from `scalar` to `reference` under the same predicate identity and verify rejection with no canonical revision advance;
8. create a new predicate identity with `reference` shape and verify the new identity/revision is distinct;
9. verify profile-revision creation and activation operations replay idempotently.

**Gate 17 semantic result: PASS.**

Additional validation:

- new Task 8 source/test strings passed Python syntax compilation before commit;
- PostgreSQL DDL compilation passed for `kc_control.profile_activation` and its indexes;
- the Task 8 implementation diff from `cf0e3703` is one commit ahead and zero behind before this documentation checkpoint;
- the implementation diff is confined to five Knowledge Core paths;
- GitHub exposes no Actions workflow run for implementation commit `c9dc15332183d05a39f37b338fa2a2459404a851`.

### Validation not claimed

This checkpoint does **not** claim:

- execution of the exact checked-in `tests/test_task8_profiles.py` from a materialized repository checkout; the local runtime still cannot resolve `github.com`;
- live PostgreSQL application of migrations `0001_task1` through `0007_task8`;
- database-level trigger protection against a privileged operator issuing arbitrary direct SQL updates to semantic tables;
- full future semantic-profile fields such as manifest digests, imports/dependencies, rich validation schemas, cardinality, or inference flags;
- Gate 18 or Gate 19 acceptance;
- final 19-gate Kernel acceptance.

Gate 17 is accepted at the Kernel semantic-operation level. Raw direct database mutation remains outside the intended client boundary and is not treated as a supported semantic operation.

## Task 8 architecture decision recorded in controlling state

The bounded physical decision introduced by Task 8 is:

> **Active semantic-profile revision is append-only operational control, separate from immutable semantic profile revisions.** `kc_control.profile_activation` records activation events ordered by canonical revision; the latest event selects the revision for new writes. Activation never rewrites prior profile/predicate revisions or assertions. Within the current Kernel’s modeled semantics, a predicate `value_shape` change is material and requires a new predicate identity or explicit future migration path.

This decision is consistent with KC-D012 and `PHYSICAL_SCHEMA_V1.md`, which already state that exact profile revisions are immutable and that an “active for new writes” pointer is operational/current configuration rather than a rewrite of historical assertions.

## Existing unresolved Kernel work

The following work remains before a final Kernel checkpoint:

1. **Gate 18 — derived generation staleness/fencing**;
2. complete safe managed-operation semantics for successful no-canonical-mutation resource re-ingest;
3. expose the resource/provenance semantic HTTP path only after that operation model is safe;
4. **Gate 19 — service-only client acceptance replay**;
5. full 19-gate replay/checkpoint;
6. live PostgreSQL migration/integration validation when an execution environment is available.

Earlier bounded deployment/privacy limitations also remain:

- Task 6 physically erases only the bounded standalone assertion case, not resource artifact bytes;
- production backup/restore and multi-service privacy reconciliation remain unproven;
- real authentication/TLS/firewall behavior and the real Authority service are not implemented;
- raw lower-level Kernel methods remain internal/debug infrastructure and must not be exposed as client APIs.

## Stop point

Task 8 is implemented and **Gate 17 is accepted**. No Gate 18 / Task 9 implementation has started.

The next separately authorized implementation slice is:

> **Gate 18 — derived generation staleness/fencing.**

Do not add Vera/ACL domain features, embeddings, or Authority implementation as part of that slice.

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
