# Worker Lab Phase 1 Specification

**Status:** Approved implementation specification
**Phase:** Headless contracts and local storage
**Purpose:** Define a finishable first coding boundary without dashboard, worker execution, or curriculum expansion.

## Outcome

Phase 1 produces a local Python package and CLI that can define, validate, store, inspect, back up, and restore Worker Lab curricula, exercises, attempts, evidence metadata, and failure records.

It does not run a coding worker yet. Phase 1 establishes the protected records and integrity rules that later execution must consume.

## Repository

- Name: `worker-lab`
- Intended path: `C:\Users\MineTrackerWorker\repos\worker-lab`
- Runtime: Python 3.12
- Initial dependencies: Python standard library plus pytest for development/testing
- Network requirement: none
- Deployment: local-only, single-user
- Data: synthetic curriculum and attempt data only

## Required package boundaries

```text
worker-lab/
  README.md
  AGENTS.md
  docs/
  worker_lab/
    models.py          strict record types and enums
    validation.py      schema and cross-record validation
    canonical.py       deterministic JSON and SHA-256 identities
    storage.py         atomic file storage and corruption detection
    lifecycle.py       legal attempt state transitions
    backup.py          verified backup and restore
    cli.py             headless operator interface
  tests/
  curricula/           Git-tracked definitions
  state/               ignored local operational records
  evidence/            ignored content-addressed retained evidence
  workspace/           ignored disposable attempt checkouts
```

The exact modules may be refined when code demonstrates a better small boundary, but responsibilities must not be collapsed into one general manager module.

## Durable records

### Curriculum

- stable curriculum ID;
- schema version;
- title and purpose;
- capability dimensions;
- prerequisite curriculum IDs;
- ordered exercise IDs;
- active/retired status.

### Exercise

- stable exercise ID and version;
- curriculum ID;
- objective;
- template repository identity;
- exact writable and protected paths;
- visible acceptance criteria;
- selected test-profile IDs;
- prohibited shortcuts;
- expected failure/recovery behavior.

### Attempt

- immutable attempt ID;
- curriculum and exercise identity/version;
- starting commit and context/task digests;
- runtime/model/role identity when execution is later added;
- state and timestamps;
- candidate identity when present;
- evaluator catalog/version;
- cleanup outcome.

### Evidence metadata

- evidence digest;
- evidence type;
- attempt ID;
- producing test ID and catalog version;
- candidate/base/environment identities;
- content path or external evidence reference;
- creation timestamp;
- verification state.

Phase 1 stores metadata and test fixtures; it does not need to retain large binary evidence.

### Failure record

- attempt ID;
- first failed boundary;
- expected and observed behavior;
- classification;
- containment/cleanup outcome;
- proposed control or accepted limitation;
- related failure IDs.

## Attempt lifecycle

Initial legal states:

```text
DRAFT -> READY -> RUNNING -> CANDIDATE -> EVALUATING
EVALUATING -> PASSED | FAILED | NEEDS_REVIEW
PASSED | FAILED | NEEDS_REVIEW -> CLOSED
DRAFT | READY | RUNNING | CANDIDATE | EVALUATING -> ABORTED
```

Rules:

- terminal attempt history is immutable;
- a retry creates a new attempt linked to the prior attempt;
- acceptance, evaluator, start identity, or candidate identity changes require a new attempt;
- illegal transitions fail with structured errors;
- Phase 1 may construct lifecycle fixtures without invoking workers.

## Canonical identity

- JSON uses UTF-8, sorted object keys, deterministic separators, and no non-finite numbers.
- Unknown fields fail closed.
- Record schema versions are explicit.
- Content identities use `sha256:<lowercase hex>`.
- Identity covers all fields that affect interpretation or authority.
- Display formatting is not used for identity.

## Storage

- one durable record per file;
- normalized repository-relative or Lab-relative paths only;
- no path traversal, absolute paths, alternate drive paths, or symlink escape;
- writes use same-directory temporary files, flush, and atomic replacement where supported;
- the prior valid record survives an interrupted or rejected write;
- corrupt or substituted records are reported and never silently repaired;
- readers do not mutate data;
- storage version changes require an explicit migration task in a later phase.

## CLI

Phase 1 commands:

```text
worker-lab validate-definition <path>
worker-lab list-curricula
worker-lab show-curriculum <id>
worker-lab show-exercise <id> --version <version>
worker-lab create-attempt --exercise <id> --version <version>
worker-lab show-attempt <attempt-id>
worker-lab transition-attempt <attempt-id> <state>
worker-lab verify-evidence <digest>
worker-lab backup <destination>
worker-lab verify-backup <path>
worker-lab restore <backup> <empty-destination>
```

Commands return nonzero status and structured plain-language diagnostics on failure. Machine-readable JSON output may be added only if it does not duplicate business logic.

## Protected authority

The trusted programmer/controller owns initial schemas, lifecycle rules, canonical identity, path containment, backup verification, test catalog, evaluator contracts, and graduation rules.

Workers may later implement bounded modules against these contracts, but cannot change the protected expectation judging their current attempt.

## Phase 1 acceptance criteria

Phase 1 is complete only when:

- every record accepts valid fixtures and rejects missing, unknown, malformed, and incompatible fields;
- canonical bytes and digests are deterministic;
- illegal lifecycle transitions fail without mutation;
- path traversal and symlink escape are rejected;
- interrupted-write simulation preserves the prior valid record;
- corrupt and substituted records are detected;
- backup verification detects missing, changed, and extra protected contents;
- restore succeeds only into an empty destination and reproduces verified identities;
- CLI inspection and failure output is usable;
- numbered test selection produces an auditable execution plan;
- a complete backup/restore/rollback drill passes;
- all Phase 1 test profiles and the milestone full suite pass;
- a named local checkpoint and verified Git bundle are created;
- active documentation is updated.

## Explicit exclusions

- invoking Codex or another coding worker;
- GitHub publication;
- dashboard or web server;
- SQLite;
- OCR;
- standalone Vera;
- concurrent attempts;
- automatic repair;
- automatic evaluator/playbook changes;
- production-project data;
- generalized plugin architecture.

## Drift gate

Every Phase 1 coding task must name at least one incomplete acceptance criterion above. Work that does not advance a criterion is deferred to the parking lot unless it fixes a blocking defect or security problem.
