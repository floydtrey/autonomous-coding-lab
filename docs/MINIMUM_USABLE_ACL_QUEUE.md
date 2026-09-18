# Minimum usable ACL — replacement Spark queue

## Scope correction

This replaces the unfinished S10–S51 queue. Retain S01–S09, any completed work, and the narrow S06 change/no-op rules already agreed. Do not restart completed work, delete useful implementations, or rerun the architecture audit.

The first usable deliverable is a single-command, local-model coding workflow that produces an independently checked, reviewable ACL change. The second deliverable is a sequential two-task workflow that carries accepted changes forward. Neither deliverable requires the full V1 platform.

- **M06: first usable local-development workflow.** A local model can receive one bounded ACL maintenance task, edit a separate target checkout, and return an accepted diff or an honest failure with test evidence. Adoption remains manual.
- **M10: minimum sequential ACL proven.** A user-supplied two-task job runs in order, hands accepted output forward, and finishes or blocks honestly.
- M07–M10 may themselves be attempted using the local-development workflow after M06 passes. Keep the running controller separate from its development target and adopt controller changes manually.

### Basis and limits

This is a deliberate reduction of the supplied September 16, 2026 audit and the earlier S-task queue, not a new repository audit. The source audit inspected `architecture/knowledge-core` at `22e6d9cc5bcfed299e7cc32e1790b17e05ba0d3f`; that is historical context, not an instruction to reset HEAD. Relevant audit sections: §3 acceptance defects; §4 Pi boundary and settlement; T05–T11 integration; §7 first-loop scope.

One explicit trade-off changes the original audit's validator plan: a new isolation-backend implementation is not a prerequisite for this local-development milestone. Reuse an existing suitable isolated runner when available. Otherwise, candidate-executing tests require an explicit operator-approved local-test mode. Local-test mode is unsandboxed: clean environment, a separate checkout, and process cleanup do not stop candidate code from using the account's host permissions. Do not enable that mode silently or describe it as isolation.

## Standing instructions for Spark

Execute only the assigned M-task and stop at its acceptance threshold. Inspect current code relevant to that task; reuse completed work and existing stores, dispatch seams, bounded tools, custody helpers, validators, and local publication helpers. Cross-file changes necessary for the named behavior are in scope. Do not invent separate contract-definition, sealing, registry, or framework tasks for ordinary wiring.

Use one pinned Pi installation, one explicitly selected local model, one prestarted endpoint, one active worker attempt, and the existing exact-file tool authority. Configuration must identify the model/endpoint and required effective settings; no silent fallback. No KC dependency for a self-contained task. Do not introduce direct worker shell access, automatic dependency installation, server auto-loading, remote publishing, or another agent loop.

Work on ACL source in a separate target checkout/worktree. The running controller, its live configuration, authoritative checks, and judging records remain outside the worker's write grants. ACL source files that implement future controller or validator behavior may be edited in the target, but those edits do not replace the running authority. Review and adopt them manually.

Run focused tests and directly affected regressions. Use fixtures for error cases; do not rerun a model qualification campaign at every step. Label real-model/host evidence separately from fixtures. Do not claim unrun tests passed. Stop when the task is satisfied; report changed files, exact tests/results, and remaining limitations. Escalate only a concrete missing capability or materially different design requirement, not normal cross-module wiring. Do not automatically start the next task.

Unless an existing equivalent is present, use the command names below. Prefer extending the existing CLI over creating another CLI framework.

## M01 — One local worker configuration and one adapter protocol

**Replaces:** reduced S17–S20; defines the outcome shape later implemented from S10.

**Depends on:** S08–S09 and existing S04–S06 task admission/packet work.

**Implement**

Use a single trusted configuration for the pinned Pi/adapter, exact local model and endpoint/API, required effective context/settings, and execution deadline. Reuse the S08 identity/readiness checks. Replace singleton assumptions only where needed to admit this configuration; do not build a general profile registry or second-provider integration.

Define the small Python↔Node JSONL messages in code: invocation/attempt identity, task packet, configuration/grant identity, target workspace, budgets; then outcome claim, actual stop reason, session reference when available, errors, and measured usage when available. Missing measurements stay unknown, not fabricated zeros. A claim is one of completed, needs_continuation, blocked, or failed; a claim never means accepted.

**Done when**

The one approved configuration resolves; unknown or changed execution-significant binding is rejected until explicitly reapproved; wrong endpoint model or inadequate required effective context blocks before dispatch. Protocol round trips and malformed-message tests pass. Configured context metadata alone is not treated as verification of server settings. No new context benchmark campaign is required.

