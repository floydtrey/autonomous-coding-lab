# Knowledge Core

This component is the bounded Knowledge Core Kernel V1 implementation.

## Current state

**Branch:** `architecture/knowledge-core`  
**Task 10 checkpoint:** `ea8ff441133329dfc19b631ed0172cdf12561704`  
**Gate 19 validated implementation head:** `2bdbc2a161bd2756fa7139ecefd4ca8b160f148e`  
**Status:** **Kernel V1 gates 1–19 accepted. The Kernel boundary is frozen pending a separately authorized next slice.**

The controlling acceptance record is `docs/architecture/knowledge-core/CURRENT_STATE.md`. The original plan in `docs/architecture/knowledge-core/IMPLEMENTATION_PLAN_V1.md` is now marked complete.

## Accepted Kernel capabilities

The bounded V1 Kernel includes:

- canonical revisions and universal knowledge refs;
- immutable/versioned semantic profiles, kinds, and predicates;
- typed scalar/reference assertions;
- append-only correction and explicit reversal;
- independent world-valid and knowledge-record time;
- conflict-preserving historical/current retrieval;
- rebuildable current projections;
- operation IDs, deterministic request digests, idempotent replay, stale-write protection, and serialized PostgreSQL managed writes;
- exact resource versions, immutable SHA-256 artifact storage, mutable locator history, and traversable provenance;
- reversible identity merge/split plus replacement-not-equivalence;
- deletion/restriction serving fences, bounded assertion erasure, and anti-resurrection reconciliation;
- append-only semantic-profile activation with assertions pinned to exact semantic revisions;
- derived-generation lineage and monotonic out-of-order settlement fencing;
- a FastAPI/Pydantic semantic service boundary;
- managed resource/provenance HTTP operations, including explicit successful no-canonical-mutation exact re-ingest;
- a serving-safe current-identity read for normal service clients.

## Gate 19 — service-only client acceptance

`tests/test_task11_gate19_service_only.py` defines a simulated Vera/ACL client whose entire capability is:

```text
HTTP/TestClient transport
X-Knowledge-Caller identification context
```

The client possesses no SQLAlchemy session, database URL, PostgreSQL connection string, `KNOWLEDGE_CORE_DATABASE_URL`, artifact-store object, artifact path, or direct storage repository.

Normal client semantics are exercised through FastAPI/TestClient for typed assertions, reference relationships, correction/reversal, bitemporal belief, conflict preservation, stale writes, idempotent retries, exact resource provenance, identity merge/split/replacement, privacy-serving behavior, and semantic-profile pinning.

Privileged privacy reconciliation, profile administration, and derived-generation settlement remain server/control-plane concerns. They are deliberately not normal Vera/ACL endpoints.

### Identity service gap fixed during Gate 19

Gate 19 found that identity transitions were writable over HTTP but current identity resolution was not readable through the service. That would have forced a client acceptance test to reach behind the API to verify merge/split/replacement behavior.

The bounded fix added:

```text
GET /v1/identity/entities/{entity_ref}
```

and made managed merge/replace/reversal rebuild the derived current-identity projection before the operation settles. A normal client can therefore observe identity semantics without SQL/storage access.

## Exact repository validation

A component workflow now runs on the branch with Python 3.12:

```text
python -m pip install -e ".[test]"
python -m pytest -q
```

The integration gate found and fixed two pre-existing defects before acceptance:

1. **Editable-package discovery:** setuptools attempted to package both `knowledge_core` and top-level `migrations`. Package discovery is now explicitly limited to `knowledge_core*`.
2. **Deletion replay timezone normalization:** SQLite persisted timezone-aware deletion-control timestamps but returned naïve values, so an idempotent replay snapshot differed only by `tzinfo`. Deletion snapshots now normalize persisted timestamps to UTC.

GitHub Actions run `34350296337` at `2bdbc2a161bd2756fa7139ecefd4ca8b160f148e` passed the exact checked-in component suite:

```text
47 passed, 2 warnings
```

The two warnings are upstream TestClient/Starlette deprecation warnings and are not semantic failures.

## Gate disposition

- Gates 1–11: accepted and included in the final exact component replay.
- Gates 12–16: accepted; identity/privacy behavior is also exercised through the Gate 19 service-only replay where externally observable.
- Gate 17: accepted; old/new assertion semantic revision pinning is verified while profile activation remains server-side administration.
- Gate 18: accepted; generation administration remains absent from the normal client API and the late-finisher fence remains enforced server-side.
- Gate 19: **accepted through FastAPI/TestClient service-only replay.**

## Explicit limitations / integration debt

Kernel V1 acceptance does **not** claim:

- live PostgreSQL application of migrations `0001_task1` through `0008_task9` in this execution environment;
- a real multi-process PostgreSQL write/generation race;
- production authentication, TLS, firewall policy, or the real Authority service;
- production backup/restore orchestration or multi-service privacy reconciliation;
- physical erasure of resource artifact bytes (bounded physical erasure currently covers standalone assertions);
- generation IDs attached to every historical derived-family row;
- Vera domain features, ACL domain profiles, embeddings/vector search, autonomous workers, or action execution.

Those items require separately bounded future work. They are not reasons to reopen the accepted V1 semantic Kernel gates.

## Stop boundary

**Stop here.** Do not immediately add Vera/ACL semantics, embeddings, Authority implementation, or production deployment features to this checkpoint.

The next project slice must be selected separately. Candidate directions in the architecture plan include retrieval/full-text plus a first real ACL knowledge profile, or Authority-service implementation, depending project priority.

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
