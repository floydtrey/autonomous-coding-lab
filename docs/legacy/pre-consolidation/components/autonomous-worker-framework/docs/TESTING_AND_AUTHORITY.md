# Testing and Authority

**Status:** Approved testing and authority policy
**Scope:** Project-agnostic Worker Lab and worker-framework operation

## Programming authority

The trusted programmer/controller AI has authority to:

- make implementation and architecture decisions inside the approved project direction;
- define and revise task scope;
- accept or reject code;
- determine whether evidence is technically sufficient;
- evaluate worker performance and improvement needs;
- classify failures and require corrective controls;
- select proportionate tests;
- maintain the framework, Worker Lab, evaluator, and active documentation;
- defer improvements that do not advance the active phase.

This authority remains limited by current user direction, system/platform restrictions, external authorization boundaries, destructive-action safety, and explicitly reserved product/business decisions.

Different AI instances and roles may receive different permissions. No authority is inferred merely because an actor is an AI.

## Role authority

| Role | May | May not |
|---|---|---|
| Product owner | Set goals, priorities, acceptable business risk, and material product direction | Be required to personally audit unfamiliar code as the only correctness control |
| Trusted programmer/controller | Design, implement, review, test, accept/reject code, evaluate workers, publish exact approved candidates | Silently change product intent, ignore platform limits, or grant unrestricted worker authority |
| Lab operator | Create authorized curricula/attempts, run evaluation, retain evidence, close/discard attempts | Change protected expectations during an attempt |
| Planner worker | Inspect allowed context and propose scope/tests/risks | Authorize implementation or writable scope |
| Coding worker | Modify exact task paths and add candidate tests | Modify its evaluator, commit/publish, grade itself, or expand scope |
| Verifier | Evaluate exact candidate and report evidence | Repair, change expectations, accept/merge, or grant graduation |
| Publisher | Mechanically package an already accepted candidate | Create, judge, approve, or merge code |

## Stable numbered test catalog

Tests and test groups receive permanent IDs such as `T001`. IDs are never reused or renumbered. Retired tests remain recorded as retired so historical evidence stays interpretable.

Each catalog entry contains:

- stable ID and version;
- name and purpose;
- exact command or evaluator callable;
- owning protected component;
- change selectors: paths, file types, capabilities, and risk flags;
- prerequisites;
- estimated cost class: millisecond, second, or minute;
- environment requirements;
- whether it is mandatory, conditional, milestone-only, or retired;
- evidence fields produced;
- replacement ID when superseded.

Example initial meanings:

| ID | Purpose | Typical selection |
|---|---|---|
| `T001` | Repository identity and clean-start check | Every mutable attempt |
| `T002` | Exact changed-path and protected-path boundary | Every candidate |
| `T003` | Diff/whitespace/integrity check | Every candidate |
| `T004` | Python changed-file compile | Changed Python files |
| `T005` | JSON schema validation | JSON/schema/fixture changes |
| `T006` | Canonical JSON and digest regression | Canonicalization or record changes |
| `T007` | Lifecycle transition tests | Attempt/lifecycle changes |
| `T008` | Path traversal and containment tests | Storage/path/workspace changes |
| `T009` | Atomic-write and corruption tests | Storage changes |
| `T010` | Backup/restore verification | Backup, evidence, or milestone changes |
| `T011` | Directly affected unit-test mapping | Source/module changes |
| `T012` | CLI contract tests | CLI changes |
| `T013` | CSS/static presentation checks | CSS or presentation changes |
| `T014` | Browser/accessibility focused checks | UI behavior changes |
| `T015` | Protected security regression profile | Security boundary changes or risk escalation |
| `T016` | Evidence substitution/tamper checks | Evidence/evaluator changes |
| `T017` | Failure and cleanup behavior | Attempt runner/workspace changes |
| `T018` | Dependency/runtime compatibility | Dependency or runtime changes |
| `T019` | Focused integration for affected components | Multi-module contract changes |
| `T020` | Full project suite | Major update or selected candidate gate |
| `T021` | Backup and rollback drill | Named milestone |
| `T022` | Exact merge/integration candidate verification | Published project candidate |

These are initial catalog semantics, not commands. Worker Lab Phase 1 will implement the versioned catalog and project-specific command bindings.