## M02 — Finish and connect the Pi adapter

**Replaces:** S10–S12 and S21–S24.

**Depends on:** M01.

**Implement**

Reuse S09's bounded tools rather than recreating them. Connect the Node Pi adapter to the existing `BoundProviderExecutor`/Worker Lab dispatch path. Supply only admitted tools and context; disable unapproved project/global extensions, skills, templates, default tools, and automatic resource discovery. Use the exact configured model without fallback.

Implement structured outcome reporting. Wait for authoritative settlement rather than treating an intermediate agent-end event or prompt acknowledgement as completion. Freeze mutations once a terminal claim is registered; serialize tool mutation/outcome handling as needed so an in-flight write cannot complete after the candidate is frozen. Missing claim, malformed output, settled error, and unexpected EOF are not success.

**Done when**

An invocation traverses the real adapter path. Focused tests prove allowed read/write, denied path and stale-write rejection, ignored unapproved resource loading, correct settlement handling, and deterministic mixed outcome/write handling. Existing injected-provider tests still work. No production activation is assumed merely because the adapter exists.

**Not included:** session reopen, forced compaction qualification, Pydantic retirement, a second transport.

## M03 — Supervise one explicitly enabled attempt

**Replaces:** S13 and S25–S27; the attempt-level launch-intent portion of S40.

**Depends on:** M02.

**Implement**

Extend the existing launch/custody helpers with an operator activation check, minimal environment, durable launch intent before process creation, owned process identity, deadline, cancellation, and child cleanup. Account for the launch-to-custody-record window. Use existing Windows lifetime-management helpers; do not build a new sandbox.

No launch while activation is disabled. Never adopt or terminate a process based only on its name or port. If absence cannot be established, preserve uncertainty and prevent validation/acceptance.

**Done when**

Disabled execution starts nothing. An enabled bounded attempt starts through Worker Lab. Capture one real intended-host allowed edit/structured outcome with an independent diff/check, plus a real cancellation check. These are scoped compatibility evidence, not final ACL task acceptance. Timeout/cancel stops its owned workload, while an unrelated test process remains untouched. Absence or uncertainty is recorded accurately. Use fixtures for other process error cases. If the real scoped edit or owned-workload cleanup fails, fix that concrete failure before advancing; do not build the remaining loop on mocked compatibility.

## M04 — Persist every outcome and expose `run-task`

**Replaces:** S28–S30 and the single-task entrypoint portion of S45.

**Depends on:** M03.

**Implement**

Use the existing attempt/invocation stores to persist normalized outcomes for completed claims, incomplete/protocol results, blocks, provider failures, timeouts, cancellation, and uncertainty. Include references to configuration/grant, observed stop state, logs, candidate/diff, and available usage. Preserve dirty failed candidates and diagnostics separately; do not require a clean interrupted workspace merely to record a failure.

Add the minimal `run-task <task-file>` entrypoint through the existing CLI/service. At this stage it returns a worker outcome, explicitly pending independent acceptance where appropriate—not a successful task verdict. Save useful error/test context for a manually requested fresh attempt. No automatic retries or Pi-session resume.

**Done when**

Success-claim, provider exception, truncated output, timeout, and cancellation cases all leave an appropriate durable record rather than a stranded RUNNING/DISPATCHING state. Reusing a terminal attempt ID does not launch again. Restart with unprovable process state blocks rather than guessing. Failed diffs remain inspectable but cannot become the next accepted base.

## M05 — Run one protected set of validation checks

**Replaces:** S34–S35; defers new isolation-backend engineering from S36–S37.

**Depends on:** M03–M04.

**Implement**

Reuse the existing protected check catalog/runner. Select checks and fixed command arguments from trusted controller configuration, never worker-supplied shell text. Keep authoritative check definitions, judging data, and logs outside worker writes. Candidate-authored tests may supplement but cannot replace the authoritative criteria.

Require verified worker absence and an exact candidate identity before running checks. Capture validator identity, stdout/stderr, exit/result, timeout, and candidate digest; use a minimal environment and clean up owned validator children. Check that candidate source bytes remain the ones being evaluated.

Use an already-available suitable isolated runner. If none is available, permit only an explicitly operator-approved local-test mode for named commands. Document that mode as unsandboxed host code execution; do not silently enable it. Do not create a generic runner plug-in platform or OS sandbox.

**Done when**

The same protected check passes correct code and rejects a broken candidate, with durable logs. A still-active worker causes zero validator launches. Worker edits cannot replace the authoritative checks. Timeout leaves no owned validator children. The selected execution mode and its resource exposure are explicit.

