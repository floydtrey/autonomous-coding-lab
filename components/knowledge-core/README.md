# Knowledge Core

This component is the bounded Knowledge Core Kernel implementation.

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
