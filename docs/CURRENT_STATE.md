# Current State

**Branch:** `architecture/knowledge-core`  
**Reconstruction status:** Tasks 1–9 complete; deterministic reconstruction accepted  
**Execution authority:** `DISABLED`

`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` is the reconstruction acceptance record and post-reconstruction boundary. Reconstruction acceptance did not include actual provider/model execution or capability qualification.

## Knowledge Core routing

KC status is maintained separately in [its current state](architecture/knowledge-core/CURRENT_STATE.md), followed by [architecture](architecture/knowledge-core/ARCHITECTURE.md) and [operations/evidence](architecture/knowledge-core/OPERATIONS.md). Historical KC documents are archived under `docs/architecture/knowledge-core/legacy/`; their old next-task prose does not govern current work. KC acceptance does not change the ACL execution status above.

## Current runtime architecture

ACL has one intended V1 architecture with the following implemented execution and authority foundations:

- Worker Lab is the authority plane.
- S05b adds [V1 output acceptance](OUTPUT_ACCEPTANCE_V1.md): explicit permission, required changes/files/evidence, and no-op permission. New preparation uses Invocation V4 and dispatch task V3; Result V4 supports independently checked no-op candidates. Existing authority and job execution gates remain in place.
- Controller Task Packet V1 carries user request plus governed Knowledge Core evidence as informational context. S05 adds V2 with an explicit no-KC context choice for self-contained tasks, preserving V1 packet bytes and digests.
- Invocation/Result V3 binds logical target/workspace identity, exact protected scope/tests, source identity, runtime requirement, and exact Provider Binding before dispatch.
- Autonomous Worker Framework dispatch is provider-neutral and requires an explicitly supplied bound provider executor.
- Provider installation observation and controlled capability qualification are separate from source identity and separate again from authorization.
- Pydantic AI + Ollama is the first adapter implementation; implementation does not establish provider capability qualification.
- Windows Job Objects are the first containment backend, not a universal ACL identity requirement.
- Candidate/result acceptance independently checks custody, authorized changed paths, protected tests, and Git workspace evidence when the selected task capability is Git-backed.

There is no active compatibility path for the removed commissioning/V2 runtime.

The sequential controller does **not** exist yet. Controller Task Packet V1 and the preparation/acceptance APIs are foundations for that controller, not an implemented orchestration loop. S02–S04 now add an immutable V1 job plan, deterministic dependency-cycle validation, and explicit job-task admission through V3 preparation without creating curriculum exercises. See [Job Plan V1](JOB_PLAN_V1.md). These changes stop at PREPARED; job execution authorization remains blocked pending dependency-readiness and budget-enforcement gates.

The next implementation milestone remains the sequential controller: prepare one bounded task, dispatch through the existing contracts, perform controller-side validation, and record the outcome before proceeding.

Initial V1 worker authority is exact-file read/write scope. The controller side uses Worker Lab's protected tests and independent acceptance checks; workers receive no shell or test-process authority. Authentication is provider-neutral and limited to operator-approved credentials for the selected transport. No provider or Pi integration is declared qualified here.

## Portable source identity V2

`config/portable-source-manifest.json` uses `acl-portable-source-manifest:v2` and identifies `acl-runtime-source:v2`.

It binds source/component bytes only. It intentionally excludes operating system/CPU identity, Python executable/path requirements, provider/model installation state, capability qualification, local activation, and task authorization. `tools/verify_portable_source.py` verifies the same source closure on a compatible host without claiming that host/provider is qualified or execution-ready.

Current component identities verified against `config/portable-source-manifest.json` are:

- Autonomous Worker Framework: 13-file closure at `sha256:7ff5e9a652ac46e65d7f948dd9b75f9bd1b30413a5d27ddf47c328e1ec1f28f6`;
- Local Model Bench: 10-file production tree at `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc`;
- Worker Lab: 45-file production tree at `sha256:1313ddce09ec5690e04f73b94c3f6298f081e11e8b5fc3abfcaaa620951358fd`;

## Provider qualification separation

Provider installation observation V2 records installed host/provider/model facts only. Controlled capability qualification V2 records tested tool/context capability only. Neither record contains execution authority or claims execution readiness.

