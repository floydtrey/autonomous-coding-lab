# Numbered Test Catalog

**Active binding:** `worker-lab-v2`
**Authority:** Permanent meanings are defined in the Autonomous Worker Framework
`docs/TESTING_AND_AUTHORITY.md`. Worker Lab binds commands and evaluator locators to those meanings;
it never redefines or reuses an ID.

The machine-readable binding is `curricula/catalogs/worker-lab-v2.json`. The immutable Phase 1
binding remains at `curricula/catalogs/worker-lab-v1.json`. Each binding records every active
test's version, purpose, owner, runner, command or evaluator locator, selectors, prerequisites, cost,
environment, evidence fields, and retirement replacement.

Published catalog files are immutable. A command, selector, dependency, profile, or other binding
change requires a new catalog version; attempts retain both the exact version and canonical digest.

## Relevant permanent meanings

| ID | Permanent meaning | Worker Lab binding |
|---|---|---|
| T001 | Repository identity and clean start | Framework evaluator |
| T002 | Exact changed/protected path boundary | Framework evaluator |
| T003 | Diff and repository integrity | Framework evaluator |
| T004 | Python changed-file compile | Python compile command |
| T005 | JSON/schema validation | Protected definition tests |
| T006 | Canonical JSON and digest regression | Canonical/record/catalog tests |
| T007 | Attempt lifecycle transitions | Lifecycle tests |
| T008 | Path traversal and containment | Storage/context path tests |
| T009 | Atomic write and corruption | Storage tests |
| T010 | Backup and restore verification | Backup tests |
| T011 | Directly affected unit tests | Framework-selected project binding |
| T012 | CLI contract | CLI tests |
| T015 | Protected security regression profile | Workspace receipt, containment, and substitution tests |
| T017 | Failure and cleanup behavior | Lifecycle/storage tests |
| T018 | Dependency/runtime compatibility | Supported Python/Git workspace runtime tests |
| T019 | Focused integration | Validation/evidence/CLI tests |
| T020 | Full project suite | Complete pytest suite |
| T021 | Backup and rollback drill | Trusted-controller milestone drill |

Profiles select the union of applicable IDs and add all prerequisites. Plans use prerequisite-first
topological order; among tests currently eligible to run, lower-cost tests run first and permanent ID
breaks ties. Every plan retains the exact catalog version and digest. Execution stops at the first
failed required boundary. Unmapped paths or capabilities fail closed. Retired IDs remain reserved
and name their replacement; they are never renumbered or reassigned.

`WORKSPACE_CHANGE:v1` binds workspace and receipt changes to T001, T002, T003, T004, T006, T007,
T008, T009, T011, T015, T017, T018, and T019. CLI-specific workspace changes also select T012.

## Phase 3 binding

`worker-lab-v3` preserves every `worker-lab-v2` definition and adds bindings for `T016` evidence
substitution/result identity and `T022` exact integration-candidate verification. Its Batch 3B
profiles are `FRAMEWORK_ADAPTER_CHANGE:v1`, `READ_ONLY_INVOCATION:v1`,
`CODE_INVOCATION:v1`, and `PHASE3_MILESTONE:v1`. The latter three contain planned Phase 3C-E
coverage and do not authorize execution or claim it has occurred.
