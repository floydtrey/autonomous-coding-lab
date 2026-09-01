# Project Audit and Work Plan

**Authority:** Active trusted project document

**Audit date:** 2026-08-31

**Scope:** Autonomous Coding Lab consolidation, worker execution readiness, and Worker Lab GUI delivery

**Current execution authority:** Disabled

## Purpose

This document records the evidence-backed state of Autonomous Coding Lab and the accepted order of work toward two outcomes:

1. Run bounded workers through the consolidated Worker Lab and framework.
2. Deliver a functional local Worker Lab GUI.

This work plan governs sequencing and completion gates. It does not itself authorize worker/model execution, external-repository access, publication, merging, or destructive cleanup. Each consequential operation still requires its normal explicit authority.

## Executive assessment

Phase 1 produced an accepted, remotely recoverable consolidated checkpoint. The repository is not yet a runnable integrated product because real execution has not been authorized or proven.

- Worker Lab has strong authority, record, lifecycle, storage, workspace, evidence, and recovery foundations.
- The framework has strong security, Codex runtime, code-task, validation, candidate, and handoff foundations.
- Local Model Bench is functional advisory infrastructure and is not a runtime dependency.
- Installation identity v2 is strict, bilateral, and enforced while execution remains disabled.
- A guarded synthetic read-only execution path is nearly complete but has not been run after consolidation.
- Workspace-write coding-worker execution exists in the framework but is not connected to Worker Lab.
- No functional Worker Lab GUI or shared application-service interface exists.
- The next gate is one explicitly authorized, disposable read-only proof after its non-executing operator controls are complete.

The shortest safe path is:

```text
stabilize merger identity
        -> prove one real read-only run
        -> add a shared application service
        -> connect workspace-write coding workers
        -> build the GUI against the stable service
        -> add local planning as an advisory proposal path
```

## Current plan status

- Repository: `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`
- Branch: `main`
- Last accepted Phase 1 commit: `5f6c41da132daa12f0bb8c4be054112d77ef7e54`
- Remote relationship at acceptance: local `main` and `origin/main` matched with zero divergence
- Working tree at acceptance: clean
- Installation manifest: committed and independently enforced by Worker Lab and the framework adapter
- Worker execution policy: `DISABLED`
- Phase 1: complete
- Phase 2: next; real execution not yet authorized

Commit/push authority is separate from worker/model execution authority.

## Completed foundations

### Consolidation

- Framework, Worker Lab, and Local Model Bench histories and selected component trees are present.
- The framework monorepo prefix defect was repaired and validated before the current working-tree changes.
- Worker Lab standalone parity was repaired without weakening its production runtime-identity requirement.
- Deterministic migration and integration inventories exist under `migration/inventory/`.
- Obsolete standalone and merger documentation is preserved byte-for-byte under `docs/legacy/`.
- The active documentation set now describes the consolidated system rather than the former standalone repositories.

### Worker Lab

Implemented foundations include:

- strict canonical schemas and validation;
- protected policies, roles, and test catalogs;
- attempt and invocation lifecycle records;
- atomic storage and stale-write rejection;
- isolated workspace preparation, verification, disposal, and interruption recovery;
- process custody and absence verification;
- evidence identity and content verification;
- durable backup, verification, and restore;
- read-only result acceptance and content-addressed proposal retention.

### Autonomous Worker Framework

Implemented foundations include:

- ChatGPT-managed Codex authentication;
- forbidden API-key rejection;
- GitHub credential-like environment stripping;
- explicit `read-only` and `workspace-write` sandbox modes;
- bounded subprocess execution and output capture;
- target-repository, HEAD, path, diff, and cleanliness enforcement;
- context profiles and deterministic task contracts;
- trusted quick/full validation;
- general workspace-write code tasks;
- candidate publication and repository-handoff primitives;
- a strict Worker Lab adapter for read-only proposals.

### Local Model Bench

Implemented foundations include:

- Ollama, managed llama.cpp/GGUF, and OpenAI-compatible providers;
- deterministic model-first and case ordering;
- JSON and Markdown suites;
- isolated and explicitly preserved context;
- per-case persistence, checkpointing, resumability, and error capture;
- unattended Windows launch and status monitoring;
- response, model, timing, token, and throughput metadata where available;
- deterministic evaluation reports and reviewable result structures.

## Phase 1 validation evidence

Phase 1 validation did not run Codex workers or local models.

| Area | Current audit result | Interpretation |
|---|---:|---|
| Root inventory tools | 9 passed | Root inspection utilities are healthy |
| Framework compile gate | Passed | Imported framework sources compile |
| Framework suite | 208 passed | Identity v2 and disabled-policy enforcement are accepted |
| Worker Lab suite | 330 passed, 7 expected skips | Skips are Windows symlink-capability cases |
| Local Model Bench | 13 passed | CRLF Markdown parsing is repaired and covered |
| Active documentation checks | 5 passed | Active links and documentation contract are healthy |

The Worker Lab suite ran from a valid short disposable path outside every Git repository. The installation consumers agreed on complete runtime-closure digests and rejected disabled execution and identity substitution.

