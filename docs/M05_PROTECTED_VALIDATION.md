# M05 — protected validation checks

M05 runs the already-selected protected catalog through the existing sealed-test
runner after M04 records a stopped candidate. The controller owns the commands,
judging inputs and logs. A passing validation report is evidence for M06; it does
not accept, promote or modify the attempt's OUTCOME_RECORDED lifecycle state.
`run-task` still stops at the worker outcome until M06 connects acceptance.

## Explicit execution mode

No suitable isolated validator runner is configured in this installation. The
only M05 execution mode is `operator-approved-local-test:v1`, with resource
exposure `unsandboxed-host-code-execution`. It is disabled without an explicit
approval for the exact candidate, source identities and named catalog commands.
The Windows Job Object controls process lifetime and descendant cleanup; it is
not a filesystem, network or security sandbox. Approved code runs with the host
user's access, including candidate code imported by a checker. A small environment
does not restrict that access. Use only trusted named checks whose host execution
the operator has reviewed. There is no implicit approval, shell command from a
worker, isolation fallback or generic runner plug-in framework.

## Prepare and approve

The existing admitted invocation must already select protected COMMAND tests.
Configure their fixed argument lists in the trusted catalog before admission;
changing that catalog afterward invalidates the sealed identity. The executable
must be an absolute canonical file outside the candidate. A whole argument equal
to `{candidate}` is replaced by the admitted candidate path. No other expansion
or shell interpolation is performed. Every named command must reference at least
one explicitly declared protected checker or judging file. Declare all such
inputs, including trusted helper/data dependencies, outside worker writes.

For example, a trusted Python check can use a fixed catalog argument list:

```json
["C:\\trusted\\python.exe", "-I", "-B", "C:\\ACL\\checks\\check.py", "{candidate}"]
```

After `run-task` has recorded verified worker absence and retained candidate bytes:

```powershell
worker-lab --root C:\ACL\lab approve-validation ATTEMPT-EXAMPLE `
  --expected-outcome-digest 'sha256:<worker-outcome digest>' `
  --controller trusted-controller `
  --protected-file C:\ACL\checks\check.py `
  --acknowledge-unsandboxed-host-code-execution `
  --timeout-seconds 30 --output-limit-bytes 1048576 --cleanup-timeout-seconds 5

worker-lab --root C:\ACL\lab validate-task ATTEMPT-EXAMPLE `
  --expected-outcome-digest 'sha256:<worker-outcome digest>' `
  --controller trusted-controller --validation-id VALIDATION-example
```

Repeat `--protected-file` for additional judging inputs. Limits are configurable
positive integers. The immutable per-attempt approval is under
`state/operator/validation-approvals/<attempt-id>.json`; approval never enables
Pi or changes its configuration. Execution rechecks enabled approval, source,
catalog, executable and declared input bytes before each check and afterward.
A missing, disabled or mismatched approval fails before any launch. The service
methods are `approve_local_validation(...)` and `validate_task(...)`.

## Evidence and restart

The exact worker custody record must show ABSENCE_VERIFIED with zero workload.
Candidate content and Git base must match the recorded worker outcome. Existing
protected authority and test-plan validation run again. Worker edits or a
candidate-authored replacement test cannot alter the authoritative criteria.
The sealed runner invokes the fixed command executor sequentially and stops on
failure. Candidate bytes are rechecked between checks and after the last one.
These are before/after byte checks, not a claim of hostile-code isolation.

The controller uses the existing locks and owned Windows process implementation.
Each validator starts suspended inside its non-inheritable kill-on-close job;
custody is persisted before resume. Timeout, cancellation, excessive output,
nonzero exit or leftover children cause owned cleanup. Logs use a monitored limit,
not a hard storage quota; a burst may exceed the configured bytes before polling.
No unrelated process is terminated. A creation/accounting/persistence uncertainty
cannot fabricate cleanup proof and blocks subsequent worker and validator launches.
No automatic validator recovery or retry is introduced.

Durable records, all outside worker writes:

- `state/validation-intents/<validation-id>.json`: exact request written before launch.
- `state/validation-logs/<validation-id>/<test-id>/`: stdout, stderr, launch intent,
  custody, exit/result, observed process identity and timestamps.
- `state/validation-results/<validation-id>.json`: candidate/outcome/approval/source
  and test-plan digests, selected mode/exposure, per-check evidence and final status.

Status is `passed`, `failed` or `uncertain`; `accepted` is always false. A CLI exit
of zero means a report was returned: inspect its status. Failed checks retain
logs. Repeating the same resolved validation ID returns the report without launch;
a different request cannot reuse it. Missing reports, unreported launches or
inconsistent per-check cleanup evidence block further execution. Lost controllers
leave job lifetime cleanup to Windows, but absence is not assumed from that alone.

## Verification scope

Tests run trusted fixed Python checker fixtures on disposable candidates. The
same checker accepts correct content and rejects broken content; candidate-side
replacement tests do not affect it. Boundary cases include active worker custody,
candidate/catalog/judging drift, no approval, timeout/cancellation with descendants,
minimal environment, output limits, corrupt cleanup records, uncertain creation
and blocking a fresh worker. Real Windows jobs are exercised. M05 does not run a
new live-model campaign. Context stays modular and the selected 128K preference
is unchanged. End-to-end accepted work is M06.
