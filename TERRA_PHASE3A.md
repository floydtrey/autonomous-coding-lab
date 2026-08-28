# Terra Phase 3A Handoff — Framework Interface Specification

## Assignment

Design the smallest safe interface between Worker Lab and the existing Autonomous Worker Framework.
This batch is specification-only. It must not implement, invoke, simulate, or authorize worker
execution.

The result will be reviewed as a security and authority decision before any production code is
allowed. Prefer a functional, narrow first integration over a generalized orchestration system.

## Starting identity

- Worker Lab repository: `C:\Users\MineTrackerWorker\repos\worker-lab`
- Required branch: `phase3/framework-interface-spec-v1`
- Required base milestone commit: `bcfb1562c3f274c0256ed4105d5f443ab0749ace`
- Required starting checkpoint: the branch HEAD containing this tracked handoff, with the base
  milestone in its ancestry
- Trusted milestone: `v0.2.0-phase2`
- Framework repository, read-only reference:
  `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`
- Framework foundation tag: `v0.1.0-foundation`
- Required framework authority checkpoint: `135373d24837f5d5b0da0650c9c00fc086fcb991`
  on clean local `main`

Before writing, verify both repository identities and statuses with non-mutating Git commands. Confirm
this file exists in `HEAD`; that commit is the approved starting checkpoint. Stop if Worker Lab is not
on the required branch, the base milestone is not an ancestor, or tracked changes already exist. The
following Worker Lab files are pre-existing user-owned untracked material and must remain untouched:

- `Worker-Lab_8_28_26.zip`
- `docs/8_27_26_ChatGPT_History`

Require the framework working tree to be clean on local `main` at the authority checkpoint above and
record its full HEAD and foundation-tag ancestry. That checkpoint refreshes the active documents to
distinguish proven framework capability from still-disabled Worker Lab invocation. Stop on any later
tracked change or identity difference rather than incorporating it into this design implicitly.

## Authority

You may:

- read the minimum routed Worker Lab and framework documents and source contracts listed below;
- create the three exact Worker Lab documents named under Deliverables;
- update the Phase 3 candidate status in `docs/CURRENT_STATE.md` only if necessary for accuracy;
- make bounded design choices and explicitly identify choices reserved for the trusted review.

You may not:

- modify any file in the Autonomous Worker Framework repository;
- modify Worker Lab production Python, tests, schemas, curricula, policies, roles, catalogs, or Phase
  1/2 contracts;
- invoke Codex, a worker, the framework runtime, or a model subprocess;
- create or transition a real Worker Lab attempt;
- access Mine Tracker or any other product repository;
- access a remote, GitHub, the network, credentials, API keys, user configuration, ZIP files, chat
  exports, backups, or historical reports;
- commit, push, merge, tag, publish, delete, restore, reset, clean, stash, or overwrite files;
- broaden Phase 3 into scheduling, concurrent workers, repair loops, evaluators, publishers,
  dashboards, real curricula, or graduation.

## Minimum reading

Read each file once unless its bytes change or a discovered conflict requires a targeted reread.

Worker Lab:

1. `docs/START_HERE.md`
2. Phase 3 boundary and lifecycle facts in `docs/CURRENT_STATE.md`
3. lifecycle and workspace contracts in `docs/PHASE2_SPEC.md`
4. authority roles and numbered test meanings in `docs/POLICY_MODEL.md` and
   `docs/TEST_CATALOG.md`
5. directly relevant public models in `worker_lab/models.py`, `worker_lab/lifecycle.py`,
   `worker_lab/workspace.py`, and `worker_lab/test_catalog.py`

Framework, read-only:

1. `AGENTS.md`, `docs/START_HERE.md`, and current limitations in `docs/CURRENT_STATE.md`
2. relevant boundaries in `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`,
   `docs/WORKER_LAB_DESIGN.md`, and `docs/TESTING_AND_AUTHORITY.md`
3. public contracts in `tools/codex_runtime.py`, `tools/context_probe.py`, `tools/code_task.py`,
   `tools/task_contract.py`, and `tools/worker_result.py`

Do not read every test or implementation file. Inspect a directly related test only when the source
contract is ambiguous, and record why it was needed.

## Required design outcome

Create a versioned Phase 3 specification that answers the following precisely.

### 1. Ownership and trust boundary

Define which repository owns every decision and record:

- Worker Lab owns exercise, attempt, authority, context, test-plan, lifecycle, evidence, and failure
  records.
- The framework owns ChatGPT-managed Codex authentication, API-key rejection, GitHub credential
  stripping, audited runtime configuration, sandbox enforcement, timeouts, repository boundaries,
  and worker subprocess execution.
- The worker owns no authority, cannot alter its contract/evaluator, and cannot commit, publish,
  approve, merge, or expand scope.
- The trusted controller is the only actor allowed to authorize invocation and accept/reject results.

Do not duplicate framework security logic inside Worker Lab or create a second permission service.

### 2. Integration mechanism

Compare only the smallest credible local mechanisms supported by the current code, select one for
the first implementation batch, and explain why. The contract must keep the repositories separate,
make version/identity drift detectable, and return structured data rather than trusting prose.

Do not design a network service, plugin system, message queue, daemon, scheduler, or generalized RPC
layer. If a thin adapter is required, specify its owner, exact public entry point, inputs, outputs, and
failure behavior without implementing it.

### 3. Versioned invocation envelope

Define the exact required identity fields for a future `worker-lab-framework-invocation:v1`-style
record. At minimum bind:

