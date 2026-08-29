# Terra Phase 3C Handoff — Contained Framework Adapter Candidate

## Objective

Implement the separately reviewable framework-adapter and Worker Lab client candidate required
before one synthetic read-only proposal. Fix the one-way attempt runtime binding, exact runtime and
repository identity, Windows process-tree custody, bounded output, strict retention, and
restart/absence evidence described in `docs/PHASE3C_SECURITY_DECISIONS.md`.

This is a non-executing implementation batch. Use fake adapters, fake runtime executors, and inert
local child-process fixtures only. Do not invoke Codex, query live Codex authentication, transition a
real attempt to `RUNNING`, or run a synthetic proposal.

## Required trusted checkpoint before Terra starts

The trusted controller must first checkpoint this handoff, the security-decision record, and routing
updates. Terra records that resulting Worker Lab commit as its actual starting identity; do not
pretend the pre-handoff `62aaf13` commit contains these files.

Required repository bases for that trusted checkpoint:

- Worker Lab: `C:\Users\MineTrackerWorker\repos\worker-lab`, `main`, ancestry containing
  `62aaf13`, with only the known user-owned `docs/8_27_26_ChatGPT_History` untracked.
- Framework: `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`, `main`, exact clean
  `135373d24837f5d5b0da0650c9c00fc086fcb991`, with no untracked files.
- Framework foundation tag: `v0.1.0-foundation` remains unchanged.

Stop on a different repository, unexpected branch or ancestry, tracked starting change, unexpected
untracked path, missing handoff/decision record, or conflict with current user authority. Preserve
and do not open the known Worker Lab history export.

## Authority order and minimum reading

Read once, in this order:

1. Worker Lab `AGENTS.md` and `docs/START_HERE.md`.
2. This handoff and `docs/PHASE3C_SECURITY_DECISIONS.md`.
3. Phase 3 portions of `docs/CURRENT_STATE.md`, `docs/PHASE3_SPEC.md`, and
   `docs/PHASE3_READINESS_REVIEW.md`.
4. Directly affected Worker Lab source/tests only: `worker_lab/integration.py`,
   `worker_lab/invocation_store.py`, `worker_lab/framework_adapter.py`,
   `worker_lab/models.py`, `worker_lab/lifecycle.py`, `worker_lab/attempt_store.py`,
   `worker_lab/canonical.py`, `worker_lab/storage.py`, and their focused tests.
5. Framework `AGENTS.md`, `docs/START_HERE.md`, the current limitations in
   `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md`, and active `docs/DECISIONS.md`.
6. Directly affected framework source/tests only: `tools/codex_runtime.py`,
   `tools/context_probe.py`, `tools/code_task.py`, `tools/worker_result.py`, and their focused tests.

Current explicit user/trusted-controller authority and this tracked handoff supersede the stale
framework documentation statement that Phase 3A is the immediate next task, but only for the exact
non-executing changes below. Record the conflict in the report and update framework current-state
documentation accurately. Do not infer broader framework authority.

Do not read history, backups, ZIPs, old reports other than the report created for this exact task,
unrelated branches, remotes, credentials, user configuration, or any product repository.

## Fixed implementation decisions

Implement every D3C decision exactly. In particular:

- entry point: `tools/worker_lab_adapter.py`;
- transport: canonical JSON over stdin/stdout, no shell and no direct cross-repository imports;
- configured Python: exact CPython identity recorded in D3C-02;
- adapter modes in this candidate: deterministic preparation, preflight through injected fakes, and
  read-only execution through injected fakes; reject workspace-write execution;
- runtime profile: exact `terra-medium:v1`, Codex `0.149.1`, Terra medium, 900 seconds, audited
  Windows sandbox, and read-only operation;
- containment: Windows Job Object with a non-inheritable kill-on-close handle and no request before
  successful assignment;