## Remaining blocking problems

### P1 — No general operator execution path

`worker_lab.synthetic_read_only.run()` contains a nearly complete real read-only flow, but it:

- has no supported CLI or root launcher;
- creates one hardcoded synthetic curriculum and exercise;
- treats entry into the function as authority and records a fixed controller name;
- does not consume the accepted disabled activation policy;
- has not been proven after the merger identity adaptation.

### P1 — Workspace-write worker bridge missing

Worker Lab recognizes `workspace-write-code-task`, and the framework separately implements bounded workspace-write code tasks. The adapter supports only `execute-read-only` and rejects non-read-only operations. Missing work includes:

- protocol and adapter mode for workspace-write;
- translation from Worker Lab invocation to framework code-task contract;
- write-candidate evidence collection;
- allowed-path, diff, test, and candidate-digest binding;
- interruption/uncertain-result handling through the complete lifecycle.

### P1 — No usable committed curriculum

Protected policy, roles, and test catalogs exist, but no committed active curriculum, real exercise, context manifest, or target configuration exists. The normal CLI therefore cannot create a meaningful project attempt from repository definitions.

### P1 — Operator surface incomplete

The CLI cannot create/list/authorize/reject/dispatch/recover invocations, list results, show a complete attempt timeline, cancel a run, or review a candidate. These actions need a stable application-service layer before the GUI is connected.

### P2 — Worker Lab GUI absent

The Tkinter file under Local Model Bench is a disposable prompt-learning experiment, not a Worker Lab GUI. There is no dashboard, task editor, authorization view, worker status display, candidate review screen, or GUI-to-service connection.

### P2 — Local models are not Worker Lab providers

The installed Qwen, DeepSeek, Phi-4, and Vera models are used only through Local Model Bench. Worker Lab's protected runtime currently names a Codex model. No planner/provider adapter converts local-model output into a validated, human-approved Worker Lab task proposal.

## Connection matrix

| Connection | State | Required work |
|---|---|---|
| Human scope -> planner proposal | Benchmark-only | Add an advisory planner interface later |
| Planner proposal -> authorized Worker Lab task | Missing | Schema validation, ambiguity handling, human approval, record creation |
| Worker Lab read-only invocation -> framework | Partial | Finish identity, expose operator command, run one real proof |
| Worker Lab workspace-write invocation -> framework code task | Missing | Protocol v2 and adapter bridge |
| Framework result -> Worker Lab read-only evidence | Implemented for synthetic path | Re-prove after identity repair |
| Framework result -> write-candidate evidence | Missing | Changed-path/test/candidate collector |
| Candidate -> trusted review | Library primitives only | Application service and operator commands |
| Candidate -> commit/publish/merge | Framework primitives exist | Keep separate and approval-gated; not an initial GUI requirement |
| Worker Lab state -> GUI | Missing | Read/query service and stable DTOs |
| GUI actions -> Worker Lab lifecycle | Missing | Command service with authorization and recovery gates |
| Local Model Bench -> Worker Lab role selection | Manual/advisory | Retain manual review first; automate only after role evidence is accepted |

## Ordered implementation plan

### Phase 1 — Stabilize the merger

**Status:** Complete at `5f6c41da132daa12f0bb8c4be054112d77ef7e54`.

**Objective:** Produce one clean, testable, remotely recoverable post-consolidation checkpoint while execution remains disabled.

Work:

1. Separate the documentation/archive changes from runtime identity changes.
2. Define installation-manifest v2 with separate source and installation identities.
3. Record SHA-256 digests for the Worker Lab production tree and complete framework runtime dependency closure.
4. Pin or explicitly declare the allowed Python and Codex runtime identities.
5. Make Worker Lab and the adapter independently parse the same strict manifest.
6. Make the activation/deferred policy an enforced pre-execution gate or explicitly supersede it with one reviewed equivalent.
7. Replace misleading `*_commit` compatibility fields in a versioned protocol instead of continuing content-as-commit semantics.
8. Add manifest substitution, traversal, missing dependency, stale digest, runtime substitution, and disabled-policy tests.
9. Update existing identity tests to the accepted contract.
10. Fix Local Model Bench CRLF Markdown parsing.
11. Run the root and all three component suites from valid environments.
12. Update `docs/CURRENT_STATE.md`, commit the bounded changes, and push the private remote.

Completion gate:

- clean working tree;
- all root and component tests pass except documented platform capability skips;
- installation manifest and every consumed dependency digest agree;
- both sides reject disabled execution and identity substitution;
- no worker/model execution occurred;
- remote contains the accepted checkpoint.

### Phase 2 — Prove one real read-only worker

**Status:** Next. Non-executing setup is authorized as normal project work; worker/model execution still requires separate explicit authorization.

**Objective:** Execute exactly one disposable, bounded read-only proposal through the consolidated installation.

Work:

1. Add a non-executing `doctor`/preflight operation.
2. Expose a supported synthetic read-only operator command.
3. Require explicit controller identity, run directory, and one-time authorization.
4. Persist the authorization and activation evidence used for the run.
5. Execute one synthetic proposal.
6. Verify process absence, unchanged workspace, exact result identity, retained proposal, attempt state, and cleanup/recovery behavior.
7. Record the run as a bounded proof, not standing authority.

