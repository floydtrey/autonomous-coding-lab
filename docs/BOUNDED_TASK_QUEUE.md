# Bounded task queue amendment

This records the approved insertion into the Bounded Spark Tasks queue. S01–S05
are complete. S05b is now complete immediately before S06; all other queue
entries remain unchanged. S06 has now passed its separate acceptance check.

Work only on the assigned task. Preserve existing working changes. If a task
reveals a materially larger problem, stop and propose a follow-on rather than
absorbing it. Do not begin a subsequent task without authorization.

## S05b — Define and carry the V1 output-acceptance contract

**Status:** complete. The [V1 output-acceptance contract](OUTPUT_ACCEPTANCE_V1.md)
is implemented through admission, sealed dispatch, and independent acceptance.

**Verification:** 119 affected Worker Lab tests and 12 root tests passed. AWF's
full suite recorded 93 passes and the pre-existing documentation-wording failure
in `test_current_state_records_reconstruction_authority_and_remaining_work`.
All six S05b acceptance cases pass; source verification reports every component
`MATCH`. No real provider was run and the job execution stop gate remains closed.

**Depends:** S04 and S05. This task is a prerequisite for S06.

**Objective:** Create a versioned contract that distinguishes:

- allowed writable paths;
- required changed paths/artifacts, when a task genuinely requires them;
- required result artifacts/evidence such as test results;
- explicit permission for a valid no-op when acceptance criteria already hold.

**Requirements:**

- Do not infer enforcement semantics from existing labels like `changed-files`
  or `test-results`.
- Preserve existing authority boundaries: allowed paths define permission, not
  mandatory mutation.
- Carry the contract through task admission/dispatch and into independent
  acceptance far enough that S06 can enforce it.
- Do not redesign unrelated result schemas or acceptance machinery beyond what
  this contract requires.
- Keep backward compatibility only where it is cheap and unambiguous; do not
  preserve broken equality semantics just for compatibility.
- Do not broaden the task further.

**Acceptance tests:**

1. A task may allow three writable paths while requiring only one specific
   artifact/change.
2. Missing a declared required artifact/change fails acceptance.
3. A change outside the allowed writable set fails regardless of required-output
   declarations.
4. A task explicitly permitting no-op can succeed with an unchanged workspace
   when its acceptance criteria pass.
5. A task not permitting no-op still cannot silently succeed unchanged when it
   requires a change.
6. Existing `changed-files` / `test-results` labels are either mapped to explicit
   enforceable semantics or rejected as insufficiently specified.

## S06 — Separate allowed paths from required outputs

**Status:** complete. S05b already supplied the necessary runtime behavior;
S06 verified the original four cases without additional runtime changes.

**Verification:** 17 Worker Lab output-acceptance tests and 46 directly affected
AWF tests passed. Portable source verification reports every component `MATCH`;
`git diff --check` passes. Existing working changes were preserved. No real
provider ran; no subsequent task was started.

| Original case | Verified behavior |
| --- | --- |
| Three writable files, one change | Admission preserves three allowed paths; dispatch/handoff and independent acceptance accept only the required file changing. |
| Outside writable set | Both AWF and Worker Lab reject an out-of-scope candidate. |
| Missing required output | Missing required changes or files reject; permission alone never satisfies an output obligation. |
| Explicit no-op | An unchanged workspace succeeds only with explicit permission and passing protected criteria; missing permission or failed criteria rejects. |

Coverage: `components/worker-lab/tests/test_output_acceptance.py` and
`components/autonomous-worker-framework/tests/test_dispatch_adapter.py`, with
AWF code-task, worker-result, and repository-handoff regressions.

**Depends:** S04 and S05b.

**Objective:** Stop treating every writable path as something that must change.

**Work:**

- Represent paths the worker may modify separately from artifacts/changes
  actually required by acceptance.
- Support an explicitly valid no-op outcome when criteria already hold.
- After S05b passes, return to S06 and complete its original four acceptance
  cases using the output-acceptance contract. Do not broaden the task further.

**Original acceptance cases:**

1. A task with three writable files can validly change one.
2. A change outside the writable set still rejects.
3. A declared required output missing still fails.
4. Explicit criteria can accept no-op.

## S07 — Pin Pi and record host compatibility

**Status:** complete; Windows import/startup compatibility passed.

**Depends:** S01.

**Objective:** Establish whether the audited Pi release can run on the intended
Windows host. Pin the package, verify its Node requirement, provide a reproducible
compatibility probe, and record installed package/runtime versions. Do not wire
Pi into production dispatch or qualify a model in this task.

**Evidence:** [S07 probe and reproduction notes](../tools/pi-compatibility/README.md)
and [captured host results](evidence/S07_PI_HOST_COMPATIBILITY.json).
Pi `0.85.1` installed using pnpm `11.19.0`; Node `24.19.0` satisfies `>=22.19.0`.
On Windows x64, SDK import and CLI `--version` both exited 0. The probe's syntax
check passed and portable source identity remained `MATCH` for all components.
S08 selection evidence is recorded below.

## Audit alignment for S08–S15

These tasks implement audit §4's five-step minimum Pi spike and T02, using the
S07-pinned SDK in an isolated Node process. They do not authorize production
dispatch. Use one exact model/runtime, disposable workspaces, bounded deadlines,
and controlled resources; record configuration/tool/extension digests and actual
versions. Keep model retries, compaction calls and continuation inside the total
budget. No second ACL agent loop or compactor is introduced.

