# Knowledge Core Implementation Plan V1

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Component:** Knowledge Core  
**Phase:** first implementation vertical slice  
**Status:** architecture plan; implementation not yet started

---

# Goal

Build the smallest real Knowledge Core kernel that can falsify the V1 physical architecture before Vera, ACL, Authority, embeddings, or broad domain features depend on it.

The first slice is a **kernel validation lab**, not a production Vera memory system.

It must prove the difficult invariants early while changing the design is still cheap.

---

# Scope

The V1 kernel includes:

- PostgreSQL-backed canonical history;
- FastAPI/Pydantic semantic API;
- local content-addressed artifact storage;
- minimal semantic core/test profile;
- entities;
- assertions and typed values;
- occurrences;
- assertion correction/supersession/reversal;
- world-valid versus knowledge-record time;
- exact resource-version provenance;
- reversible identity transitions;
- operation/idempotency records;
- current-state projection and rebuild;
- minimal derived-generation state;
- deletion/restriction fencing and tombstone behavior sufficient to validate anti-resurrection logic;
- integration/acceptance tests.

---

# Explicitly out of scope

Do **not** add during the first kernel slice:

- Vera integration;
- ACL integration;
- autonomous workers;
- Authority service implementation;
- Effect Executor implementation;
- real car/home/email/action adapters;
- pgvector embeddings;
- vector indexes;
- external graph/vector/search databases;
- full ACL domain profile;
- full Vera household/device profile;
- production identity-resolution heuristics;
- production privacy/legal policy engine;
- Windows service installer;
- production backup scheduler;
- cloud deployment;
- UI.

The slice is complete when the architecture gates pass, not when it has many features.

---

# Initial component layout

```text
components/
└── knowledge-core/
    ├── README.md
    ├── pyproject.toml
    ├── alembic.ini
    │
    ├── knowledge_core/
    │   ├── __init__.py
    │   ├── app.py
    │   ├── config.py
    │   │
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── dependencies.py
    │   │   ├── errors.py
    │   │   ├── schemas.py
    │   │   └── routes/
    │   │       ├── health.py
    │   │       ├── entities.py
    │   │       ├── assertions.py
    │   │       ├── resources.py
    │   │       ├── history.py
    │   │       └── maintenance.py
    │   │
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── operations.py
    │   │   ├── assertions.py
    │   │   ├── history.py
    │   │   ├── identity.py
    │   │   ├── resources.py
    │   │   ├── deletion.py
    │   │   └── projections.py
    │   │
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── enums.py
    │   │   ├── ids.py
    │   │   ├── temporal.py
    │   │   ├── assertions.py
    │   │   ├── transitions.py
    │   │   └── errors.py
    │   │
    │   ├── storage/
    │   │   ├── __init__.py
    │   │   ├── database.py
    │   │   ├── models/
    │   │   │   ├── canonical.py
    │   │   │   ├── semantic.py
    │   │   │   ├── control.py
    │   │   │   └── derived.py
    │   │   └── repositories/
    │   │       ├── canonical.py
    │   │       ├── assertions.py
    │   │       ├── resources.py
    │   │       ├── identity.py
    │   │       ├── control.py
    │   │       └── projections.py
    │   │
    │   ├── artifacts/
    │   │   ├── __init__.py
    │   │   ├── store.py
    │   │   └── hashing.py
    │   │
    │   ├── profiles/
    │   │   ├── __init__.py
    │   │   ├── loader.py
    │   │   └── validation.py
    │   │
    │   ├── projections/
    │   │   ├── __init__.py
    │   │   ├── current_assertions.py
    │   │   ├── current_identity.py
    │   │   └── rebuild.py
    │   │
    │   └── authority/
    │       ├── __init__.py
    │       └── interface.py
    │
    ├── migrations/
    │   ├── env.py
    │   └── versions/
    │
    ├── profiles/
    │   └── core-test/
    │       ├── profile.json
    │       └── README.md
    │
    ├── scripts/
    │   ├── rebuild_current.py
    │   └── verify_store.py
    │
    └── tests/
        ├── conftest.py
        ├── unit/
        ├── integration/
        └── acceptance/
```

This is the initial physical package layout, not a permanent promise that every folder survives forever. Empty abstraction folders should not be created merely to satisfy the diagram; create them when the slice needs them.

---

# Why these folders exist

## `api/`

HTTP boundary only.

Responsibilities:

- parse/validate request;
- identify authenticated caller context supplied by the deployment layer;
- call semantic application operation;
- map typed result/error to HTTP response.

