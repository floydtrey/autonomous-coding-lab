# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

## Current implementation state

**Branch:** `architecture/knowledge-core`  
**Task:** Knowledge Core Kernel Task 1 — foundation + typed assertion + correction/undo  
**Starting architecture checkpoint:** `dfdaaa45887cb882a05c929a3166981cc0528595`  
**Task 1 implementation commit:** `9bc2bdcad5796a3ff816e5c87afb12a170e74ad3`  
**Status:** Task 1 implemented and focused validation passed; Task 2 not started

This section is the durable implementation-progress checkpoint for the component. The
architecture documents under `docs/architecture/knowledge-core/` remain the design
baseline; later work must still be separately bounded by the user and
`EXECUTION_GOVERNANCE.md`.

## Current implemented boundary

Kernel Task 1 implements only:

- component/package and database foundation;
- canonical revision and universal reference records;
- minimal semantic profile/kind/predicate foundations;
- entities and typed scalar/reference assertions;
- append-only assertion correction;
- explicit correction reversal/undo.

Task 1 deliberately does **not** implement current projections, bitemporal queries,
idempotency/stale writers, resources/provenance, identity resolution, deletion,
FastAPI routes, Authority, embeddings, Vera, or ACL integration.

The production database target is PostgreSQL. Unit tests use SQLite with SQLAlchemy
schema translation so Task 1 semantics can be tested without claiming PostgreSQL
integration proof. PostgreSQL integration remains a separate validation step.

## Task 1 validation checkpoint

Validation performed on the Task 1 implementation before the checkpoint write:

- focused Task 1 test suite: **4 passed**;
- Python compile check: passed;
- Alembic PostgreSQL offline migration render: passed.

A live PostgreSQL server was not available in the execution environment, so Task 1
does **not** claim that the migration has been applied against a running PostgreSQL
instance. That integration validation belongs before relying on the database fixture
in a later bounded task.

The focused tests prove the current Task 1 behaviors:

1. scalar `has_name = "Robert Smith"` is stored as one typed text value and pins the
   exact predicate/profile revision;
2. `works_for` requires a real reference-valued target and rejects scalar or unknown
   references;
3. correction appends a replacement assertion and transition without overwriting the
   original assertion;
4. reversal appends a `restores` transition, retains both assertions and both
   transitions, and rejects a second reversal of the same correction.

## Stop point

Task 1 is the current stop point. No Task 2 implementation has been started.

The next separately authorized task is:

> **Knowledge Core Kernel Task 2: bitemporal history + current projection.**

Do not begin it implicitly while validating or polishing Task 1.

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
