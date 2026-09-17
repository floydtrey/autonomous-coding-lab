# M06 — one task through protected checks and acceptance

The public `run-task` command now composes the existing supervised worker,
protected validation and evidence-gated acceptance operations. It returns
`accepted`, `failed`, `blocked` or `pending_review`, with the worker outcome,
candidate location, retained diff and validation evidence. This supersedes M04's
worker-only public command behavior. M04 outcomes and M05 validation reports
remain separate immutable observations with `accepted: false`.

M06 is implemented and verified in the separate development target. One bounded
real-model ACL maintenance task returned an independently accepted diff through
this workflow. The checkpoint evidence is described below; the original checkout
has not adopted these controller changes.

## Prepare one explicitly approved task

Use the existing attempt, workspace, task-packet, invocation preparation and
authorization operations described in [M04](M04_WORKER_OUTCOMES.md). The task
file still uses `worker-lab-run-task:v1` and references one exact authorized
invocation, controller and canonical workspace root. Its digest is checked again
inside the worker operation, so replacing the file cannot switch the approved
invocation between workflow approval and dispatch.

The running controller, authoritative checks, judging inputs and durable records
must remain outside worker writes. The worker receives the admitted exact-file
tools. A separate target checkout may contain source for a future controller, but
its edits cannot replace the running authority. Paths below are examples; the
operator supplies the installation, state, target and checker locations.

Before execution, explicitly approve the already-selected catalog commands:

```powershell
worker-lab --root C:\ACL\lab approve-task-execution C:\ACL\operator\task.json `
  --controller trusted-controller `
  --protected-file C:\ACL\checks\check.py `
  --acknowledge-unsandboxed-host-code-execution `
  --timeout-seconds 30 --output-limit-bytes 1048576 --cleanup-timeout-seconds 5

worker-lab --root C:\ACL\lab run-task C:\ACL\operator\task.json
```

Repeat `--protected-file` for all declared checker and judging dependencies. The
commands come from the protected catalog; the task and worker cannot supply shell
commands. Approval binds the exact invocation, task file, source identity, test
plan, executable and declared input bytes, limits and review requirement. Changed
approval cannot replace the immutable consent. Missing consent launches nothing.

The local check mode is `operator-approved-local-test:v1`, with resource exposure
`unsandboxed-host-code-execution`. It runs with the host user's access. Windows
Job Objects provide owned process lifetime and cleanup, not filesystem or network
isolation. Advance consent explicitly authorizes these named checks for this
invocation's future candidate. After verified worker absence, the workflow derives
M05's candidate-specific approval and rechecks that it matches the advance consent.
The separate `approve-validation` and `validate-task` interfaces remain available
for examining an already stopped candidate.

Model activation, binding/readiness and protected host settings remain separate
requirements. These commands do not enable Pi, load a model, restart a server,
install dependencies or select a fallback. Context and supported runtime settings
remain configurable through M05A's protected configuration and pin; the current
operator preference remains 131072 context tokens with a 2048-token output budget.

## Acceptance gates

`accept-task` independently reloads the durable evidence. It requires a completed
worker claim, successful worker custody with verified zero workload, the exact
unchanged candidate and Git base/receipt, current protected authority, and the
complete selected set of passing checks. It verifies each validator's launch,
process identity, custody, result and logs. Empty or incomplete checks cannot pass
by carrying a `passed` label.

The admitted output contract controls permitted paths, required changes, required
artifacts, evidence and no-op permission. Ignored and other new files count as
changes; rename source and destination paths remain visible. A no-op needs explicit
permission and all required checks and artifacts. Retained worker output and the
saved diff must match the current candidate evidence. Acceptance rechecks the
evidence before persisting its result.

Generic lifecycle transitions cannot produce `PASSED`. Successful M06 acceptance
has its own immutable record; the attempt and invocation remain
`OUTCOME_RECORDED`. A task is not accepted merely because it reached that lifecycle
state or passed a check. Acceptance does not commit, promote, publish or modify
the running controller or the user's main checkout.

For an existing completed outcome and validation report:

```powershell
worker-lab --root C:\ACL\lab accept-task ATTEMPT-EXAMPLE `
  --expected-outcome-digest 'sha256:<worker-outcome digest>' `
  --controller trusted-controller --validation-id VALIDATION-example `
  --expected-validation-digest 'sha256:<validation-report digest>'