Must not contain SQL/domain business rules.

## `application/`

Semantic use cases/orchestration.

Examples:

- append assertion;
- correct assertion;
- reverse transition;
- retrieve historical belief;
- ingest resource;
- merge/split identity;
- fence deletion target;
- rebuild current projection.

This is where transaction boundaries and repository interactions are coordinated.

## `domain/`

Database/framework-independent semantic types/rules that can be expressed without SQL or FastAPI.

Examples:

- operation/result enums;
- value-state rules;
- temporal query modes;
- transition types;
- typed IDs;
- invariant errors.

Do not create a giant object-oriented domain hierarchy just to mirror every table.

## `storage/`

PostgreSQL implementation.

- DB engine/session/transaction setup;
- SQL models/table mapping;
- repositories/queries;
- no FastAPI request objects.

## `artifacts/`

Content-addressed local artifact backend.

- stage bytes;
- SHA-256;
- immutable commit;
- verify/read;
- orphan/reconciliation helpers.

## `profiles/`

Runtime loading/validation of immutable semantic profiles.

The actual profile manifests used by deployments live in component-level `profiles/` so they are visible/versionable artifacts rather than hidden Python constants.

## `projections/`

Rebuildable current/derived logic.

Current-state rebuild belongs here instead of being mixed into canonical repositories.

## `authority/interface.py`

Only the **interface/contract** to an external Authority service for now.

The first kernel uses a test/dev authority stub supplied by tests/application bootstrap. Do not implement the real Authority service inside Knowledge Core.

## `migrations/`

Alembic migrations for the Knowledge Core PostgreSQL database.

The repository's top-level historical `migration/` directory is not reused for live Knowledge Core database migrations.

---

# First PostgreSQL migration scope

The first migration should include enough of `PHYSICAL_SCHEMA_V1.md` to exercise every kernel gate without adding unused future tables.

Expected initial tables:

### `kc`

- revision
- knowledge_ref
- semantic_profile
- semantic_profile_revision
- semantic_predicate
- semantic_predicate_revision
- semantic_kind
- semantic_kind_revision
- semantic_role
- semantic_role_revision
- entity
- occurrence
- assertion
- assertion_value
- assertion_participant
- assertion_transition
- identity_transition
- identity_transition_member
- resource
- resource_version
- resource_locator
- provenance_link
- record_classification

### `kc_control`

- operation
- deletion_case
- deletion_target

### `kc_derived`

- generation
- generation_source
- current_assertion
- current_identity_member
- current_classification

Do not create embedding/vector tables in migration 1.

---

# Minimal core-test semantic profile

The test profile should be tiny and deliberately cross-domain-neutral.

Entity kinds:

- person
- organization
- device
- project

Occurrence kinds:

- user_statement
- observation
- correction
- identity_resolution
- resource_ingestion

Predicates:

- has_name
- prefers
- works_for
- located_in
- has_state
- supports_claim

Participant role:

- recipient/test-extra-role only if the n-ary validation test needs it.

This profile is test infrastructure, not the eventual Vera/ACL vocabulary.

---

# Minimal API surface for the slice

Exact HTTP route names may change, but the semantic operations must exist.

## Health/service

```text
GET /health
GET /v1/status
```

## Entity

```text
POST /v1/entities
GET  /v1/entities/{ref}
```

## Assertion

```text
POST /v1/assertions
GET  /v1/assertions/{ref}
POST /v1/assertions/{ref}/correct
POST /v1/transitions/{ref}/reverse
```

## Knowledge retrieval

```text
GET /v1/knowledge/current
GET /v1/knowledge/history
GET /v1/knowledge/belief
```

Requests carry structured subject/predicate/time parameters rather than natural-language SQL-like strings.

## Resources/provenance

```text
POST /v1/resources/ingest
GET  /v1/assertions/{ref}/explain
GET  /v1/resources/{ref}/impact
```

## Identity

```text
POST /v1/identity/resolve
POST /v1/identity/transitions/{ref}/reverse
```

## Maintenance/test-only administrative surface

Projection rebuild and deletion reconciliation operations should be internal/admin-scoped and are not normal Vera endpoints.

---

# Kernel acceptance gates

The slice does not advance until all gates pass.

## Gate 1 — typed scalar assertion

Create a person/entity and `has_name = "Robert Smith"` assertion.

Verify:

- ref registry integrity;
- typed value integrity;
- exact predicate/profile revision pin;
- current projection selection.