The audit requires more than source review: retain real installed-package/model
evidence, distinguish deterministic fixtures from real activity, and reserve the
combined qualification decision for S16. S08–S15 must collectively cover the
following before that decision; a missing prerequisite is a failure/blocker,
never an inferred pass.

## S08 — Prove exact Pi model/endpoint selection

**Depends:** S07. **Status:** complete; all three real selection cases passed.

Supply an explicit model and local API endpoint to the pinned SDK. Disable
default/restore/first-available selection and unapproved resource discovery.
Capture configured and effective model/API/endpoint, installed model identity,
runtime version, request destination/model, settings and response/stop reason.
The correct pairing must complete a bounded real request. Deliberately wrong
model and endpoint cases must fail without fallback. This does not qualify
effective context capacity or worker tools. Audit mapping: §4 spike step 1.

**Evidence:** [S08 results and reproduction](../tools/pi-compatibility/S08.md) and [captured selection results](evidence/S08_PI_MODEL_SELECTION.json). Exact pairing returned `ACL_S08_OK`; wrong model and invalid endpoint each returned HTTP 404 with no fallback. Active server context was 4K; effective 32K support is not qualified.

## S09 — Port ACL bounded file semantics into the Pi spike

**Depends:** S08. **Status:** complete with user-selected qwen3.8:27b Q4_K_M; see [current S09 evidence](../tools/pi-compatibility/S09_27B.md).

Expose only ACL-owned exact-file read/write tools in a disposable workspace;
preserve stale-write checks, normalized paths, encoding/size bounds and atomic
writes. No Pi unrestricted filesystem or shell tools. A real model must read and
edit an allowed file; independently check the diff and protected validator.
Deterministic outside-path and stale-write cases reject, leaving protected files
unchanged. Record the tool/grant digest. Audit mapping: steps 2–3.

**Evidence:** [S09 implementation, validation and proposed follow-on](../tools/pi-compatibility/S09.md). Six deterministic tests passed. The real approved model returned a tool-call-shaped string as text; Pi executed zero tools and independent validation rejected the unchanged target. This historical blocker was resolved by the explicitly approved model change: the 27B real read/edit and seven deterministic tests pass, and exact selection/no-fallback was rechecked. The 7B pairing remains unqualified for tools.

## S10 — Add structured worker outcome reporting to the Pi spike

**Depends:** S09. **Status:** queued.

Add a trusted outcome tool supporting `completed`, `needs_continuation`,
`blocked`, and `failed`, with summary and remaining work/blocker. Exercise it in
the real scoped-edit probe. Malformed or missing claims are incomplete/protocol
failure; worker text or a valid claim cannot independently accept a task.
Record actual model/profile/session identity. Audit mapping: steps 2–3.

## S11 — Implement correct Pi settlement handling

**Depends:** S10. **Status:** queued.

Wait for `agent_settled`, inspect authoritative final message/stop reason, and
distinguish settlement from success. Fixtures must show early `agent_end` does
not finish an attempt, settled errors do not count as completion, and missing
outcome claims remain incomplete. Include disconnect/malformed/truncated event
cases. Capture real settled completion with the S10 claim. Settlement does not
prove process absence. Audit mapping: completion boundary and steps 2–4.

## S12 — Freeze mutations after terminal outcome claim

**Depends:** S09 and S10. **Status:** queued.

Define terminal-claim behavior and test mixed outcome/write batches. Once the
adapter accepts a terminal claim, subsequent writes cannot mutate candidate
state. Both call orderings must have deterministic results; do not assume one
terminating tool ends a mixed Pi batch. Audit mapping: §4 termination and step 3.

## S13 — Prove Pi cancellation and owned-process cleanup

**Depends:** S08; use S11's event handling when available. **Status:** queued.

Start bounded real activity, cancel/time-limit it, and prove the owned process
tree/workload stops. Do not terminate unrelated processes or the pre-existing
model server. Cancelled/timed-out work must never be accepted. Record owned
process identity and absence evidence; use controlled disconnect/truncation
fixtures where needed, without replacing the real cancellation case.
Audit mapping: step 4.

## S14 — Prove exact-session reopen

**Depends:** S09, S11 and S13. **Status:** queued.

Persist one exact session reference, settle/stop it, then reopen that reference
with the same admitted grant/profile revalidated. A different session/reference
cannot substitute; stored tools/configuration cannot widen authority. Verify
continued real interaction and retained identity. Audit mapping: step 5.

## S15 — Exercise one compaction/continuation path

**Depends:** S14. **Status:** queued.

Exercise Pi-owned compaction/continuation within the same grant and total budget.
Capture completion or explicit failure; say whether a real model or controlled
fixture triggered compaction. Do not introduce an ACL compactor. Record actual
server context separately from Pi `contextWindow` metadata. If retaining the
32K requirement for the spike, verify server configuration and meaningful
retention/tool use in this controlled context case before S16; metadata alone
cannot establish it. Broader production readiness remains S19.
Audit mapping: step 5 and §4 effective-context/budget requirement.

### S09 follow-on diagnosis result

[Native tool-call diagnosis](../tools/pi-compatibility/DIAGNOSIS.md) completed: Pi, direct OpenAI-compatible replay, native Ollama chat, and explicit protocol reminder all returned text without native calls. Failure occurs upstream of Pi. No 7B configuration remedy was established. Subsequent user-approved 27B qualification completed S09; S10 remains queued.