- process identity: custody-record digest with PID plus Windows creation time, never PID alone;
- limits and retention: exact D3C-05 values and fail-closed behavior;
- attempt binding: exactly one null-to-invocation-digest assignment on `READY -> RUNNING`; and
- no change to `worker-lab-v3`, prior catalogs, or `v0.1.0-foundation`.

If an implementation detail would weaken or reinterpret one of these decisions, stop and report it
instead of choosing a substitute.

## Allowed framework changes

Use focused modules and the smallest compatible changes:

- add `tools/worker_lab_adapter.py` for strict preparation/preflight/execution protocol handling;
- add one focused framework module if needed for canonical Worker Lab request/result translation or
  bounded binary stream capture;
- make the minimum compatible change to `tools/codex_runtime.py` needed to reuse existing auth,
  environment, sandbox, command, and timeout controls through an injected execution seam;
- add `tests/test_worker_lab_adapter.py` and narrowly extend `tests/test_codex_runtime.py`;
- use inert fixture child processes to prove bounded capture and structured failure behavior;
- minimally update framework `docs/CURRENT_STATE.md` and `docs/DECISIONS.md` to describe the
  candidate and keep live Worker Lab invocation disabled; and
- create `TERRA_PHASE3C_FRAMEWORK_REPORT.md` in Worker Lab, not an untracked report in the framework.

Do not change consumer profiles, publishing, handoff, merge, repair, Mine Tracker-specific behavior,
existing public contracts, foundation tags, or unrelated runtime paths. Do not add a default
execution mode that can be reached without the strict Worker Lab protocol and fixed profile.

The framework adapter may call existing Codex runtime functions in production code, but every test
and every invocation in this batch must inject a fake before the call boundary. Do not run the
production call path.

## Allowed Worker Lab changes

- strengthen `worker_lab/integration.py` with canonical runtime/process-custody identities and the
  exact field/size invariants needed by the decisions;
- strengthen `worker_lab/invocation_store.py` or add a narrowly scoped custody store under
  `state/process-custody/` with atomic guarded transitions;
- replace the inert command alias in `worker_lab/framework_adapter.py` with trusted configuration,
  exact repository/Python/adapter verification, a fixed command builder, bounded result parsing, and
  an injected process runner;
- add a small Windows Job Object/process runner module if keeping the native API boundary separate
  materially improves reviewability;
- update `worker_lab/lifecycle.py` and `worker_lab/attempt_store.py` only for the exact
  null-to-invocation-digest `READY -> RUNNING` rule;
- add the minimum compatible validation to `worker_lab/models.py` without changing
  `worker-lab-attempt:v2` fields;
- extend `tests/test_integration.py`, `tests/test_invocation_store.py`,
  `tests/test_lifecycle.py`, and `tests/test_attempt_store.py`, plus one focused Windows
  containment test file if needed;
- minimally update `docs/CURRENT_STATE.md` and this task's reports; and
- create `TERRA_PHASE3C_REPORT.md` recording the complete two-repository candidate.

Do not change workspace preparation/disposal semantics, backup scope, CLI, policies, roles,
exercises, evaluators, prior schemas, permanent test meanings, or any published catalog. Do not add a
live CLI execution command in this batch.

## Required behavior and test cases

### Identity and command

Tests must prove that exact clean identities pass and each of these fails before request dispatch:

- wrong Worker Lab or framework commit;
- any tracked framework modification or untracked framework path;
- any Worker Lab change other than the named unopened history exception;
- substituted/reparse framework root, adapter, or Python path;
- adapter working-tree/blob mismatch;
- Python path, version, architecture, or digest mismatch;
- Codex launcher/version/runtime identity mismatch;
- altered executable, mode, protocol, flag, environment, cwd, model, reasoning, timeout, or sandbox;
  and
- exercise-, prompt-, or worker-supplied executable configuration.

The canonical preparation identity and the later fake execution identity must match byte-for-byte.

### Containment and recovery

Windows-focused tests must prove:

