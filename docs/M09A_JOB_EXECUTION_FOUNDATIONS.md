# M09A — authorization, realistic worker budgets, shared deadline and telemetry

M09A is the first bounded implementation slice of M09. It prepares the existing
single-task machinery for job-controlled coding work; it does not add the
sequential controller loop, status, stop or reconcile commands.

**Checkpoint status:** implementation and the focused Windows job/deadline/
acceptance checks below are verified. The Node adapter and root source-identity
regressions, final integration checkpoint and M09A closure remain pending.
Do not start M09B from this intermediate verification checkpoint.

Source assignment: the conversation titled "ACL M09A — Authorization, Realistic
Worker Budgets, Shared Deadline, and Telemetry". An opaque chat identifier was
not available to record.

## Selected coding-work ceilings

The protected Pi configuration remains configurable. The selected initial
operating ceilings in `config/pi-local-worker.json` are:

| Setting | Selected ceiling |
| --- | ---: |
| requested_context_tokens | 131072 |
| request_limit | 64 |
| tool_calls_limit | 128 |
| max_output_tokens (per provider response) | 8192 |
| provider_timeout_seconds | 900 |
| attempt_timeout_seconds | 1800 |
| tool_timeout_seconds | 30 |
| max_concurrency | 1 |

These are ceilings, not targets. Smaller explicitly pinned values remain
supported for deterministic exhaustion tests. The protected coding-worker
runtime requirement now admits an 1800-second attempt ceiling. Any changed
configuration still requires a fresh exact configuration pin, matching Provider
Binding/readiness evidence and explicit activation; no fallback is introduced.

Configuration/binding/readiness tests use explicitly identified simulated runtime
observations. M09A has not regenerated a live host's Provider Binding, requalified
a real model, or enabled production activation. Before the first later real run,
recreate the matching binding/readiness and activation evidence through the
existing approved path; old evidence is not made current by these source tests.

## Worker instruction

The Pi system instruction now describes bounded multi-file coding work rather
than a one-file qualification edit. It permits reading authorized context,
making required changes within granted files and rereading relevant files while
preserving the existing admitted-tool-only boundary. Shell, worker-run tests,
Git, network, unapproved filesystem access, resource discovery, automatic retries,
model fallback, session reopen and compaction remain unavailable. The worker
reports exactly one terminal claim; writes freeze and acceptance remains
independent.

## Job authorization

`service_runtime_v3.authorize_invocation()` replaces the JOBTASK-only rejection
with M07's existing `job_authorization_gate()`, holding the job lock across the
existing V3 authorization transaction and retaining expected-state checks. The
gate proves the exact active reservation, controller, invocation, admitted
attempt, dependencies and accepted input lineage. Expired or inconsistent state
blocks rather than selecting a replacement attempt.

No second job authority contract is introduced. The configured runtime, sealed
prompt/context, writable grants, protected checks and output obligations remain
bound to the authorized invocation.

## Shared reservation deadline

M07's absolute reservation deadline is reused by worker and validator execution.
Preparation consumes time from that reservation. Job worker dispatch resolves
the reservation allowance before launch and carries its absolute deadline into
the Pi request. Pi applies the minimum of that deadline, the configured attempt
timeout and the existing dispatch timeout. Provider and tool timeouts remain
additional limits.

Protected validation resolves the same job deadline and each check applies the
minimum of its remaining time and its approved check timeout. Subsequent checks
do not receive a new reservation clock. The validator checks time before
creation, before resuming an owned suspended process, around polling, through
owned-child drain and before concluding validation. A zero exit observed after
the deadline is not a timely pass. The applicable absolute deadline is retained
in validation intent/report records.

Expiration before process creation launches no worker/validator. Expiration while
owned work is running enters existing termination, bounded cleanup and custody
recording. Cleanup may consume its separately bounded allowance after work is
stopped; it does not grant more execution time. Missing or uncertain absence
proof blocks advancement. No process-absence inference or unrelated-process
termination is added.

A restart does not create a new reservation or deadline. The integration tests
include replay of retained noncompleted worker outcomes after reservation expiry:
no new worker starts and the original outcome and job reservation remain intact.
This does not implement M09C's user-facing stop/reconcile commands.

## Objective attempt evidence

M09A does not add a grading engine. Existing durable records are joined using
attempt/invocation identity and their digests:

| Evidence | Objective information retained |
| --- | --- |
| Job aggregate/reservation | Job/task identity, reservation identity, reserved time, immutable deadline and approved attempt budget |
| Run-task intent | Invocation identity and controller-observed attempt start timestamp |
| Sealed Pi request | Model/configuration identity, request/tool/output/context/time ceilings and effective execution deadline |
| Pi result and worker outcome | Terminal claim, summary, remaining work, observed request/tool counts and token usage when available, stop/error reason, candidate and custody evidence, recorded end timestamp |
| Validation intent/report | Applicable reservation deadline, protected-check references/results, start/end times, logs and validator custody |
| Task-run and acceptance records | Workflow disposition and independently verified acceptance/check references |