## M05A — Fix the four M01–M05 audit findings

**Status:** complete in the isolated development target (September 17, 2026).

**Verification:** 644 Worker Lab tests passed; seven Windows symlink cases skipped.
All 12 Node adapter tests and 12 root source/inventory tests passed. The broader
framework suite passed 93 tests with the previously recorded reconstruction-wording
assertion still failing. Each of the four audit reproductions now has a lasting
regression, including the >32 MiB candidate reaching approved checks without a ZIP.
Portable source identities were refreshed. No original-checkout adoption,
activation, live-model request, runtime restart or M06 work was performed.

**Added by operator request:** September 17, 2026, after the M01–M05 audit and temporary-file cleanup. All four findings remain in the active implementation. Removed snapshots, generated test repositories and one-off scripts were not the authoritative files to fix.

**Depends on:** M01–M05. **Required before:** M06.

**Goal**

Close the four confirmed audit defects in the existing worker/supervision/outcome path so the next single-task milestone has protected execution dependencies, trustworthy review evidence, configurable supported settings and no accidental repository-size ceiling.

**Implement**

1. **Protect interpreter installations and startup inputs (P1, M03).** Extend the existing path/authority checks to keep the configured Node and Python installations and execution-significant startup inputs outside worker-write surfaces. Resolve and reject overlapping/substituted locations before launch. Cover Python virtual-environment startup files such as `.pth` and `sitecustomize`; checking only that an executable path is absolute is insufficient. Reuse the existing trusted host settings and path guards. Do not replace this fix with filename bans or a new OS sandbox.

2. **Bind the retained diff to the admitted candidate (P2, M04).** Reuse the existing sanitized Git helper/environment for diagnostic diff capture. Ambient `GIT_DIR`, `GIT_WORK_TREE` and related redirection must not select another repository. The retained diff, archive when available, and candidate digest must refer to the same admitted workspace.

3. **Make supported single-worker settings configurable (P2, M01).** Treat the one protected configuration and separately trusted pin as the source of supported execution settings. Allow explicit changes to output budget, provider/attempt/tool deadlines, supported local endpoint details, and runtime/model/version pins without editing authority code. Apply schema, range and supported-transport checks; keep protocol, tool, authorization and no-fallback invariants fixed. Changed execution-significant settings invalidate old bindings/activation and require fresh approval and matching readiness/compatibility evidence. Keep 131072 as the current preferred context, while retaining custom context and budget options. No multi-profile registry, second provider or automatic runtime upgrade/load is added.

4. **Separate candidate identity from optional full-archive capture (P2, M04/M05).** Make the archive budget explicit and configurable. An oversized diagnostic ZIP must not discard an otherwise verifiable candidate identity, mislabel completed work as provider failure, or prevent protected validation. Retain the exact candidate identity, candidate location and a trustworthy reviewable diff, including authorized new-file evidence when needed. Record archive omission/limits as diagnostics. Continue rejecting candidate drift, unreadable/unsafe candidate state and unproven worker absence; archive optionality must not weaken those gates.

**Done when**

- A candidate-local interpreter/startup-input fixture is rejected before worker/bridge execution; its granted `.pth` marker does not execute. A correctly separated configured interpreter still works with the existing admitted file tools.
- With inherited Git repository variables pointing to a different valid repository, a one-file edit still produces the correct nonempty retained candidate diff. Its evidence matches the actual candidate bytes; no redirection is accepted.
- Explicitly re-pinned supported output/deadline/endpoint/runtime settings resolve through the existing configuration/binding/protocol path without source changes. Stale pins/bindings/activation, unsupported transport/authority changes, wrong model/runtime observations and inadequate effective context still reject. Custom context choices work and the selected 128K preference is preserved.
- A completed authorized edit in a workspace containing an untouched asset larger than 32 MiB retains exact candidate identity and useful review evidence when the full archive exceeds its configured budget. It can reach the approved protected checks; archive limitation is reported separately from worker failure. Candidate drift still rejects.
- Focused regression tests cover each reproduced finding and directly affected Python/Node tests pass. Convert the useful audit reproductions into lasting regressions; remove regenerated scratch environments after preserving results. Refresh source-byte identities only for actual source changes and report exact checks/results.

**Boundaries**

Fix the active `pi_supervision.py`, `pi_worker.py`, `run_task.py` paths and directly affected helpers/contracts/tests as needed. Do not attempt to fix deleted staging copies or generated fixture repositories. Keep the original/running controller separate from the development target and adopt changes manually.