- attempt, exercise, policy, role, context, task, test-catalog, and test-plan identities;
- exact Worker Lab and framework contract/version identities;
- prepared workspace receipt identity, canonical workspace root/path digests, and starting commit;
- exact operation (`read-only-proposal` or `workspace-write-code-task`);
- sandbox, model, reasoning effort, timeout, and allowed/writable paths;
- prompt or instruction digest without storing credentials;
- creation time and trusted-controller authorization identity.

Decide which fields are persisted by Worker Lab, passed to the framework, recomputed independently,
or returned as evidence. Unknown fields, missing identities, mismatches, and unsupported versions must
fail closed.

### 4. Lifecycle and state custody

Map the existing Worker Lab lifecycle to invocation boundaries. Specify:

- all checks required before `READY -> RUNNING`;
- whether the state transition occurs immediately before or only after framework process creation;
- how an invocation-start receipt prevents an ambiguous restart from silently rerunning work;
- how success can produce `CANDIDATE` only after exact changed-path and candidate identity checks;
- how worker, runtime, timeout, contract, boundary, validation, and interruption failures are retained;
- when `ABORTED`, `FAILED`, or another existing state is appropriate;
- how cleanup occurs without losing the first failed-boundary evidence;
- why Phase 3A authorizes no lifecycle change yet.

No automatic retry or repair loop is allowed in the first integration. A new attempt is required
unless a future approved specification defines a safe, identity-bound retry.

### 5. Two-step rollout

Specify two separately reviewable operations:

1. a read-only proposal against an already verified synthetic workspace; and
2. only after that boundary passes, one workspace-write code task against a fresh synthetic
   workspace with exact writable paths.

The read-only proposal must prove no filesystem, Git HEAD, index, configuration, or receipt mutation.
The code task must preserve detached HEAD, forbid commit/push/GitHub access, enforce exact changed
paths, stop at the first failed required validation, and return a strict result suitable for Worker
Lab evidence parsing.

Neither operation may target Mine Tracker. Use only a project-agnostic synthetic fixture when later
implementation is authorized.

### 6. Result and failure contract

Map current framework result fields to Worker Lab records. Identify fields that are insufficient,
ambiguous, or unsafe to reuse directly. Define stable failure categories and the exact first boundary
recorded for at least:

- identity/version/context mismatch;
- workspace or receipt verification failure;
- forbidden API-key environment or missing ChatGPT-managed authentication;
- forbidden sandbox or credential/environment leakage;
- Codex unavailable, timeout, nonzero exit, or malformed result;
- Git HEAD/config/index/remote/alternate-object mutation;
- unexpected or protected changed paths;
- focused/full validation failure;
- interrupted controller process and uncertain outcome.

Worker stdout/stderr and prose are untrusted evidence inputs. They must never directly authorize a
state transition, test pass, acceptance, or publication.

### 7. Test and evidence plan

Propose permanent test bindings and cost-aware profiles using the existing T001-T022 meanings. Give
exact planned coverage for the interface adapter, read-only proposal, workspace-write task, security
regressions, interruption/restart behavior, and Phase 3 milestone. Separate fast development tests
from the one complete milestone gate. Do not execute tests in this documentation-only batch.

### 8. Implementation batches and completion conditions

Divide later work into small batches, expected roughly as:

- 3B: strict invocation/result schemas and a non-executing adapter seam;
- 3C: read-only proposal execution and non-mutation/restart evidence;
- 3D: one bounded workspace-write task and candidate identity;
- 3E: failure recovery, CLI acceptance, milestone validation, backup/rollback, and documentation.

Adjust these only when the current contracts make a different boundary materially safer. Give each
batch explicit entry conditions, deliverables, tests, prohibited scope, and exit conditions. Define a
numbered Phase 3 completion checklist suitable for trusted approval.

## Decisions reserved for trusted review

Clearly flag, rather than silently settling, any decision that would:

- expand framework or Worker Lab authority;
- change authentication, sandbox, credential, or audited Codex-version policy;
- allow Worker Lab to control raw subprocess options;
- persist prompts or worker output containing potentially sensitive content;
- permit rerunning an uncertain attempt;
- permit commits, remotes, GitHub, publishing, real curricula, or product repositories;
- require a new lifecycle state or change an existing permanent policy/test meaning.

## Deliverables

Create exactly:

1. `docs/PHASE3_SPEC.md` — normative interface, identity, lifecycle, failure, testing, rollout, and
   exclusion contract.
2. `docs/PHASE3_READINESS_REVIEW.md` — numbered completion conditions, unresolved decisions, risks,
   and an explicit recommendation to approve, revise, or reject implementation start.
3. `TERRA_PHASE3A_REPORT.md` — exact starting identities, context read, decisions made, files changed,
   commands run, validation performed, limitations, and final Git status.

You may make a minimal candidate-status update to `docs/CURRENT_STATE.md`. Do not update README,
START_HERE, prior phase documents, or any other file.

## Validation and stopping rules

This is a documentation-only change:

- run `git diff --check` once after the final edit;
- verify the changed-path set is limited to the three deliverables and optional current-state update;
- do not run pytest, compilation, the numbered runtime profiles, a worker, or the framework;
- do not create a backup, bundle, branch, commit, PR, tag, or remote operation.

Stop immediately and report without compensating action if:

- repository identity or tracked cleanliness differs from the required start;
- the framework contracts contradict the fixed authentication/sandbox/credential boundaries;
- a safe interface requires modifying framework code in this batch;
- the design cannot distinguish a never-started invocation from an interrupted/uncertain one;
- the requested result cannot be achieved without expanding authority or scope.

Leave all changes uncommitted for trusted review.