```

The usual `run-task` path invokes the same acceptance operation automatically
after the protected checks. A CLI exit code of zero means a report was returned;
inspect `status` and `accepted` to determine the task result.

## Explicitly required review

Add `--review-required` to `approve-task-execution` before the worker starts when
the task requires review. That requirement cannot be waived by an acceptance-time
argument. Missing or stale review yields `pending_review` or a blocked report.
An explicit rejection cannot accept the candidate.

After inspecting the candidate, diff and checks, record a decision against their
exact evidence. The run report supplies `outcome_digest`, the validation identity,
and `acceptance.validation_digest` when acceptance reached the review gate:

```powershell
worker-lab --root C:\ACL\lab record-task-review ATTEMPT-EXAMPLE `
  --expected-outcome-digest 'sha256:<worker-outcome digest>' `
  --controller trusted-controller --validation-id VALIDATION-example `
  --expected-validation-digest 'sha256:<validation-report digest>' `
  --review-id REVIEW-example --reviewer operator-reviewer --decision approved

worker-lab --root C:\ACL\lab run-task C:\ACL\operator\task.json `
  --review-id REVIEW-example
```

The review binds the invocation, outcome, candidate, validation and complete
acceptance evidence. Repeating the workflow with that review reuses the stopped
worker and durable checks. It does not resume Pi or start a corrective attempt.
The `--review-id` option is also available on `accept-task`.

## Artifacts, restart and limits

The M05A archive budget remains available as
`run-task --candidate-archive-limit-bytes <bytes>`. The default is 33554432
uncompressed bytes; zero omits the ZIP. An omitted ZIP does not discard candidate
identity, location or the complete retained diff, and does not prevent validation
or acceptance. Omission and its budget are explicit diagnostics. Unreadable,
unsafe or changing candidate state still fails closed.

M06 adds these records beneath the protected `state` directory:

- `operator/task-execution/<attempt-id>.json`: immutable advance consent.
- `task-runs/<attempt-id>/<digest>.json`: workflow reports.
- `task-decisions/<digest>.json`: non-accepting decisions, including pending review.
- `task-reviews/<review-id>.json`: explicit review of exact evidence.
- `task-acceptances/<attempt-id>.json`: immutable successful acceptance.

Existing worker outcomes, candidate artifacts, launch/custody records, validation
intents/results and logs keep their M04/M05 locations. Acceptance records pin
their identities and content digests. Replaying accepted work revalidates the
same live candidate and evidence; changed bytes cannot obtain the old acceptance
as a current successful result. Historical acceptance records remain inspectable.

Controller locks prevent competing workflow execution. Durable intent and outcome
records prevent duplicate worker launches; validation uses a deterministic
identity for the outcome. Interrupted acceptance can reuse the stopped worker and
checks, but unresolved workload or inconsistent records block. These files are
not a multi-record transaction, and recovery does not guess missing proof.

M06 provides one task after preparation and explicit approvals. Dependency
scheduling, accepted-output promotion and the assembled sequential controller
belong to M07–M09. There are no automatic retries, session resume, remote
publication or automatic controller upgrades. Adoption remains manual.

## Verification boundary

Focused fixtures cover passing and failing protected checks, complete evidence,
required review, scope and output obligations, no-op rules, generic lifecycle
bypass rejection, drift, interrupted acceptance and no-duplicate replay. The first
focused run passed 172 tests and exposed one fixture line-ending assumption. The
fixture now fixes its local Git line-ending setting; its isolated rerun passed.
The affected regressions passed 177 tests, with five Windows symlink cases skipped.
The framework suite passed 94 tests and the root suite passed 12 tests. These are
focused and affected checks, not a claim that every repository test was rerun.

The real run used attempt `ATTEMPT-AF6B91775B4C4B10ABA5EC7CBAD467F8` in a
separate target. It corrected one stale assertion string in the framework's
documentation test. The worker returned `completed_claim`; the independent
protected checker ran all five documentation tests and passed; the workflow
returned `accepted`. The exact candidate diff was reviewed and its single test
correction retained in the isolated development target. This did not adopt the
controller into the original checkout.

Replaying the real task with activation disabled returned the identical accepted
report and left launch, custody and validation records unchanged. The report
digest is `sha256:55ab7261b022ea83e7739c26d75662a8aff9018960684c695b0f28e725aaf8aa`.
The checkpoint keeps the real report, replay check, protected checker, candidate
diff and durable judging records separately from fixture results.

M06 meets the first local-development milestone. The operator separately authorized
continuation through M07 and M08; that authorization does not claim either later
step is already implemented or verified, and does not authorize automatic adoption.