This is four bounded corrections, not another architecture audit or new runner/registry/packaging framework. Use deterministic fixtures for these failures; no new model qualification campaign is required. Do not silently enable worker execution or unsandboxed validators. Acceptance, advance consent for named checks in the single-command workflow, promotion, retries and sequential orchestration remain assigned to their existing later tasks. Stop after M05A; do not begin M06 automatically.

## M06 — Gate acceptance and deliver a usable single-task workflow

**Replaces:** S31–S33; completes the single-task entrypoint introduced in M04.

**Depends on:** M04–M05 and completed M05A audit corrections.

**Status:** complete in the isolated development target. See
[M06 task workflow](M06_TASK_WORKFLOW.md) for the implemented advance-consent,
`run-task`, `accept-task` and exact-review interfaces and separate fixture/real
evidence. A real bounded maintenance task returned an independently accepted diff;
its exact reviewed test correction was retained only in the development target.
Replay with activation disabled reused the identical report and execution records.
The original checkout has not adopted the controller changes. The operator
separately authorized continuation through M07 and M08.

**Implement**

Add one evidence-gated accept operation and route `run-task` through it. Require verified worker absence, a valid completed claim, exact unchanged candidate identity, allowed-change/required-change/no-op rules from S06, required independent checks, and any explicitly required review. A required review that has not occurred yields pending-review/block, not acceptance.

Prevent generic lifecycle transitions from producing PASSED/accepted state. Bind acceptance to the exact evidence and make repeating it idempotent. Return accepted/failed/blocked/pending-review status, an inspectable diff, test evidence, and the candidate location. Do not promote changes into the running controller or user's main checkout.

**Done when**

`run-task` executes one real, small ACL maintenance task with the configured local model in a separate target checkout. Correct work produces an independently accepted, reviewable diff; a failed check cannot produce acceptance. Missing evidence, candidate drift, out-of-scope edits, and the former generic PASSED bypass all reject.

**USABILITY CHECKPOINT**

Local models can now attempt bounded ACL development tasks. You review/apply accepted changes manually and request a fresh attempt with diagnostics when needed. This is sufficient to begin using local models to build M07–M10; model reliability remains something to assess from actual results.

## M07 — One durable job record and next-task selector

**Status:** implemented in the isolated development target. The 39 focused job/plan
checks pass. See [M07 durable jobs](M07_DURABLE_JOBS.md). Job execution remains
disabled until M09 connects the reservation deadline to process supervision.

**Replaces:** S38–S40, excluding launch intent already handled in M03.

**Depends on:** existing S02–S04 plan/admission work and M04; scheduled after M06 so it can be developed through ACL.

**Implement**

Reuse the admitted plan and existing record stores. Add one job aggregate containing plan revision, task states/dependencies, attempt references, accepted artifact references, and blockers/final state. Reuse existing dependency validation rather than inventing another plan schema.

Choose one eligible task at a time, only after every prerequisite is accepted. Use one controller/job lock and durable decision references. Existing per-attempt launch intent remains the source for worker-launch reconciliation. Do not imply atomic replacement of one record makes all related files transactional; block ambiguous cross-record state.

**Done when**

A two-task plan selects A first and B only after accepted A. Failed/blocked A suppresses B. Restart retains the plan and outcomes. A competing controller cannot launch the same job task. No database service, event bus, append-only event-sourcing platform, or parallel scheduling is added.

## M08 — Promote accepted local output and pass it to the next task

**Status:** complete in the isolated development target. See
[M08 accepted snapshots](M08_ACCEPTED_SNAPSHOTS.md) for promotion, durable lineage,
exact downstream preparation and remaining limits. Before the final two narrow fixes, broad affected regressions passed 674 tests with seven Windows symlink skips. After those fixes, 76 focused job/snapshot/input tests and 57 validator/acceptance/workflow tests passed. Final root tests passed 12; Node adapter tests passed 12. This is staged focused and affected verification, not a fresh full-repository test claim.
No model was launched for M08. The operator subsequently authorized integration
of the accepted work into `architecture/knowledge-core` and publication of that
development branch. M09 remains a separate assignment.

**Replaces:** S41–S43.

**Depends on:** M06–M07.

**Implement**

Reuse existing workspace/local-publication helpers to make a controller-owned clean snapshot or local commit from an accepted candidate. Recheck candidate identity before promotion. Record acceptance→snapshot→next-task lineage and prepare B from A's accepted snapshot, never the original template or a rejected dirty candidate.

Make promotion idempotent using acceptance/artifact identity. On restart, recognize a completed promotion or conservatively block if its proof is missing. An accepted no-op can reuse the existing base; it need not fabricate a change or empty commit.