Provider Binding seals the exact capability-qualification digest, model identity, adapter/tool surface, runtime requirement, and runtime settings before Worker Lab authorization. Qualification evidence never activates ACL.

There is no default capability-probe runner. The older dispatch command has no implicit runner; M04 adds the explicitly activated Pi-only run-task operation described below.

## Task 9 deterministic reconstruction acceptance

Task 9 accepted its historical reconstruction checkpoint only after the complete deterministic gate proved all required boundaries together. The following records that gate, not a fresh full-suite acceptance of the present tree:

- complete Autonomous Worker Framework suite passes;
- complete Worker Lab suite passes, with only the known environment-dependent symlink skip where symlink creation is unavailable;
- root portable-source/inventory tests pass;
- portable source identity V2 reports every component `MATCH` against exact committed bytes;
- source identity contains no execution authority, host requirements, Python executable, provider runtime, or execution-readiness claim;
- current operating documentation describes one architecture;
- active production/config/current operating docs contain no obsolete commissioning/runtime identity references;
- repository-specific contracts that remain are bounded Git-workspace mechanics/evidence rather than ACL logical system identity;
- protected catalog pytest paths resolve to existing test files;
- provider capability qualification still requires an explicitly injected probe runner;
- no implicit provider/model/runner fallback exists;
- the exact checkpoint contains no Task 9 temporary validation machinery;
- execution remains `DISABLED`;
- no actual provider/model request or real capability qualification occurred during reconstruction.

Task 9 did not modify production runtime behavior. Later Worker Lab changes updated its source identity; the current digest above comes from the present manifest and verifier, not the Task 8/9 checkpoint. Source matching is separate from controller completion and host/provider qualification.

## Post-reconstruction boundary

Reconstruction is complete, but ACL is **not activated**.

The next implementation milestone is the missing sequential controller with exact-file worker scope and controller-side validation. Actual host/provider capability qualification and a supervised disposable vertical slice require separate explicit user authorization. Persistent execution, autonomous retry loops, GUI expansion, Linux containment work, or broader runtime expansion remain separate later decisions.

Benchmark Lab remains a separate advisory system. Benchmark results may inform which model/configuration to qualify for ACL roles, but do not authorize ACL execution or alter Provider Binding/Worker Lab policy by themselves.

## M01 — local Pi configuration and protocol

[M01](M01_PI_CONTRACT.md) adds one pinned Pi/local-model configuration and a
versioned Python/Node wire contract, with no provider launch or dispatch runner.
The initial context selection is 128K; 4K, 8K, 32K, 128K and 256K are explicit
configuration options. Every selection has its own configuration/settings digest.
S09's 4K file-tool evidence is not 128K capability qualification. Existing
production qualification/authorization gates remain closed to an unqualified Pi
worker. The M02 integration update is recorded below.

## M02 — Pi adapter connected; activation remains disabled

The supplied [minimum usable ACL queue](MINIMUM_USABLE_ACL_QUEUE.md) supersedes
unfinished S10–S51 work. Codex is the acting implementation agent.
[M02](M02_PI_ADAPTER.md) connects the pinned Pi adapter to the existing Worker Lab
and BoundProviderExecutor dispatch path, reuses S09's file tools, records structured
claims, waits for agent_settled and serializes file/outcome operations to freeze
mutations at a terminal claim. No second provider registry or agent loop was added.

A small Pi readiness branch reuses Provider Binding and the selected configuration;
it checks exact model/version/endpoint/server-context observations and does not
claim the deferred full S16 qualification. Tests use the installed Pi SDK with
deterministic HTTP responses, not real-model execution. Production has no default
Pi launcher: M03 must supply activation, durable custody and verified cleanup.
The completed M03 supervision and scoped real-model evidence are recorded below.

## M03 — supervised attempt and scoped real-model checks complete

[M03 supervision](M03_PI_SUPERVISION.md) adds explicit local activation, durable
launch intent, atomic Windows job membership at process creation, suspended launch
until custody is recorded, minimal environment, deadline/cancellation and verified
owned-workload cleanup. It reuses the existing custody records and M02 dispatch.
Unresolved launch evidence blocks further launch and cannot reach candidate checks.