## Test profiles

A profile is a named, versioned set of test IDs selected for a change class.

Examples:

```text
CSS_CHANGE = T001,T002,T003,T013,T014
JSON_RECORD_CHANGE = T001,T002,T003,T005,T006,T011
STORAGE_CHANGE = T001,T002,T003,T004,T006,T008,T009,T011,T019
PR_CANDIDATE = T001,T002,T003,T005,T006,T011,T015,T019,T022
MILESTONE = all active applicable tests + T020,T021
```

Profiles are project-specific bindings built from shared semantic IDs. A CSS-only project does not inherit irrelevant Python tests, and a Python CLI project does not run browser checks.

## Selection algorithm

1. Inspect exact changed paths, file types, task capabilities, protected boundaries, and risk flags.
2. Select every matching profile.
3. Take the union of their test IDs; never run duplicates.
4. Add always-required identity, scope, and diff checks for mutable candidates.
5. Resolve prerequisites.
6. Sort by cheapest/highest-signal checks first so failures stop early.
7. Produce and retain the numbered execution plan before running tests.
8. Stop at the first failed required boundary unless the test policy explicitly requires collecting independent diagnostics.
9. If a changed path or capability has no trusted mapping, fail selection closed or escalate to the full applicable suite.

The selector is protected authority. A coding worker may propose mappings but cannot change selection for its current attempt.

## Efficient cadence

### Inner loop

Run only millisecond/second tests directly affected by the current edit. Do not invoke a broad `quick` label when more precise numbered tests exist.

### Logical task boundary

Run identity, scope, diff integrity, focused behavior, affected contracts, and relevant security tests. Do not run unrelated components.

### Candidate acceptance

Run the full applicable project suite once against the exact candidate or exact merge candidate when policy/risk requires it. Ordinary low-risk tasks do not require a redundant local full run immediately before the protected verifier runs the same suite.

### Post-integration

Run protected integration CI on the resulting project state. This is allowed repetition because the integrated state has a new identity and may include concurrent/base changes.

### Milestone

Run the complete active catalog, backup verification, rollback drill, and end-to-end lifecycle tests before a named version or authority expansion.

## Evidence reuse

Test evidence may be reused only when all identity inputs match exactly:

- candidate tree/content digest;
- base commit or integration base;
- test catalog and selected test versions;
- evaluator and protected-test identity;
- runtime/operating-system/environment fingerprint;
- dependency lock/versions;
- relevant configuration;
- sandbox and authority profile.

Reused evidence must say it was reused and name the originating run. A mismatch invalidates reuse for affected tests. Time alone does not invalidate deterministic evidence, but external-service or time-sensitive tests may define an explicit freshness limit.

## Test ownership

- Trusted controller owns protected framework, evaluator, security, selection, and graduation tests.
- Curriculum authors define visible acceptance contracts under controller review.
- Coding workers may add candidate regression tests inside writable scope.
- Worker-authored tests are evidence of understanding, not independent proof.
- Protected tests may remain hidden but may only exercise published contract consequences, not surprise requirements.
- Verifiers run tests but cannot rewrite them for the candidate being judged.

## Acceptance and rejection

The trusted programmer/controller accepts or rejects code based on:

- task and repository identity;
- scope compliance;
- relevant numbered test evidence;
- actual diff review;
- security and failure behavior;
- architecture proportionality;
- unresolved risk;
- whether the change advances the active phase.

A green suite is necessary when required but does not compel acceptance. Code may be rejected for unsafe design, hidden scope, unjustified complexity, weak tests, or phase drift.

## Worker evaluation

Workers are evaluated across correctness, security, stability, modularity, expansion readiness, efficiency, explainability, and authority discipline. The controller determines what improved performance requires.

Do not optimize for perfection without an exit condition. Record improvement opportunities, but implement them now only when they block functional completion, create material risk, or satisfy an active phase criterion.

## Current-phase drift control

- Every task names the active phase and criterion it advances.
- Ideas outside the phase go to a parking lot with rationale and possible trigger.
- The trusted programmer/controller may defer technically valuable work to preserve focus.
- Security defects and blockers may interrupt the phase; ordinary polish may not.
- A phase ends when its written acceptance gate passes, not when no further improvements can be imagined.
