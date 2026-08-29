# Terra Phase 3C Correction Handoff — VS Code Worker

**Implementer:** GPT-5.6 Terra, medium reasoning, in the separate VS Code / GitHub Copilot setup
**Reviewer:** Sol High in the Codex desktop task, only after the user confirms Terra is finished
**Status:** Uncommitted correction handoff; worker and framework execution remain disabled
**Date:** 2026-08-28

## Workflow boundary

This handoff is for the Terra worker running in VS Code. Do not delegate this implementation to a
Terra subagent or switch the reviewer task from Sol to Terra in the Codex desktop app. The Codex
desktop task must wait while the user runs this handoff in VS Code, then review only the resulting
changes after the user confirms that Terra is done.

The current dirty candidate was produced during a mistaken Codex-platform Terra delegation. Treat
all of it as untrusted input: preserve it, inspect it, correct it in place where sound, and do not
assume that its reports or passing-test claims establish acceptance.

## Exact starting state

- Worker Lab: `C:\Users\MineTrackerWorker\repos\worker-lab`, branch `main`, HEAD
  `3c5a7e343c7c23046b1ec3bb369d8e03ec9bc4f8`, one commit ahead of `origin/main`.
- Autonomous Worker Framework:
  `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`, branch `main`, HEAD
  `135373d24837f5d5b0da0650c9c00fc086fcb991`.
- The Worker Lab working tree contains an uncommitted Phase 3C candidate plus the known user-owned
  `docs/8_27_26_ChatGPT_History` export. Preserve that export and do not open, hash, scan, stage,
  copy, or modify it.
- The framework working tree contains the companion uncommitted adapter candidate.
- No live Codex/authentication check, real adapter execution, real attempt, broad suite, commit,
  tag, push, PR, cleanup, or remote operation is authorized.

Before editing, record read-only status and diff summaries in both repositories. Do not require a
clean tree and do not reset, restore, stash, clean, or overwrite the existing candidate.

## Required authority

Read in this order:

1. `AGENTS.md` and `docs/START_HERE.md` in Worker Lab.
2. `docs/PHASE3C_SECURITY_DECISIONS.md`.
3. `TERRA_PHASE3C_ADAPTER.md`.
4. This correction handoff.
5. Only the directly changed Phase 3C source, tests, current-state files, and the two current Terra
   Phase 3C reports in both repositories.
6. The framework `AGENTS.md`, `docs/START_HERE.md`, and directly affected adapter/runtime files.

The original security decisions and handoff remain controlling. This document narrows the repair
work and records the reviewer findings; it does not authorize execution or weaken any decision.

## Current candidate boundary

The candidate attempts to provide:

- strict canonical adapter request parsing and fake-only preparation/preflight/execution seams;
- exact framework, adapter, CPython, launcher, and runtime identity evidence;
- a fixed Worker Lab adapter command;
- a native Windows Job Object runner with bounded streaming output;
- durable process-custody records and restart evidence;
- one-time durable authorized-invocation binding for `READY -> RUNNING`;
- a 32,768-byte accepted-proposal limit and content-addressed proposal storage; and
- construction of a custody-bound strict Worker Lab result from the adapter execution response.

None of those claims is trusted until Terra reviews the final code and the later Sol review accepts
the exact diff and focused evidence.

## Required corrections and proof

### 1. Complete the Windows Job Object failure matrix

Review `worker_lab/windows_job.py`, `worker_lab/process_custody.py`, and their tests. Refactor only as
needed to add deterministic injected native/process/storage seams. Prove all of these cases:

- Job creation or configuration failure occurs before adapter launch and records a valid
  non-dispatching failure without fabricated process absence.
- Adapter launch failure records a valid non-dispatching failure.
- Assignment failure terminates the adapter without sending request bytes and records zero only
  when Job Object activity was independently queried as zero.
- Adapter creation-time capture failure, `ASSIGNED` persistence failure, and `DISPATCHING`
  persistence failure terminate the contained tree and preserve the first failure.
- No request byte is written until assignment identity and both required custody transitions are
  durably persisted.
- Standard-input failure, simulated interruption/cancellation, reader failure or reader non-exit,
  timeout, stdout/stderr overflow, active-process query failure, nonzero active count, and terminal
  persistence failure each end in either independently proven zero-process evidence or durable
  `UNCERTAIN` custody. Never invent zero.
- A normal inert parent-and-child tree exits with observed zero active processes.
- Result acceptance and workspace cleanup are refused until exact `ABSENCE_VERIFIED` zero-process
  evidence exists.