- the request runner creates/configures the Job Object before adapter launch;
- no request byte is written until successful job assignment and custody persistence;
- assignment/configuration failure terminates the inert adapter without child creation;
- a normal inert parent/child tree exits with zero active processes;
- timeout, output overflow, and simulated interruption terminate the complete inert tree;
- cleanup is refused until zero active processes is verified;
- PID reuse is rejected through mismatched Windows creation time;
- a live exact controller identity leaves the invocation/workspace untouched on recovery;
- absent-controller recovery succeeds only with complete consistent custody evidence; and
- missing, inaccessible, stale, or contradictory evidence remains uncertain and is never rerun.

Skip only when a specific Windows capability is genuinely unavailable, and record the exact reason.
Do not convert a containment failure into a skip merely to obtain a passing candidate.

### Bounds and retention

Test every limit at `limit`, `limit + 1`, invalid UTF-8, empty input, wrong type, embedded NUL,
absolute Windows/UNC paths, and credential/token marker content. Prove output is bounded while being
read rather than after an unbounded capture. Prove failure records retain only stable controller
fields, byte counts, and digests, never raw stderr or sensitive content.

### Lifecycle and storage

Tests must prove:

- `DRAFT`/`READY` require null runtime identity;
- only `READY -> RUNNING` accepts the exact authorized invocation digest;
- missing, malformed, unauthorized, stale, or substituted invocation identity fails;
- later transitions retain the same runtime identity;
- pre-dispatch `READY -> ABORTED` keeps it null;
- `RUNNING -> ABORTED` retains it;
- custody and invocation writes reject stale snapshots and terminal reopening; and
- no fake-backed success can reach `CANDIDATE` without a strict result, zero changes, accepted
  proposal content, and independently verified identities.

## Development and validation cadence

Use exact new test nodes while developing. Stop at the first failed boundary, correct the cause, and
rerun only the affected slice.

At the final candidate boundary, run once in this order:

1. compile only changed Python files in each repository;
2. focused framework adapter/runtime tests;
3. focused Worker Lab integration, custody, lifecycle, and attempt-store tests;
4. Worker Lab `tests/test_test_catalog.py` and `tests/test_protected_definitions.py` only if protected
   definition compatibility is touched;
5. `git diff --check` in each repository; and
6. read-only status/diff summaries in each repository.

Do not run a complete suite, a milestone profile, Codex, authentication status, a real adapter
process against Codex, a live runtime profile, backup/restore, rollback, or a milestone drill. Those
belong to trusted review after the candidate is inspected.

## Reports

Create `TERRA_PHASE3C_REPORT.md` and `TERRA_PHASE3C_FRAMEWORK_REPORT.md` in Worker Lab. Record:

- exact starting identities and the trusted handoff checkpoint;
- every document and source file read;
- every changed file in both repositories;
- the final process-custody and recovery design;
- every command/result in actual order;
- every failure, correction, and skip;
- exact tests not run and why;
- remaining limitations; and
- separate final status for the framework and Worker Lab candidates.

Do not claim a framework milestone, Phase 3C acceptance, or execution readiness. The only valid final
status is a non-executing candidate awaiting trusted review, or a stopped/blocked report naming the
first unresolved boundary.

## Stop without compensating action

Stop if safe completion requires:

- invoking Codex or live authentication;
- allowing a real attempt to reach `RUNNING`;
- weakening Job Object containment or accepting PID-only absence evidence;
- buffering unbounded process output;
- retaining forbidden content;
- changing a prior catalog, permanent test meaning, attempt schema shape, workspace/disposal rule,
  backup boundary, or framework foundation behavior;
- accessing a credential, remote, network, backup, history export, product repository, or user
  configuration; or
- making an unrelated refactor.

Do not commit, tag, push, publish, create a PR, merge, back up, delete, reset, restore, clean, stash,
or dispose of a workspace. Leave both repositories' candidates uncommitted for trusted review.
