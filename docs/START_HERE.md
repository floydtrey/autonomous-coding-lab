# Start Here

This is the routing page for current ACL work.

## Current authority order

1. `AGENTS.md` — repository work rules.
2. `docs/CURRENT_STATE.md` — exact current runtime/reconstruction state.
3. `docs/ARCHITECTURE.md` — current system boundaries and execution path.
4. `docs/GOVERNANCE.md` — authority/security rules.
5. `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` — reconstruction acceptance record and post-reconstruction boundary.

For source portability, read `docs/PORTABLE_SOURCE_IDENTITY.md`. For Controller/Knowledge Core handoff, read `docs/CONTROLLER_TASK_PACKET_V1.md`. For Git/repository boundaries, read `docs/REPOSITORY_COUPLING_INVENTORY.md`.

For the S02–S04 immutable job-plan contract, dependency validation, and admission-only bridge, read `docs/JOB_PLAN_V1.md`. These foundations do not implement the sequential controller.

For the approved S05b prerequisite immediately before S06, read
[the bounded task queue amendment](BOUNDED_TASK_QUEUE.md). S05b defines and carries
the output-acceptance contract; S06 follows after its acceptance tests pass.

For S05b schema, evidence semantics, and migration limits, read
[V1 output acceptance](OUTPUT_ACCEPTANCE_V1.md).

For S07's pinned Pi package and Windows import/startup evidence, read
[the compatibility probe](../tools/pi-compatibility/README.md). This does not
establish model/provider qualification or enable execution.

## Component ownership

- Worker Lab: protected authority, lifecycle, Provider Binding, dispatch preparation, independent acceptance.
- Autonomous Worker Framework: bounded execution/workspace containment and provider adapter surface.
- Knowledge Core: governed informational context only.
- Local Model Bench: advisory evaluation only.

## Current identity model

Portable source identity is host-independent and lives in `config/portable-source-manifest.json`. It contains reviewed component byte closures, not host/runtime activation facts.

Host/provider installation observation, capability qualification, Provider Binding, local activation, and per-invocation authorization are separate. A source checkout is not enabled by editing committed identity data.

ACL target identity is logical (`target:*` / `workspace:*`). Git repository facts are optional coding-workspace evidence beneath that boundary.

## Reconstruction status

Tasks 1–9 are complete. Task 9 accepted its reconstruction checkpoint through the deterministic test, source-identity, documentation, repository-boundary, no-fallback, and disabled-execution gates. That historical acceptance is not a claim that subsequent changes or an end-to-end V1 controller are accepted.

The sequential controller does **not** exist yet. The next implementation milestone is to build that controller around the existing task-packet, Invocation/Result V3, Provider Binding, and Worker Lab acceptance contracts. Initial V1 workers receive exact-file read/write authority; protected tests and result validation run on the controller side. Authentication is provider-neutral, with operator-approved credentials for the selected transport. No provider, including any proposed Pi integration, is qualified by this documentation.

Reconstruction completion does **not** activate ACL. Until the user separately authorizes the next supervised stage:

- do not execute a provider/model;
- do not perform real provider capability qualification;
- do not enable persistent execution;
- do not introduce provider/model/runner fallback;
- do not broaden current bounded workspace/tool authority.

Actual host/provider qualification and a supervised disposable vertical slice remain separate execution gates requiring explicit authorization; they are not substitutes for implementing the missing sequential controller. Benchmark-lab work remains separate and advisory.

## Research and Knowledge Core docs

`docs/research/` is non-authoritative research/reference material. For Knowledge Core, read [current state](architecture/knowledge-core/CURRENT_STATE.md), [architecture](architecture/knowledge-core/ARCHITECTURE.md), then [operations/evidence](architecture/knowledge-core/OPERATIONS.md). These three documents govern current KC work; its retrieval output remains informational to Worker Lab.

`docs/architecture/knowledge-core/legacy/` preserves historical KC documents and accepted evidence outside the default read order. Its old status and next-task prose are not current guidance. Git history remains intact; there is no second legacy runtime to resume.

## Minimum usable ACL implementation

Use the supplied [replacement M-task queue](MINIMUM_USABLE_ACL_QUEUE.md) for new
implementation; it supersedes unfinished S10–S51. S01–S09 evidence remains valid
within its recorded scope. Codex now acts on assigned tasks. See
[M02 adapter integration](M02_PI_ADAPTER.md) and
[M03 supervision](M03_PI_SUPERVISION.md). M03's real edit and cancellation checks
passed at the operator's preferred 128K setting.
[M04 worker outcomes](M04_WORKER_OUTCOMES.md) adds the explicit single-task command
and durable failure/restart evidence.
[M05 protected checks](M05_PROTECTED_VALIDATION.md) adds explicit named local-test
approval, exact candidate checks and durable validator cleanup evidence. Local
validation is unsandboxed host code execution; no approval is implied.
[M05A audit corrections](MINIMUM_USABLE_ACL_QUEUE.md#m05a--fix-the-four-m01m05-audit-findings)
are complete in the separate development target, with deterministic regression
evidence and refreshed source identities. These fix the retained runtime files.
[M06 task acceptance](M06_TASK_WORKFLOW.md) is verified, including one real
local-model maintenance task and independent acceptance. [M07 durable job
selection](M07_DURABLE_JOBS.md) is complete with deterministic fixture evidence.
[M08 accepted snapshots](M08_ACCEPTED_SNAPSHOTS.md) is complete and carries accepted
source bytes into the next task without changing its approved authority.
[M09A execution foundations](M09A_JOB_EXECUTION_FOUNDATIONS.md) is also complete:
reserved JOBTASK authorization is connected to the existing gate, realistic
configurable coding-work ceilings are selected, one absolute reservation deadline
is shared across preparation/worker/validation, and objective attempt evidence is
retained. The selected ceilings are 131072 context, 8192 max output tokens, 64 model
requests, 128 tool calls, 900-second provider timeout and 1800-second attempt timeout.
Runtime activation remains a separate gate.

The next queue step is M09B sequential run plus status. M09C later owns stop/reconcile
and M09D assembled M09 closure. Do not treat M09A completion as implementing those
commands or as live-model activation.
