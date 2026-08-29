# Phase 3C Security Decisions

**Status:** Approved design authority for a bounded, non-executing implementation candidate
**Date:** 2026-08-28
**Worker Lab starting checkpoint:** `62aaf13`
**Framework starting checkpoint:** `135373d24837f5d5b0da0650c9c00fc086fcb991`
**Execution authority:** Disabled

## Decision boundary

These decisions settle the security questions reserved by `PHASE3_READINESS_REVIEW.md` so a
reviewable Phase 3C adapter candidate can be implemented. They do not authorize a Codex worker,
`READY -> RUNNING`, a real or synthetic attempt, a milestone tag, a remote operation, or work in an
external product repository.

The first implementation candidate must remain test-driven and fake-only. A trusted controller must
review and checkpoint the exact framework adapter and Worker Lab client before separately
authorizing one live synthetic read-only proposal.

## D3C-01 — Retain the fixed local process adapter

Use canonical JSON over standard input and standard output through the framework-owned entry point
`tools/worker_lab_adapter.py`. Do not directly import framework Python modules into Worker Lab, alter
`sys.path`, or introduce a service, daemon, queue, plugin, shell command, or network transport.

Worker Lab constructs the complete command from trusted configuration. Invocation, exercise,
prompt, worker, and repository content cannot provide an executable, adapter path, flag,
environment, working directory, or raw Codex option. The adapter supports only the protocol modes
explicitly implemented for Phase 3. Workspace-write execution remains rejected in Batch 3C.

## D3C-02 — Pin the framework, adapter, and Python identities

The trusted configuration contains:

- the canonical absolute framework repository root;
- the exact full framework commit;
- the canonical absolute CPython executable;
- the exact adapter relative path `tools/worker_lab_adapter.py`; and
- the exact supported client and adapter contract versions.

For this local checkpoint, the configured Python identity is:

