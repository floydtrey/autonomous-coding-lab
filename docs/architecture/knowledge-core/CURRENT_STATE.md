# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Kernel V1 starting architecture checkpoint:** `dfdaaa45887cb882a05c929a3166981cc0528595`  
**Task 10 checkpoint:** `ea8ff441133329dfc19b631ed0172cdf12561704`  
**Gate 19 validated implementation head:** `2bdbc2a161bd2756fa7139ecefd4ca8b160f148e`  
**Frozen Kernel V1 checkpoint:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**Exact freeze validation:** GitHub Actions run `34350709966` — **47 passed, 2 upstream deprecation warnings**  
**Status:** **Knowledge Core Kernel V1 acceptance gates 1–19 passed. Kernel boundary is frozen pending a separately authorized next slice.**

This file is the branch-specific controlling acceptance record for Knowledge Core. It does not replace the repository-wide `docs/CURRENT_STATE.md`, which records the accepted state of `main` and other ACL work. Documentation-only commits after `9e904f49480055615bb0cf32360dbdc8400e117c` do not reopen or alter the frozen Kernel implementation boundary.

## Accepted Kernel boundary

The V1 Kernel now includes:

- canonical revisions and universal knowledge refs;
- immutable/versioned semantic profiles, kinds, and predicates;
- atomic typed assertions and reference-valued relationships;
- append-only correction/reversal history;
- independent world-valid and knowledge-record time;
- rebuildable current assertion projection with conflict preservation;
- operation IDs, deterministic request digests, idempotent replay, stale-writer protection, and serialized PostgreSQL managed writes;
- exact logical-resource/resource-version identity, immutable SHA-256 artifact storage, locator history, and traversable provenance;
- reversible identity merge/split semantics and replacement-not-equivalence;
- deletion/restriction serving fences, bounded assertion tombstoning, and anti-resurrection reconciliation;
- append-only semantic-profile activation and exact assertion semantic pinning;
- derived-generation lineage plus monotonic out-of-order settlement fencing;
- FastAPI/Pydantic semantic service routes for normal client operations;
- managed exact-resource ingest including explicit successful no-canonical-mutation replay;
- a serving-safe current-identity query required for client-side identity semantics;
- a service-only Gate 19 simulated Vera/ACL client with no database or artifact-store credentials.

## Gate 19 acceptance

Gate 19 uses `tests/test_task11_gate19_service_only.py` and the existing Task 1–10 suites.

The simulated client has only:

- an HTTP/TestClient transport;
- `X-Knowledge-Caller` identification context.

It does not possess or import:

- SQLAlchemy sessions;
- PostgreSQL/database URLs;
- `KNOWLEDGE_CORE_DATABASE_URL`;
- artifact-store objects or artifact paths;
- direct SQL/storage repositories.

The normal client HTTP replay covers the externally observable portions of typed assertions, relationships, correction/reversal, bitemporal reads, conflict preservation, stale writes, idempotent retries, exact resource provenance, identity merge/split/replacement, privacy serving fences, and semantic-profile pinning. Privileged privacy reconciliation, profile administration, and generation settlement remain server/control-plane concerns and are deliberately absent from the Vera/ACL client API.

## Exact repository validation

A branch-local GitHub Actions workflow installs the exact checked-in component on a clean Ubuntu runner using Python 3.12 and executes:

```text
python -m pip install -e ".[test]"
python -m pytest -q
```

The first workflow run exposed an editable-package discovery defect: setuptools attempted to treat both `knowledge_core` and `migrations` as top-level packages. The package configuration was corrected so only `knowledge_core*` is packaged.

The second workflow run installed successfully and executed the suite. It exposed one pre-existing Task 6 portability defect: SQLite replay returned deletion-control timestamps without timezone information, causing the original and replayed idempotent snapshots to differ only by `tzinfo`. Deletion snapshots now normalize persisted timestamps to UTC.

Workflow run `34350296337` validated the Gate 19 implementation head `2bdbc2a161bd2756fa7139ecefd4ca8b160f148e`. After the freeze documentation was committed, workflow run `34350709966` validated the exact frozen Kernel checkpoint `9e904f49480055615bb0cf32360dbdc8400e117c`:

```text
47 passed, 2 warnings
```

The two warnings are upstream TestClient/Starlette deprecation warnings and are not semantic failures.

## Gate disposition

- Gates 1–11: covered by the original foundation/temporal/operation/resource acceptance suites and included in the final exact 47-test replay.
- Gates 12–16: previously accepted by bounded runtime validation and replayed through final checked-in component tests; service-observable identity/privacy behavior is also exercised by Gate 19.
- Gate 17: semantic profile immutability accepted and included in the final suite; Gate 19 verifies old/new assertion revision pinning through the HTTP client while profile activation remains server-side administration.
- Gate 18: derived generation fencing accepted and included in the final suite; Gate 19 verifies that generation administration remains absent from the normal client surface while the server-side fence still rejects an obsolete late finisher.
- Gate 19: **accepted** through FastAPI/TestClient service-only replay and exact repository CI.

## Explicitly unclaimed / remaining integration debt

Kernel acceptance does **not** claim:

- live PostgreSQL application of migrations `0001_task1` through `0008_task9` in this execution environment;
- a real multi-process PostgreSQL generation/write race;
- production authentication, TLS, firewall policy, or the real Authority service;
- production backup/restore orchestration or multi-service privacy reconciliation;
- physical erasure of resource artifact bytes (Task 6 physical erasure remains bounded to standalone assertions);
- generation IDs attached to every historical derived-family row;
- Vera domain features, ACL domain profile, embeddings/vector search, autonomous workers, or action execution.

These are not reasons to reopen the V1 Kernel acceptance gates. They are separately bounded deployment/integration or future-feature slices.

## Recommended next bounded slices

Do not combine these into one task. Select one separately:

1. **Live PostgreSQL integration qualification** — apply migrations `0001_task1` through `0008_task9` to a real PostgreSQL instance, rerun the service acceptance against PostgreSQL, and exercise advisory-lock/stale-write/generation concurrency behavior. This closes the largest remaining gap between the validated semantic Kernel and its intended production datastore.
2. **Retrieval/full-text foundation** — design and validate deterministic lexical retrieval over Knowledge Core before embeddings/vector search. Keep it generic and service-only.
3. **First real ACL semantic profile** — only after the retrieval/storage boundary is satisfactory, define a small versioned ACL vocabulary for projects, tasks, evidence, decisions, dependencies, and outcomes. Do not import Worker Lab execution authority into Knowledge Core.
4. **Authority-service boundary** — implement/validate the external Authority service contract separately if authorization becomes the higher priority. Knowledge Core should consume decisions, not become Authority.
5. **Later Vera profile/integration** — defer until the generic infrastructure and ACL path have proven the Kernel under real use.

## Stop boundary

The V1 Kernel is frozen after Gate 19. Do not immediately add Vera/ACL domain semantics, embeddings, Authority implementation, or production deployment features on this checkpoint.

The next slice must be selected separately and should begin from the frozen Kernel V1 checkpoint plus any subsequent documentation-only reconciliation commits.