**Done when**

B reads A's accepted change. Rejected A is never used. Interrupting promotion does not cause duplicate or unverified handoff. Workers get no commit/push authority, nothing is published remotely, and the running ACL instance is not upgraded automatically.

## M09 — Assemble the sequential controller CLI

**Replaces:** S44–S48, reusing rather than duplicating M04/M06 single-task execution.

**Depends on:** M07–M08 and the completed single-task workflow.

Implementation is intentionally split into M09A (authorization/budgets/shared deadline/telemetry), M09B (sequential run + status), M09C (stop + reconcile), and M09D (assembled acceptance/closure). See [M09A execution foundations](M09A_JOB_EXECUTION_FOUNDATIONS.md). M09A does not implement the sequential loop.

**Implement**

Add/finish `run <plan-file>`, `status <job-id>`, `stop <job-id>`, and `reconcile <job-id>`. Use the existing single-task routine inside this sequence:

`select → prepare/authorize → run-task → accept/block → promote → advance`

Allow one active worker. Failure, missing completion, exhausted deadline, or unresolved review stops/blocks advancement. No automatic corrective attempt, model switching, session continuation, or new compactor.

Reconciliation may finish provable durable bookkeeping and permit a later explicit run to continue with unstarted tasks. It must not guess that an uncertain worker finished or silently launch a replacement. Completion requires all required tasks accepted, no active/uncertain attempt, and final artifact identity matching accepted lineage.

**Done when**

A single command runs a deterministic two-task fixture in order. Status shows evidence and blockers; stop affects only the owned attempt. Restart/reconcile does not rerun accepted tasks. Failed validation suppresses the dependent task and objective completion. CLI/service integration tests reuse the same execution and acceptance path as `run-task`.

## M10 — Prove the minimum workflow on actual ACL work

**Replaces:** reduced S16 and S49–S51.

**Depends on:** M09.

**Implement/run**

Use one real, already-needed ACL backlog improvement that can be expressed as two small dependent tasks in a separate target checkout: a production change followed by a caller/test/documentation change that genuinely consumes it. Choose actual paths and protected checks from the current repository at execution time; do not invent a feature merely for a demo. State expected behavior/checks before the worker starts.

Run the real local model through the assembled controller. Capture exact command/config identity, changed artifacts, independent check results, acceptance lineage, and final status. Demonstrate B consumes accepted A.

Run one negative case through the same assembled path using an intentionally failing protected check. The failure may be injected deterministically; do not burn model runs attempting to make the model misbehave. Label real execution and fixtures honestly. Check that status/reconcile does not duplicate accepted work.

**Done when**

A real two-task ACL improvement produces inspectable accepted output; the negative case blocks its dependent task and cannot complete the objective. A short saved usage note gives the actual commands used for run-task/run/status/stop/reconcile and explains manual adoption of controller changes. Do not claim the former full S16 session/compaction qualification passed when those cases were deferred.

**STOP LINE**

The minimum usable sequential ACL is complete. Move further ACL development into bounded local-worker tasks. Add capabilities in response to demonstrated problems, not because an older checklist contains them.

## Explicitly deferred from the old queue

| Old work | Minimum-scope decision |
|---|---|
| S14–S15 exact session reopen and forced compaction qualification | Deferred. Pi may use its existing inner context handling. ACL blocks an unfinished attempt; a person may request a fresh bounded attempt. |
| S16 formal spike seal | Replaced by real execution evidence in M03/M06/M10. No separate qualification dossier or claim covering deferred features. |
| S17–S19 complete registry / multiple-profile extensibility | One explicit trusted configuration only. Identity/readiness checks remain. |
| S36–S37 new isolation backend | No new backend engineering in this milestone. Reuse an existing suitable runner, or require explicit unsandboxed local-test approval as described above. |
| S30/S40/S43/S47 broad restart automation | Keep no-duplicate and evidence-consistency protections. Block ambiguous state instead of building full automatic recovery. |
| S49 disposable-only target | Replace with actual, bounded ACL maintenance work. Disposable scratch checks remain useful tests, not the final value demonstration. |
| KC, automatic server loading, model comparisons, Foreman planning, automatic retries, GUI, packaging platform | Outside this replacement queue. |

## Initial instruction to Spark

Read this replacement queue and preserve completed S01–S09 work. Execute M01 only. Inspect the relevant current implementation, make the smallest necessary configuration/protocol change, run the focused acceptance tests, report results, and stop. Do not create another roadmap or begin M02 automatically.