- Recovery leaves a live exact controller untouched; accepts an absent controller only with a
  complete consistent record; rejects PID reuse; and leaves missing, inaccessible, stale,
  contradictory, or uncertain evidence blocked and never rerun.

Do not turn a containment failure into a skip. A genuine unavailable Windows capability may be
skipped only with its exact reason recorded.

### 2. Complete identity and command-authority tests

Review `worker_lab/framework_client.py` and the framework adapter. Add focused proof that each of
these fails before request dispatch:

- wrong Worker Lab commit or any Worker Lab dirt other than the exact unopened history exception;
- wrong framework commit, dirty tracked file, or untracked framework path;
- substituted/reparse framework root, adapter, Python, or launcher path;
- adapter worktree/blob mismatch;
- Python path, executable digest, version, implementation, or architecture mismatch;
- Codex launcher path, digest, or audited version mismatch;
- runtime identity mismatch between prepare, fake preflight, and fake execution;
- altered executable, isolated/no-bytecode flags, adapter path, mode, protocol, environment, working
  directory, model, reasoning effort, timeout, or sandbox; and
- any attempt by exercise, prompt, invocation content, or worker content to supply executable,
  adapter path, raw flags, environment, or working directory.

Use injected evidence and inert fixtures. Do not call the real Codex launcher or authentication.
The framework adapter must independently recompute the audited launcher version through an injected
version-reader seam in tests; a hard-coded version inside the identity is insufficient.

### 3. Verify the actual response-to-result chain

Review the current `accept_execute_response` implementation rather than assuming it is correct.
Using the actual framework `execute-read-only` response shape, prove that Worker Lab:

- accepts an exact canonical field set only and rejects missing, unknown, noncanonical, or
  wrong-typed fields;
- binds invocation, prompt, runtime, proposal/output digests, byte counts, and operation exactly;
- requires a matching final `ABSENCE_VERIFIED` custody record for the same invocation, exit code
  zero, and active process count zero;
- sets `ResultRecord.process_identity` to the final custody-record digest;
- independently supplies and validates Worker Lab-owned repository, workspace, test-plan, and
  unchanged-workspace evidence rather than trusting worker prose;
- enforces the 32,768-byte proposal limit and 65,536/16,384 capture limits while reading;
- rejects empty, wrong-type, invalid UTF-8, embedded NUL, absolute Windows paths using either slash,
  UNC paths using either slash, and credential/token markers;
- atomically stores only accepted proposal bytes at the normalized content-addressed reference and
  retains no unrestricted prompt, raw stderr, environment, absolute command, or rejected content;
  and
- cannot reach `CANDIDATE` merely because a fake adapter returned success.

Tests must pass the actual adapter response into the Worker Lab acceptance function. Do not create
an unrelated `ResultRecord` fixture and treat that as integration proof.

### 4. Verify lifecycle and guarded storage

Retain `worker-lab-attempt:v2` without changing its field shape. Prove through `AttemptStore` and
the durable `InvocationStore` that:

- `DRAFT` and `READY` require null runtime identity;
- the stored invocation is durably reloaded in exact `AUTHORIZED` state;
- the caller supplies the expected stable invocation identity digest explicitly;
- only exact `READY -> RUNNING` binds it once;
- missing, malformed, stale, unauthorized, or substituted identity fails;
- later states and `RUNNING -> ABORTED` retain it;
- `READY -> ABORTED` retains null; and
- stale writes and terminal reopening fail.

Do not edit `worker-lab-v3`, protected definitions, evaluator meanings, workspace/disposal behavior,
or prior schemas.

## Focused validation only

Develop with exact failing nodes. At the final VS Code candidate boundary, run once:

1. compilation of changed Python files only in each repository;
2. framework `tests/test_worker_lab_adapter.py` and the directly changed runtime test nodes;
3. Worker Lab integration, framework-client, process-custody, Windows-Job, lifecycle, invocation-
   store, and attempt-store focused tests;
4. protected-definition/catalog tests only if their compatibility is touched;
5. `git diff --check` in both repositories; and
6. read-only final status and diff summaries.

Use repository-local pytest temporary directories. Do not run either complete suite, a milestone
profile, live Codex/authentication, a real adapter, a real attempt, backup/rollback, or cleanup.

## Reports and final stop

Update `TERRA_PHASE3C_REPORT.md` and `TERRA_PHASE3C_FRAMEWORK_REPORT.md` with:

