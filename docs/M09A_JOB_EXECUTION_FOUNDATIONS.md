# M09A — authorization, realistic worker budgets, shared deadline and telemetry

M09A is the first bounded implementation slice of M09. It prepares the existing
single-task machinery for job-controlled coding work; it does not add the
sequential controller loop, status, stop or reconcile commands.

## Selected coding-work ceilings

The protected Pi configuration remains configurable. The selected initial
operating ceilings are:

- requested context: 131072 tokens
- model requests: 64
- tool calls: 128
- maximum output: 8192 tokens per provider response
- provider timeout: 900 seconds
- attempt timeout: 1800 seconds
- tool timeout: 30 seconds
- maximum concurrency: 1

These are ceilings, not targets. Smaller explicitly pinned values remain
supported for deterministic exhaustion tests. The protected coding-worker
runtime requirement now admits an 1800-second attempt ceiling. Any changed
configuration still requires a fresh exact configuration pin, matching Provider
Binding/readiness evidence and explicit activation; no fallback is introduced.

## Worker instruction

The Pi system instruction now describes bounded multi-file coding work rather
than a one-file qualification edit. It permits reading authorized context,
making required changes within granted files and rereading relevant files while
preserving the existing admitted-tool-only boundary. Shell, tests, Git, network,
resource discovery, retries, model fallback, session reopen and compaction
remain unavailable. The worker reports exactly one terminal claim; acceptance
remains independent.

## Job authorization

`service_runtime_v3.authorize_invocation()` no longer bypasses or merely
rejects JOBTASK invocations. JOBTASK authorization enters M07's existing
`job_authorization_gate()` and holds the job lock across the existing V3
authorization transaction. The gate continues to prove the exact active
reservation, controller, invocation, admitted attempt, dependencies and accepted
input lineage and rejects expired or inconsistent state.

No second job authority contract is introduced.

## Shared reservation deadline

M07's absolute reservation deadline is reused by worker and validator execution.
Job worker dispatch resolves the same reservation allowance before launch and
passes its absolute deadline into the Pi request. Pi applies the minimum of that
absolute deadline, the configured attempt timeout and the existing dispatch
timeout.

Protected validation resolves the same job deadline and each check applies the
minimum of the remaining reservation time and its approved check timeout.
Subsequent checks do not receive a new reservation clock. Expiration before
process creation launches no worker/validator. Expiration while owned work is
running enters the existing termination, bounded cleanup and custody-evidence
path. Cleanup proof remains mandatory.

A restart does not create a new reservation or deadline.

## Objective attempt evidence

M09A does not add a grading engine. Existing durable evidence is intentionally
retained as the M10 grading input:

- run-task intent: attempt/invocation identity and start timestamp;
- sealed Pi request: exact worker/configuration, request/tool/output/context/time
  ceilings and absolute execution deadline;
- Pi result/worker outcome: terminal claim, summary, remaining work, measured
  request/tool counts and token usage when available, stop reason/error,
  candidate and custody evidence, and end/record timestamp;
- validation report: protected-check identities/results, timing, logs and
  validator custody;
- task-run/acceptance records: final workflow disposition and independent
  acceptance evidence.

Elapsed wall time is derivable from the retained start/end timestamps. Budget or
timeout exhaustion remains an objective stop/error reason. Failed attempts are
immutable evidence and are not overwritten by later work.

## Verification status

Implementation is staged on the M09A development branch. Focused and affected
local tests, portable-source verification and final checkpoint integration are
still required before M09A is declared complete.