Completion gate:

- one attempt reaches `CANDIDATE` with exact retained evidence;
- the synthetic workspace remains unchanged;
- no external product repository is accessed;
- interruption/recovery behavior is tested;
- execution returns to disabled after the proof if a temporary activation was used.

### Phase 3 — Create the application service

**Objective:** Give CLI and GUI one stable, tested interface to Worker Lab behavior.

Required service operations:

- system health and installation status;
- list/show curricula, exercises, roles, policies, and tests;
- list/show attempts, invocations, results, failures, and evidence;
- create and prepare attempts;
- create, authorize, reject, and dispatch invocations;
- cancel, recover, abort, and clean up;
- review candidate identity, changed paths, tests, and evidence;
- backup and restore durable state.

The service owns orchestration. The GUI must not write storage records directly or reproduce policy decisions.

Completion gate:

- CLI can exercise every service operation without private-module calls;
- list/status operations are non-mutating;
- authorization and recovery remain fail-closed;
- service tests cover legal and prohibited lifecycle paths.

### Phase 4 — Connect the workspace-write coding worker

**Objective:** Carry one bounded coding task from authorized Worker Lab attempt to reviewed candidate in a disposable repository.

Work:

1. Add a versioned workspace-write adapter operation.
2. Reuse the existing framework code-task and Codex runtime instead of duplicating them.
3. Bind objective, readable paths, writable paths, acceptance criteria, test plan, target commit, runtime, and authorization.
4. Execute in the prepared isolated workspace.
5. Verify unchanged HEAD, exact changed paths, clean diff, required tests, process custody, and candidate content digest.
6. Store the result and transition the attempt to `CANDIDATE`.
7. Add abort and uncertain-outcome recovery.

Initial exclusion:

- no automatic commit, push, pull request, merge, or product-repository access.

Completion gate:

- one disposable coding task reaches `CANDIDATE`;
- only authorized files changed;
- all sealed validation passes;
- a human can inspect and reject the candidate without publication;
- interruption cannot fabricate success.

### Phase 5 — Build the Worker Lab GUI MVP

**Objective:** Provide a local Windows desktop interface over the accepted application service.

Recommended first implementation: standard-library Tkinter, keeping installation simple while the workflow stabilizes.

Initial views:

1. System health and execution state.
2. Curricula, roles, and worker definitions.
3. Task/exercise creation or import.
4. Attempt queue and lifecycle timeline.
5. Invocation preparation and authorization.
6. Running-job status/progress bar and bounded log summary.
7. Candidate changed paths, tests, evidence, and failure boundary.
8. Accept/reject/abort/cleanup actions.
9. Backup and recovery status.
10. Separate advisory benchmark/model evidence view.

GUI rules:

- call only the application service;
- run long work in a background process;
- poll durable status rather than treating console output as truth;
- never hide authorization, scope, or failure boundaries;
- never enable publication or merge merely because a candidate passed tests;
- remain usable when model providers are offline.

Completion gate:

- the GUI can complete the same disposable coding workflow as the CLI;
- closing/reopening the GUI reconstructs state from durable records;
- a running or interrupted job is shown accurately;
- every consequential action displays its target and requires explicit confirmation;
- GUI and CLI produce the same service-layer records.

### Phase 6 — Add the local planner proposal path

**Objective:** Let a selected local model propose plans/tasks without granting it task authority.

Work:

1. Define a planner provider interface separate from Local Model Bench's benchmark runner.
2. Submit a bounded scope and repository context.
3. Require a strict plan/task schema with requirement traceability, dependencies, ambiguity, acceptance criteria, and tests.
4. Reject invalid, incomplete, or over-scoped proposals.
5. Present the proposal in the GUI for human editing and approval.
6. Convert only the approved form into Worker Lab records.
7. Keep coding and verification as separate roles.

Completion gate:

- planner output cannot execute directly;
- unresolved product decisions produce a blocked proposal;
- approved requirements are fully traced into tasks and tests;
- model identity and prompt/config identity are retained with the proposal;
- semantic role fitness is based on reviewed benchmark evidence.

## Immediate work packet

The next implementation request should be:

> Implement Phase 2's non-executing readiness path while execution remains disabled. Add a supported doctor/preflight operation and synthetic read-only operator command, require explicit controller identity, run directory, and one-time authorization, persist the authorization and activation evidence, add interruption/recovery tests, and stop before launching a worker or model unless that one bounded proof is separately and explicitly authorized.

## Change-control rules for this plan

- Update phase status only after its completion gate is satisfied.
- Do not add intermediate milestones merely to restate this plan.
- Do not restart source recovery or import work unless imported history or component paths change.
- Record newly discovered work under the phase whose completion gate it blocks.
- Do not silently expand an implementation phase into GUI, planner, publishing, or product-repository work.
- Keep `docs/CURRENT_STATE.md` factual and short; this file owns the ordered roadmap.
- If implementation evidence contradicts this plan, stop, record the evidence, and revise the plan through trusted review.