- the exact starting dirty boundary and the fact that the inherited candidate was untrusted;
- every file read and changed;
- every focused command and result in actual order;
- every failure, correction, and skip;
- exact tests not run and why;
- any remaining limitation; and
- separate framework and Worker Lab candidate status.

Leave all changes uncommitted. Do not tag, push, create a PR, or claim Phase 3C acceptance,
framework-milestone readiness, or live-execution authority. Stop and tell the user that the VS Code
Terra candidate is ready for Sol review. The user will then return to the Codex desktop task and
explicitly confirm that Terra is finished.

## Sol Review Round 1 — Rejected for correction

**Review status:** The focused baseline passes, but the candidate does not yet satisfy the Phase 3C
security contract. VS Code Terra must correct the findings below and leave the result uncommitted for
another Sol review.

Sol independently reran only the authorized focused slices:

- Worker Lab integration, framework-client, custody, Windows-Job, lifecycle, invocation-store, and
  attempt-store tests: `53 passed` with one pytest-cache permission warning.
- Framework adapter/runtime tests: `37 passed` with one pytest-cache permission warning.
- `git diff --check` was clean in both repositories.

Passing these slices does not establish acceptance because several required failure and independent-
evidence paths are absent from the implementation and tests.

### SR1-01 — Do not fabricate Worker Lab-owned success evidence

`worker_lab/framework_adapter.py::accept_execute_response` currently sets `observed_head` equal to
`starting_commit`, declares `workspace_state` to be `unchanged`, and emits a passing validation stage
for every sealed test ID without receiving any independently observed Git, workspace, or evaluator
evidence. A fake adapter response plus process custody can therefore manufacture an authoritative
passing `ResultRecord`.

Change the acceptance API so those fields come from strict Worker Lab-owned evidence records or
injected read-only verifiers. Recompute and validate observed HEAD, zero changed paths, workspace
receipt/path identity, and the actual ordered validation-stage results. Do not synthesize passes.
Acceptance must remain unable to transition an attempt to `CANDIDATE`; that later transition must
require the separately accepted proposal/result and the governing lifecycle checks.

Add negative tests proving a successful fake response is rejected when independent Git/workspace or
test evidence is missing, stale, mismatched, incomplete, reordered, or failed.

### SR1-02 — Require complete successful custody, not only a terminal label

`accept_execute_response` currently checks only `ABSENCE_VERIFIED`, active count zero, and exit code
zero. `ProcessCustodyRecord` permits an `ABSENCE_VERIFIED` record with no adapter identity and no
request evidence, and acceptance does not reject a retained `first_failure`.

For a successful result, require all of the following from the exact final durable record:

- matching invocation ID and stable invocation identity;
- non-null adapter PID and Windows creation time;
- `request_sent is True`;
- successful `EXITED -> ABSENCE_VERIFIED` provenance, or an equivalent explicit outcome field that
  cannot be confused with a terminated/failure path;
- exit code zero, observed active count zero, canonical absence time, and `first_failure is None`;
  and
- a final custody digest reloaded from `ProcessCustodyStore`, not merely a caller-constructed object.

Tighten custody validation so a fabricated/non-dispatched absence record cannot satisfy successful
acceptance. Keep non-dispatched termination evidence usable for failure/recovery reporting without
making it execution success.

### SR1-03 — Reader failures must be authoritative failures

Both `worker_lab/windows_job.py::_drain_bounded` and the new drain threads in
`tools/codex_runtime.py::execute_codex_bounded` allow a stream-read exception to terminate a daemon
thread without reporting that exception to the controlling thread. If the bytes collected before the
exception happen to form valid JSON/proposal content, the process can be treated as successful even
though capture was incomplete.

Capture the first reader exception in a thread-safe controller-owned slot/event, terminate the Job
Object/process, join both readers, and fail closed. Persist only bounded byte counts/digests and either
verified zero-process termination evidence or `UNCERTAIN`. Never return partial bytes as success.

Add deterministic tests for stdout read failure, stderr read failure, a reader that remains alive,
and a failure after a syntactically valid prefix. Cover both the outer Windows runner and the inner
bounded Codex runtime with injected streams/processes; do not invoke Codex.

### SR1-04 — Finish the Job Object failure matrix instead of relying on generic cleanup

`tests/test_windows_job.py` contains only five cases: normal parent/child exit, stdout overflow,
timeout, Job creation failure, and adapter launch failure. The required assignment, creation-time,
custody-persistence, dispatch-persistence, input-write, interruption, reader, active-query,
nonzero-active, and terminal-persistence cases are still absent.