Controller-observed attempt elapsed time is derivable from the retained run-task
intent and worker-outcome timestamps. This is not GPU-only inference time. The
reservation timestamp additionally permits measuring preparation-inclusive time.

A hard stop may leave no terminal adapter response: usage and claim then remain
unknown/null, not fabricated as zero or completed. The sealed request and timeout
reason remain evidence. Token usage supplied by the adapter/provider is not an
independent hardware measurement. Failed attempts and earlier verification runs
are not overwritten or relabelled when a later run succeeds.

## Verification record — 2026-09-18

The following are operator-reported Windows console results from the source
conversation. They are not assistant-executed Windows runs or an imported raw
JUnit archive. Overlapping batches are listed separately, not added into a
misleading full-suite total.

| Checkpoint / batch | Exact result | Interpretation |
| --- | --- | --- |
| `b194f8e2bf4e7380d933c1679ead4a0e9d846f11`: Pi configuration/protocol, runtime selection, job plan/admission/runner (six files) | 216 passed, 2 failed in 10.00s; exit 1 | Admission fixture lacked a trusted mapping for task B's README when registering the whole plan |
| `0c8b5e5adfe321b4cf77da8c062a13360485fb56`: job admission rerun | 11 passed in 3.48s; exit 0 | Fixture corrected before approval; unreserved invocation and unmapped later-task rejection remain tested |
| `472d5078d9481bb6f013ac245a535beb329be08d`: Pi dispatch/supervision, worker outcomes, protected validation, acceptance, workflow (six files) | 114 passed, 5 failed in 221.94s; exit 1 | Five workflow cases blocked after long temporary paths prevented custody-record writes; original uncertainty evidence was retained |
| Same `472d507` production bytes: workflow rerun after the operator enabled Windows long paths and restarted | 9 passed in 26.86s; exit 0 | Resolved the observed host path-length failure without changing directory permissions, production storage or test paths |
| `3e8531a9b9018add737276ce481af47c51499152`: validator-deadline, protected validation, acceptance and workflow (four files) | 67 passed in 156.10s; exit 0 | Includes 12 deterministic validator-deadline race cases and affected real Windows validation/acceptance regressions |
| Same `3e8531a` production bytes plus the exact integration test now committed here | 13 passed in 22.97s; exit 0 | One real job/authorization/dispatch/record pipeline with simulated provider, clock and validator processes; no sequential loop or real model |

The integration test is `components/worker-lab/tests/test_m09a_job_execution.py`.
Its operator-verified LF SHA-256 is
`d722e3865ff7e64a8266a922f0d2dfa75a774b3fbc63cd80e5cc398eb60100cd`;
Git blob `a923877b235662e4f442444cd6381fa5e602fd6c`. The operator's local detailed
report is named `M09A-job-execution-20260918-082822-880.xml`; its contents have not
been retrieved into this checkpoint.

The 13 cases exercise a common deadline from reservation through dispatch and
multiple checks; preparation consuming time; stricter worker/check limits;
expired/mismatched reservations; a late worker claim blocked before validation;
joinable model/config/usage/time/check evidence; incomplete/failed claims and
remaining work; immutable replay; and unknown claim/usage after a hard stop.
Task B stays pending with no attempt allocated.

The earlier manifest calculation error was corrected in `a09b600`; it had
omitted the component-relative `worker_lab/` path prefix from the aggregate.
No verifier was weakened. The latest operator verification at `3e8531a` reports:

| Component | Files | Verified SHA-256 digest |
| --- | ---: | --- |
| autonomous-worker-framework | 13 | `03c17a17e39aba142a5a0bf1085484f8dc715a1a41218cfa170d9eda8c5cc6dd` |
| local-model-bench | 10 | `139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc` |
| worker-lab | 45 | `ef8cf4476b9eceff533280a1ca0a01a0946521f3b187a3860915c66df2053a5b` |

Manifest-byte SHA-256:
`8536211077e535503866d831cf904494b25a92272bf83ed9f529385d2b4e73b9`.
This checkpoint adds only the verified test and this documentation; production
code, selected configuration and manifest bytes are unchanged from `3e8531a`.

## Remaining closure work and next-task boundary

Run the existing Node adapter regression file with `ACL_PI_TEST_PYTHON` set to the
approved test interpreter, and `tests/test_portable_source.py` from the repository
root. Neither requires a model server, Docker, model fallback or installation.
Keep their actual results separate from the Windows results above. Then record
the final M09A checkpoint, branch/HEAD and working-tree state before closure.

At the last reported local status, the integration test and
`components/knowledge-core/task6i-host-evidence/` were untracked. The test is
included here byte-for-byte; KC host evidence must remain untouched and untracked.
Do not stage the repository wholesale. Do not reset an advanced branch.

M09B is a separate assignment for sequential run/status. It must reuse these
single-task operations, preserve the reservation-before-preparation order, exact
job authorization, stricter shared deadlines, immutable evidence and independent
acceptance, and advance only from verified accepted snapshots. M09C owns full
stop/reconcile, M09D assembled closure, M10 the no-KC real two-task usefulness and
initial grading baseline, and M11 later KC guidance/retrieval integration. Do
not add any of those features in M09A.
