# M04 — durable worker outcomes and `run-task`

M04 adds one explicitly invoked task operation to the existing Worker Lab service
and CLI. It consumes an already prepared and authorized invocation, runs the
selected Pi worker under M03 supervision, and returns a durable worker outcome.
It never reports task acceptance. Context remains configurable; the operator's
current preference is 131072 tokens.

## Command and protected inputs

```powershell
worker-lab --root C:\ACL\lab run-task C:\ACL\operator\task.json
```

The operator-owned task file is a small reference to existing sealed authority:

```json
{
  "schema_version": "worker-lab-run-task:v1",
  "invocation_id": "INVOCATION-EXAMPLE",
  "expected_identity_digest": "sha256:<64 lowercase hex characters>",
  "controller_identity": "trusted-controller",
  "workspace_root": "C:\\ACL\\attempt-workspaces"
}
```

Use the existing create-attempt, prepare-workspace, Controller Task Packet,
prepare-invocation and authorize-invocation service operations first. The task
file does not add scope, commands, a provider choice, or executable paths. It must
be outside the admitted worker workspace. M04 does not enable job-task execution;
its existing dependency/budget authorization gate remains in place until the
later job-controller tasks.

Local activation remains a separate explicit operator action via
`set_pi_activation`. `run-task` never enables it. In the protected data root,
`state/operator/pi-host.json` supplies canonical absolute host paths:

```json
{
  "schema_version": "acl-pi-host:v1",
  "node": "C:\\trusted\\node.exe",
  "python": "C:\\trusted\\python.exe",
  "framework_root": "C:\\trusted\\ACL\\components\\autonomous-worker-framework",
  "pi_installation": "C:\\trusted\\ACL\\tools\\pi-compatibility",
  "agent_dir": "C:\\ACL\\lab\\state\\pi-agent"
}
```

The framework path must be this installation's framework. M03 validates the
remaining paths, source identities, model configuration and activation. The
selected model/server must already be ready. The command neither starts Ollama
nor loads a model. Operators supply these trusted host settings; worker output
cannot choose them. The CLI's successful command exit means the outcome was
recorded; inspect `status`, `accepted` and `acceptance` for its meaning.

## Outcome records

The existing AttemptStore retains immutable
`state/worker-outcomes/<attempt-id>.json` records with schema
`worker-lab-worker-outcome:v1`. Each identifies the invocation, configuration,
sealed grant, Provider Binding and task-file digest. It includes observed stop
state, custody, worker claim, available usage, diagnostics and artifact paths.
Unknown usage stays null.

Statuses are `completed_claim`, `needs_continuation`, `blocked`, `protocol_error`,
`provider_failed`, `timed_out`, `cancelled`, `uncertain`, and `interrupted`.
Every outcome has `accepted: false`. A completed claim has
`acceptance: pending_independent_acceptance`; other outcomes are not accepted.

The existing Pi outcome callback durably retains the parsed claim and stops the
AWF call before its validation stage. M04 does not invoke protected validators or
acceptance. This keeps the M05/M06 boundary explicit while reusing the existing
protected dispatch preflight, prompt construction, tools and supervisor.

After verified absence, candidate identity and a diagnostic Git patch are retained
under `state/worker-artifacts/<attempt-id>/`. M05A binds diff capture to the admitted
workspace with the shared sanitized Git environment. The patch includes tracked
changes and new regular files, including ignored, empty and binary files, without
changing the candidate index. Capture checks content identity before and after;
drift, unsafe paths or unreadable state still fail.

The optional full ZIP has a default **33554432-byte (32 MiB) uncompressed-content
budget**, configurable by `run-task --candidate-archive-limit-bytes <bytes>` or the
service's `candidate_archive_limit_bytes` argument. Zero omits the ZIP. The operator
choice is recorded in the immutable task intent and reused after interruption.
Over-budget capture retains the exact content digest, candidate workspace and
complete patch; `candidate.archive` is null, `archive_capture` records status,
budget and observed content bytes, and `CANDIDATE_ARCHIVE_OMITTED` is a diagnostic.
It does not turn a completed claim into provider failure or prevent M05's explicitly
approved checks. An existing terminal outcome is returned unchanged even if a
later call supplies a different archive budget. If capture otherwise fails, the
outcome still records the error and retained workspace location.
No clean-workspace requirement is imposed on failure recording. An uncertain
workload is not read as a stable candidate: its workspace and logs remain, but
no candidate snapshot or validation is attempted.

Process logs remain at their M03 paths and are referenced by the outcome. Dirty
failed artifacts are diagnostics, explicitly not an accepted base. Nothing is
committed, promoted or copied into the controller checkout.

## Lifecycle and restart

A controller lock spans the complete operation. An immutable run-task intent is
written before changing lifecycle state; M03's separate launch intent still
precedes process creation. A normalized outcome is written before invocation and
attempt finalization. Both then enter `OUTCOME_RECORDED`, a distinct state that
cannot pass through the existing candidate/acceptance path. The invocation's
result digest refers to the worker-outcome schema in this state, not Result V3/V4;
the attempt's cleanup reference binds the same outcome digest.

The files are not a multi-record transaction. Repeating the same task file after
a durable outcome exists repairs only missing lifecycle bookkeeping and returns
the same record. It never launches again, even if activation or runtime settings
have since changed. Different task identity cannot reuse that attempt. If a parsed worker result was
saved before the normalized outcome write, recovery correlates it to the retained
request and preserves its available usage, while still recording interruption.

An intent without an outcome after restart never resumes. Verified absence yields
an interrupted observation; missing/unprovable custody yields uncertainty. Dirty
workspace contents do not prevent recording either result. Unresolved earlier
run-task or launch evidence blocks replacement execution. No process is adopted
or killed by name/port, and no failed snapshot becomes a subsequent base.

A person may request a fresh authorized attempt from a clean trusted base using
the retained error/claim/log/diff information. There is no automatic retry or Pi
session resume. Generic lifecycle commands cannot fabricate OUTCOME_RECORDED;
the stores require its durable matching outcome.

## Verification boundary

Tests cover normalized success/incomplete/error/timeout/cancel/protocol outcomes,
blocked activation, dirty and untracked file preservation, duplicate execution,
identity mismatch, immutable outcomes, interrupted lifecycle writes, uncertain
restart and replacement blocking. Installed Pi SDK tests with deterministic HTTP
responses run inside the real Windows supervisor and assert that M04 launches no
validator. They include successful settlement, a provider error, and an actually
truncated child output stream. These are SDK/host fixtures; M03's real-model edit
and cancellation evidence remain separately scoped evidence.

M05 protected validation, M06 acceptance and later scheduling/promotion remain
out of scope. The normal older dispatch API still requires an explicitly injected
runner; the new `run-task` operation supplies only the selected Pi supervisor.

Final M04 verification: 541 Worker Lab tests passed, seven environment-dependent
symlink tests skipped, 12 root source/inventory tests passed, and all portable
source identities matched. The incremental patch applies to the completed M03 tree.