The generic `except BaseException` path also swallows custody-transition write failures and excludes
already persisted `EXITED`/`TERMINATED` records from correction. Prove that each injected failure
leaves the durable store in the strongest truthful state. It may be `ABSENCE_VERIFIED` only after an
observed zero; otherwise it must remain blocked/uncertain, and no failure may be silently converted
to success.

Implement every deterministic failure test listed earlier in this handoff. Assert launch and request
ordering directly, including that no request byte is written before assignment identity and durable
`ASSIGNED` plus `DISPATCHING` custody.

### SR1-05 — Enforce canonical requests and exact per-mode responses on both sides

The framework adapter parses request JSON but does not compare the input bytes with its canonical
encoding. Noncanonical JSON and duplicate-key encodings can therefore be accepted. Require exact
canonical UTF-8 request bytes after strict parsing and reject duplicate keys.

Worker Lab `framework_client.call_adapter` checks only three common fields with `.get()` and accepts
unknown fields. It also does not reject a mode that is inconsistent with the invocation state before
calling the runner. Define an exact response field set for `prepare`, `preflight`, and
`execute-read-only`; reject missing/unknown fields and noncanonical responses; and enforce the exact
mode/state mapping before process dispatch.

Add tests for whitespace/key-order drift, duplicate keys, missing/unknown response fields, wrong
mode for `PREPARED`/`AUTHORIZED`/`DISPATCHING`, and invalid scalar types.

### SR1-06 — Use contained atomic proposal storage

`ProposalStore` builds `state_root/proposals` with ordinary `Path.mkdir`, reads existing targets, and
uses `os.replace` without the containment, symlink, and reparse protections used by
`AtomicRecordStore`. A substituted proposals directory or target can redirect accepted bytes outside
the intended state root.

Use the existing contained storage rules or a narrowly extended binary-content store. Reject linked
or reparse-substituted roots, parents, and targets; keep the normalized content-addressed reference;
atomically write and verify exact bytes; and add focused substitution/stale-content tests.

### SR1-07 — Complete identity and runtime evidence coverage

The current identity tests cover only part of the required matrix. Add explicit cases for wrong
Worker Lab commit, Python implementation, configured Python path, adapter/launcher path, Codex
version, reparse/substituted components, fixed flags, protocol, mode, working directory, and the
absence of any invocation/exercise/prompt authority over executable, flags, environment, or cwd.

The framework tests do not call `local_runtime_identity` or its injected version reader, and no test
currently exercises `execute_codex_bounded`. Add fake-only tests for exact runtime identity agreement,
version mismatch, bounded stdout/stderr at limit and limit-plus-one, invalid UTF-8, timeout, nonzero
exit, and the reader-failure behavior in SR1-03.

### Correction validation and stop

Run exact new failing nodes while correcting, then rerun the same final focused slices once with a
repository-local basetemp. Compile changed Python and run `git diff --check` in both repositories.
Update both Terra reports with the Round 1 failures, corrections, exact commands/results, and tests
still not run. Do not run a full suite or any live Codex/authentication/adapter/attempt action. Leave
both repositories uncommitted and return them to the user for Sol Review Round 2.

## Round 1 correction completion record

VS Code Terra completed the Worker Lab containment, custody, independent-evidence, and contained-
storage portions of this handoff before its usage limit. With explicit user authorization, Codex
continued the remaining fake-only framework protocol and bounded-runtime work. The implementation is
now uncommitted and non-executing; it awaits the final Sol diff review and checkpoint decision.

## Sol high-review correction completion

Sol's final high-level review found four remaining gaps: caller-constructed workspace/test success
claims, an unsealed adapter working directory, incomplete framework invocation scalar validation,
and missing structured-text/content-reference bounds. With the user's authorization, Codex corrected
all four in place. Final focused evidence is `86 passed, 2 skipped` in Worker Lab and `53 passed` in
the framework, with changed Python compilation and clean diff checks in both repositories. The two
skips are only unavailable Windows symlink creation. The candidate remains uncommitted and
non-executing pending the trusted checkpoint operation.

The trusted checkpoint operation subsequently passed the complete 158-test framework gate, created
framework commit `2d8c93312103015125f0eef9e2afdc697a45d244`, and annotated it as
`v0.2.0-worker-lab-adapter`. Worker Lab pins that exact commit and adapter digest; its final focused
checkpoint validation passed `87 passed, 2 skipped`. Execution remains separately disabled.