## Gate 2 — reference-valued relationship

Record `Robert works_for Acme` using a reference-valued assertion.

Verify foreign-key integrity and direct relationship retrieval.

## Gate 3 — correction without overwrite

Append correction `Robert works_for BetaCorp` superseding the earlier assertion.

Verify old assertion remains byte-for-byte/semantically intact and historically queryable.

## Gate 4 — explicit reversal/undo

Reverse the mistaken correction.

Verify current state returns to Acme while history retains Acme -> BetaCorp -> reversal.

## Gate 5 — world time versus knowledge time

Record a late correction whose world-valid date precedes its record date.

Verify:

- current historical reconstruction reflects corrected world history;
- historical-belief query before correction still returns the older belief.

## Gate 6 — conflict preservation

Insert two sourced conflicting assertions without lifecycle invalidation.

Verify both can remain current/conflicting and retrieval does not silently pick one as truth.

## Gate 7 — exact resource-version provenance

Ingest a small text artifact, then change the mutable source/path and ingest a new exact version.

Verify the assertion provenance points to the exact bytes/version consumed, not merely the path.

## Gate 8 — backward explanation / forward impact

From an assertion, trace to evidence/resource version.

From that resource version, find dependent assertion/derived items.

## Gate 9 — current projection destruction/rebuild

Delete/drop the current assertion projection contents.

Rebuild from canonical records and verify identical semantic current results.

## Gate 10 — stale writer protection

Two clients read the same revision. First correction commits. Second correction with stale expected revision must fail with conflict and append no unintended canonical transition.

## Gate 11 — idempotent retry

Submit the same semantic write with the same operation ID twice.

Verify one canonical mutation and repeatable settled result.

Reuse the same operation ID with a different payload and verify rejection.

## Gate 12 — reversible identity merge

Create two same-name people, merge them through an identity transition, verify assertions were not physically rewritten, reverse the merge, and recover the original separate identities.

## Gate 13 — replacement is not equivalence

Create two device entities with a `replace` transition and verify queries never treat them as the same historical entity.

## Gate 14 — restriction fence

Fence an assertion/resource target through a deletion/restriction case.

Verify it disappears from current/retrieval projection before physical payload cleanup.

## Gate 15 — minimal erasure tombstone

Erase specialized payload in a controlled test and retain only the permitted opaque reference/control state.

Verify substantive content is no longer retrievable.

## Gate 16 — anti-resurrection restore simulation

Restore a fixture/snapshot that predates the restriction, then apply a newer deletion-control ledger before enabling queries.

Verify deleted/restricted content never becomes serving state.

A real production backup engine is not required for this gate; the semantic restore sequence is.

## Gate 17 — semantic profile immutability

Create assertion under profile revision 1. Activate revision 2. Verify the old assertion still resolves under revision 1 semantics.

A material predicate meaning change must use a new semantic identity/migration path.

## Gate 18 — derived generation staleness/fencing

Create a derived generation, change a source/profile revision, mark old generation stale, build new generation, and verify an older finishing job cannot replace the newer settled generation.

## Gate 19 — service-only client path

Run the acceptance cases through FastAPI/test client or real loopback HTTP.

The simulated Vera/ACL client must possess no PostgreSQL connection string or database credentials.

---

# Stop boundary after the kernel

If all gates pass:

1. freeze a **Knowledge Core Kernel checkpoint** commit;
2. update architecture/current-state docs;
3. do not immediately add Vera/ACL domain features;
4. select the next bounded slice separately—likely retrieval/full-text + first real ACL knowledge profile, or Authority-service implementation depending project priority.

If any gate fails because the physical model cannot represent the behavior cleanly, fix the architecture/schema before expanding.

---

# Build-order recommendation

Within the kernel slice:

```text
1. package/config/test harness
2. PostgreSQL container/local test fixture + migrations
3. revision/ref/profile foundations
4. entity + assertion typed values
5. current projection + rebuild
6. lifecycle correction/reversal + bitemporal queries
7. operation/idempotency + stale preconditions
8. resource/artifact ingest + provenance
9. identity transitions
10. deletion/restriction semantic fence
11. FastAPI semantic routes
12. full acceptance replay
13. checkpoint and stop
```

Do not build embeddings or Vera integration while a lower numbered gate is failing.

---

# Result

The first implementation is deliberately a **small systems kernel**, not an assistant.

If it passes, the project will have proven that the storage/API foundation can safely support later Vera and ACL work before either system depends on it.