Focused and affected regressions pass (168 Python tests and 12 Node tests),
including installed-SDK fixture dispatch and real Windows lifetime/descendant/
controller-crash checks. The operator authorized model loading and real checks.
The first real edit attempt changed only the allowed file but did not complete:
the OpenAI endpoint reset preloaded 128K context to the server's 4K default, and
the initial four-request budget was exhausted. Owned absence was verified.
The adapter now rejects context drift before tools and preserves transport errors;
request/tool budgets are configurable, with eight of each selected for this task.
Raw outcome validation now precedes Pi's argument coercion. The operator authorized
restarting Ollama and retaining 128K; the user environment and server now use 131072.
The final real edit passed the exact-content/diff check with a completed settled
outcome. Real cancellation also passed. Both verified zero owned workload and
preserved an unrelated process. Earlier failed attempts remain inspectable.
This is scoped compatibility evidence, not final task acceptance or full-context
qualification. Probe activation was disabled afterward. The M04 implementation is recorded below;
the running checkout has not been upgraded or implicitly activated.

## M04 — durable worker outcomes and single-task entrypoint

[M04](M04_WORKER_OUTCOMES.md) adds `run-task <task-file>` through the existing
service and CLI. It references an already authorized invocation, consumes explicit
protected Pi host settings, and uses the M03 supervisor. The worker outcome is
saved before attempt/invocation lifecycle finalization. Every returned outcome
has `accepted: false`; a completed claim remains pending independent acceptance.
The operation stops at the Pi outcome callback before any validator runs.

Completed, incomplete, blocked, protocol, provider-error, timeout, cancellation and
uncertain results are durable. Stopped dirty candidates, including untracked
files, are retained separately from accepted output. Repeating a terminal task
returns its outcome without launching; interrupted cross-record finalization is
repaired from the immutable record. Unresolved earlier stop evidence blocks a
replacement. Recovery never resumes Pi or assumes an unchanged clean workspace.

Attempt and invocation OUTCOME_RECORDED states bind the separate worker-outcome
schema, not an accepted Result. The generic lifecycle command cannot create that
state without the protected operation. The M05 validation implementation is recorded
below. Context remains configurable and the current 128K preference is unchanged.


## M05 — protected checks with explicit local execution approval

[M05](M05_PROTECTED_VALIDATION.md) reuses the sealed catalog and test runner with
fixed commands under owned Windows process lifetime control. Checks require exact
candidate/source/authority identity and verified worker absence. Executables and
declared judging inputs are pinned outside worker writes; logs and custody are
retained in protected state. Candidate and judging bytes are checked again after
execution. Timeout/cancellation cleans owned descendants; missing cleanup proof
blocks new validators and workers, including after restart.

No suitable isolated validator runner is configured. The only supported mode is
explicitly operator-approved named local testing, documented as unsandboxed host
code execution. It is never silently enabled. Reports remain `accepted: false`;
The M06 implementation below connects these observations to the single-task flow.
The original checkout and selected 128K model configuration remain unchanged.


## M05A — audit corrections before M06