- path: `C:\Program Files\Python312\python.exe`;
- implementation/version/architecture: `CPython 3.12.10 AMD64`; and
- executable digest:
  `sha256:4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.

Before preparation or execution, the client fails closed unless:

1. both configured paths resolve to their expected canonical locations;
2. neither the framework root, Python executable, adapter path, nor any traversed component is a
   linked or reparse substitution;
3. framework `HEAD` is the configured full commit;
4. framework tracked and untracked status is empty;
5. the adapter's working-tree bytes equal the blob at the configured commit;
6. the Python path, version, implementation, architecture, and executable digest match; and
7. the command is the fixed configured Python, isolated/no-bytecode flags, exact adapter path,
   exact mode, and exact protocol version.

The known user-owned `docs/8_27_26_ChatGPT_History` path is the sole Worker Lab untracked exception.
It is never opened, hashed, scanned, copied, passed to the adapter, or treated as authority. All
tracked Worker Lab bytes and every executable or protected path must match the configured Worker Lab
commit. Any other untracked path fails closed.

## D3C-03 — Use one exact runtime profile and canonical runtime identity

`terra-medium:v1` remains the only supported profile:

- Codex CLI: audited `0.149.1`;
- model: `gpt-5.6-terra`;
- reasoning effort: `medium`;
- timeout: `900` seconds;
- Windows sandbox setting: framework-audited `elevated`; and
- worker sandbox: exactly `read-only` for Batch 3C.

Preparation returns the digest of a canonical `worker-lab-runtime-identity:v1` object containing the
framework commit, adapter blob digest, adapter contract version, Python identity above, resolved
Codex launcher digest and audited version, environment-sanitization policy version, operation,
sandbox values, model, reasoning effort, timeout, and fixed command digest. It contains no raw
absolute path. Framework preflight and execution independently recompute the same object. Any
difference fails before Codex starts.

The existing ChatGPT-only authentication, API-key rejection, GitHub credential stripping, strict
Codex configuration, separate target repository, and sandbox enforcement remain framework-owned.
Worker Lab must not copy them.

## D3C-04 — Use a Windows Job Object for complete process-tree custody

The Worker Lab adapter-process runner owns an outer Windows Job Object configured with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Its handle is non-inheritable and is never duplicated into the
adapter or worker, so a child cannot keep the Job Object alive after the controller exits. This is
transport/process-tree custody, not a replacement for the framework's Codex authentication,
sandbox, environment, command, or timeout controls.

Required launch ordering:

1. create the Job Object and persist the controller/process-custody intent;
2. start the exact adapter with binary pipes, no shell, and no request bytes;
3. assign the adapter process to the Job Object;
4. verify assignment and persist adapter PID plus Windows process creation time;
5. only then send the bounded canonical request; and
6. require the adapter to perform no preflight or child creation until it has read and validated the
   complete request.

If Job Object creation, configuration, assignment, identity capture, or persistence fails, terminate
the adapter, send no request, and record a non-executing containment failure.

On timeout, interruption, malformed/oversized output, or controller cancellation, terminate the Job
Object, wait for the adapter handle, and verify the Job Object reports zero active processes. Do not
inspect, validate, quarantine, or delete the workspace before this proof. If absence cannot be
proved, keep the invocation/attempt uncertain and leave the workspace untouched.

Add strict durable `worker-lab-process-custody:v1` evidence under
`state/process-custody/<invocation-id>.json`. Its identity binds the invocation digest, controller PID
and Windows creation time, adapter PID and creation time when known, containment mode, assignment,
exit/termination observation, active-process count, absence-verification time, first failure, and
canonical custody digest. `ResultRecord.process_identity` is the custody digest, never a reusable
PID alone.

PID reuse must be rejected by comparing the Windows process creation time. On restart:

- if the recorded controller process with the same creation time is active, do not touch the
  invocation or workspace;
- if that exact controller is absent, kill-on-parent-close plus the no-request-before-assignment
  protocol may be used as process-absence evidence only when the complete custody record validates;
  and
- any missing, stale, inaccessible, or contradictory evidence remains uncertain and cannot be
  converted to success or retried.

## D3C-05 — Bound and minimize retained content

Use these exact UTF-8 byte limits:

| Content | Maximum |
|---|---:|
| Canonical adapter request | 262,144 bytes |
| Deterministic worker prompt | 32,768 bytes |
| Canonical adapter response/result | 65,536 bytes |
| Successful proposal content | 32,768 bytes |
| Captured worker stdout | 65,536 bytes |
| Captured worker stderr | 16,384 bytes |
| Structured `expected` or `observed` text | 2,048 bytes each |
| Relative content reference | 256 bytes |

The implementation must enforce capture limits while the process runs; it must not first buffer
unbounded output in memory. Crossing a limit terminates the contained process tree and yields
`INTEGRATION_RESULT_INVALID` with no candidate.

Durable retention rules:

- retain the invocation, strict result, process-custody record, byte counts, and canonical digests;
- retain a successful proposal only after exact UTF-8, size, digest, and prohibited-content checks;
- store accepted proposal bytes atomically under a normalized relative content-addressed path;
- retain only the prompt digest, never the unrestricted prompt;
- never retain raw stderr, authentication/status output, environment values or dumps, commands with
  absolute local paths, or an overflowing/malformed response; and
- never retain content containing an absolute Windows/UNC path or the names/values of API-key,
  GitHub-token, authorization-header, or bearer-token material. Such content fails closed; do not
  attempt a best-effort secret redaction and then accept it.

Failure evidence uses stable codes, bounded controller-authored summaries, exit status, byte counts,
and digests of bytes safely observed before termination. Worker prose cannot populate authority,
validation, containment, or lifecycle fields.

## D3C-06 — Bind `READY -> RUNNING` without a schema-version change

`worker-lab-attempt:v2` already contains `runtime_identity`. Keep the record schema unchanged.
Strengthen lifecycle behavior so `runtime_identity` may change exactly once, from `null` to the exact
authorized invocation digest, only during `READY -> RUNNING`.

Required invariants:

- `DRAFT` and `READY` require `runtime_identity` to be null;
- `RUNNING` and every later non-aborted execution state require it to be the invocation digest;
- the invocation must already be durably `AUTHORIZED` and revalidated;
- `transition_attempt` must receive the expected invocation digest explicitly;
- `AttemptStore` permits only that exact one-way change and rejects substitution or later change;
- a pre-dispatch abort from `READY` retains a null runtime identity; and
- an abort from `RUNNING` retains the bound runtime identity.

This is a lifecycle invariant correction, not an attempt record shape change.

## D3C-07 — Keep `worker-lab-v3` immutable

The integrated `worker-lab-v3` catalog, T016/T022 bindings, and Phase 3 profiles are accepted and
must not be edited. Add focused cases to the already bound test files where possible. New paths that
do not match an immutable selector are treated as unmapped/high risk and explicitly select the union
of `FRAMEWORK_ADAPTER_CHANGE:v1` and `READ_ONLY_INVOCATION:v1`; they do not justify mutating v3.

No profile may claim a live proposal passed during this implementation batch.

## D3C-08 — Require a new framework milestone before first execution

Any framework adapter, runtime, bounded-stream, or containment-related source change requires a new
reviewed framework checkpoint before Worker Lab may start Codex. The intended milestone name is
`v0.2.0-worker-lab-adapter`; it must identify the exact accepted adapter commit and must not move
`v0.1.0-foundation`.

Terra does not create this tag. Terra leaves both candidates uncommitted for trusted review. The
trusted controller separately reviews the diffs, runs the required focused and framework candidate
validation, checkpoints the framework, and only then updates the configured framework commit.

Worker Lab `v0.3.0` remains reserved for the Batch 3E Phase 3 recovery/milestone gate.

## Implementation approval and final stop

These decisions authorize the bounded implementation described by `TERRA_PHASE3C_ADAPTER.md` using
fakes and inert child-process fixtures. They do not authorize:

- calling Codex, checking live authentication, or running a real worker;
- a real adapter request against a workspace;
- `READY -> RUNNING` outside focused fake-backed tests;
- a synthetic proposal acceptance run;
- a commit, tag, push, PR, merge, backup, cleanup, or remote operation; or
- any external product repository.

After Terra's candidate and report are complete, stop for trusted review.