The operator requested M05A after the M01–M05 audit and temporary-file cleanup.
The [M05A queue step](MINIMUM_USABLE_ACL_QUEUE.md#m05a--fix-the-four-m01m05-audit-findings)
addresses four active implementation defects: interpreter/startup-input write
separation, sanitized candidate diff capture, configurable supported worker
settings, and candidate identity independent of the full-archive size limit.
The affected implementation and audit reproductions were retained during cleanup.
M05A implements those corrections in the separate development target. Runtime
locations and Python startup inputs are checked before launch; the file bridge
skips site startup. Diff capture uses the shared sanitized Git environment and
includes new regular files. Supported settings now come from the strictly
validated, explicitly re-pinned protected configuration. Optional ZIP capture
has an operator-selected budget independent of candidate identity and validation.
Verification passed: 644 Worker Lab tests (seven unavailable symlink cases skipped),
12 Node adapter tests and 12 root source/inventory tests. The broader framework
suite retains its pre-existing reconstruction-wording assertion failure, with
93 tests passing. Updated portable source identities match. M05A is complete;
M06 was subsequently authorized and its implementation is recorded below. M05A
left the running checkout, activation and selected 128K setting unchanged.

## M06 — verified single-task local development checkpoint

[M06](M06_TASK_WORKFLOW.md) extends the public `run-task` command through the
existing supervised worker, protected checks and evidence-gated acceptance path.
Advance consent binds the exact task, invocation, named unsandboxed local checks,
source identity, judging bytes and any required review. Missing consent launches
nothing. The task file is rechecked at the worker boundary.

Acceptance requires successful worker custody, exact candidate and retained diff,
complete passing validator evidence, explicit output obligations and any required
review. Ignored/new files and both rename paths are included in scope inspection.
Generic lifecycle transitions cannot produce PASSED. Successful acceptance is an
immutable separate record; worker outcomes and validation reports remain
non-accepting observations and preserve OUTCOME_RECORDED lifecycle state.

The workflow reports accepted, failed, blocked or pending_review with candidate,
diff and check evidence. Replays reuse durable worker/check outcomes and recheck
the live evidence before acceptance. Optional ZIP omission does not prevent an
otherwise valid candidate from reaching this gate. No promotion or automatic
controller adoption is introduced.

The first focused run passed 172 tests with one fixture line-ending failure; the
corrected fixture passed its isolated rerun. Affected regressions passed 177 tests
with five Windows symlink skips. The framework and root suites passed 94 and 12
tests respectively. This is focused and affected verification, not a full-repository
test claim.

One bounded real-model ACL maintenance task completed the workflow and returned
an independently accepted diff. Its protected checker passed all five documentation
tests. The reviewed single assertion-string correction was retained in this
development target. Replay with activation disabled returned the identical report
without changing execution evidence. The selected configuration remains 131072
context tokens with a 2048-token output budget. The original checkout has not
adopted these changes. M06 is complete; the operator separately authorized
continuation through M07 and M08, whose implementation and verification remain
separate checkpoints.


## M07 — durable job selection

[M07](M07_DURABLE_JOBS.md) adds one protected aggregate for the approved plan,
with one durable task reservation, exact attempt binding, accepted dependency
references, blockers and restart-safe result recording. The 39 focused job/plan
checks pass. These are deterministic coordination fixtures, not model execution.
The generic job authorization boundary remains disabled until M09 connects the
job time budget to supervision; M08 supplies accepted-source handoff.


## M08 — accepted local snapshots and exact downstream input

[M08](M08_ACCEPTED_SNAPSHOTS.md) is complete in the isolated development target.
The controller promotes only an independently accepted candidate to a separate
clean local artifact. Acceptance, source bytes, base/commit, checkout metadata and
the next task's input remain linked by protected records. Repeated promotion
verifies the same artifact; missing or inconsistent interruption proof blocks.
An accepted no-op retains its existing base without an empty commit.

The next task uses the selected accepted snapshot, including files outside its
context manifest. Admission, workspace preparation and job binding check the exact
source and lineage. Original plan/profile permissions, context membership and
purposes, checks and output obligations do not expand. Divergent accepted histories
block instead of being merged automatically. Workers receive no commit/push tools.

Before the final two narrow fixes, broad affected regressions passed 674 tests with seven Windows symlink skips. After those fixes, 76 focused job/snapshot/input tests and 57 validator/acceptance/workflow tests passed. Final root tests passed 12; Node adapter tests passed 12. This is staged focused and affected verification, not a fresh full-repository test claim.

Initial failing checks and their corrective reruns remain recorded separately.
The last fixes align public job identities with the approved plan's identifier
rules and allow naturally departing validator helpers to drain within the existing
cleanup timeout; persistent children still fail. M08 uses deterministic worker
fixtures with real Git and protected checks, not a new model run. The earlier real
M06 evidence remains pinned to its own controller checkpoint.

The runtime grants no remote publication or automatic adoption. The operator
separately authorized integrating accepted work through M08 into the development
branch `architecture/knowledge-core` and publishing that branch. Earlier isolated
checkout statements describe their historical checkpoints. The selected
131072-context/2048-output-token configuration remains unchanged.
M09's assembled sequential commands and deadline supervision are the next queue
step and require a separate assignment; generic job-task execution remains disabled.
