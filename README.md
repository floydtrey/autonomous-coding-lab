# ACL Next

ACL Next is the clean rebuild of Autonomous Coding Lab.

This branch intentionally contains only the new implementation. The previous ACL
remains in repository history and on its existing branches as reference material,
but it is not part of this working tree and must not be imported as a runtime
dependency.

## Current scope

The first implemented layer is Core V0:

- identity and correlation;
- structured diagnostics;
- authority ceilings, grants, narrowing, and enforcement;
- generic resources and targets;
- generic tools and tool enforcement;
- replaceable adapter contracts;
- narrow transport normalization.

Core intentionally does not contain Controller workflow, AI roles, JobPlan,
validation policy, KC semantics, Git/GitHub assumptions, or old Worker Lab code.

Development proceeds by adding the new layers directly to this clean tree and
using the prior ACL only as external reference when a proven mechanism is worth
adapting.


## Controller Pass 1

The first Controller construction pass is now present under `acl_controller/`.

Implemented so far:

- generic request/workflow records;
- file-backed Controller state with generation checks;
- explicit workflow state transitions;
- exact external role-profile resolution with no silent fallback;
- action registry for already-structured action types;
- small `ControllerService` façade over Core, state, configuration, and routing.

Controller diagnostics use Core's structured diagnostic stream. State transitions,
profile resolution, action registration/dispatch, and Controller service operations
emit correlated DEBUG/INFO/error records when diagnostics are enabled.

Not built yet:

- AI role dispatch;
- authority handoff into role execution;
- clarification;
- approval gates;
- retry/continuation budgets;
- workflow engine;
- recovery/stop;
- final status/inspection surface.

Controller contains no Planner/Worker/Reviewer reasoning and no Git/GitHub target
assumptions.


## Controller Pass 2

The second Controller construction pass adds the execution-control mechanisms that
the later workflow engine will compose:

- generic role dispatch through Core adapters;
- persisted Core authority grants and narrowing;
- clarification pause/answer records;
- external approval gates with self-approval rejection;
- separate retry and continuation budgets.

Role dispatch understands only a small generic result envelope:

- `COMPLETE`
- `NEEDS_CLARIFICATION`
- `NEEDS_CONTINUATION`
- `BLOCKED`
- `FAILED`

It does not interpret role-specific content. Pass 3 will decide how the workflow
engine reacts to those structured statuses.

Authority remains Core-owned. Controller persists and references Core grants but
cannot enlarge a supplied ceiling or parent grant.

Clarifications, gates, grants, and retry accounting are persisted under Controller
state so later recovery can reconstruct why a workflow is waiting or blocked.

Diagnostics remain intentionally verbose during the rebuild. Role dispatch,
adapter identity, grant issue/narrow operations, questions, answers, gate
decisions, retry consumption/exhaustion, workflow IDs, attempt IDs, and correlated
failures are emitted through the shared Core diagnostic stream when enabled.

Not built yet:

- workflow engine;
- stop/cancel/recovery service;
- final inspection/status aggregation;
- AI role implementations;
- validation subsystem.


## Controller Pass 3

The third Controller construction pass adds the mechanical workflow loop,
conservative recovery, and aggregated inspection surface.

Implemented:

- persisted generic workflow programs made of ROLE, ACTION, and GATE steps;
- exact persisted step-result records;
- mechanical workflow execution with a per-call operation ceiling;
- structured handling for COMPLETE, NEEDS_CLARIFICATION, NEEDS_CONTINUATION,
  NEEDS_RETRY, BLOCKED, and FAILED;
- explicit gate steps;
- conservative stop requests for active role executions;
- standardized `role.cancel` and `role.status` adapter control operations;
- no automatic rerun when active execution state cannot be proven;
- recovered exact terminal role results use the same response parser and workflow
  result path as live role results;
- aggregated read-only workflow inspection including program, grant, profile,
  results, clarification history, gates, retry state, and stop history.

Workflow programs are Controller recipes, not work/task plans. They contain
mechanical execution ordering only. Planner/Worker/Reviewer reasoning remains
outside Controller.

Recovery deliberately blocks when a non-role action has no generic status/cancel
protocol, when an active execution disappears without terminal evidence, or when
adapter status cannot be confirmed.

Diagnostics remain a primary rebuild feature. Pass 3 emits workflow step starts,
program binding, exact result identities/digests, operation-limit stops, stop and
recovery observations, uncertain recovery blocks, and inspection summaries in
addition to the Core/Pass-1/Pass-2 diagnostic stream.

Still not implemented:

- actual Determiner/Planner/Worker/Reviewer role implementations;
- Validator implementation;
- concrete provider/harness adapters;
- user interface;
- dedicated test campaign.


## Roles Foundation Pass

The first AI-role pass establishes only the shared role contract and diagnostics.
It does not implement Determiner, Planner, Worker, Reviewer, or Validator behavior.

Implemented under `acl_roles/common/`:

- canonical `RoleRequest` envelope;
- canonical `RoleResponse` envelope;
- shared `RoleStatus` values;
- provider-neutral context references;
- externally supplied instruction-set identity/digests;
- authority-grant identity and available tool IDs in the model-facing request;
- adapter-only trusted authority envelope kept separate from the model request;
- common request/response digests and byte counts;
- instruction/context/tool/profile/adapter diagnostics;
- explicit response parse-error and adapter-error diagnostics;
- optional raw deep-debug request/response artifacts.

Raw role payloads are **not** written to the normal diagnostic log. Full request
and response artifacts are stored only when explicitly enabled:

- `ACL_ROLE_DEBUG_ARTIFACTS=1`
- `ACL_ROLE_DEBUG_PATH=<path>`

This keeps ordinary DEBUG logging detailed without automatically persisting full
prompt/context content.

Controller role dispatch now consumes the shared role contract rather than owning
a separate role-status/parser definition.

### Next pass — Determiner foundation

The next pass is deliberately limited to:

1. Determiner input/output contract;
2. Determiner instructions;
3. externally configured work-type taxonomy;
4. Determiner profile/configuration skeleton.

It will **not** yet add a concrete runtime/provider adapter or perform live model
runs. Those belong to the following Determiner integration pass.


## Determiner Foundation Pass

The Determiner foundation is now defined, but intentionally not connected to a
real model/runtime yet.

Implemented:

- Determiner-specific input contract;
- Determiner-specific result contract;
- CLASSIFIED and UNKNOWN classification outcomes;
- structured clarification responses through the shared role envelope;
- optional SMALL / MEDIUM / LARGE complexity classification;
- confidence and concise reason-code fields;
- externally loaded work-type taxonomy;
- Determiner-specific result parsing and diagnostics;
- pre-classification Controller routing using `work_type: null`;
- an unbound `determiner-general` role profile containing Determiner instructions.

Initial configured work types:

- CODING
- RESEARCH
- DOCUMENT
- VIDEO
- KNOWLEDGE
- SYSTEM_ADMIN
- GENERAL

`UNKNOWN` is an outcome, not a work type. `NEEDS_CLARIFICATION` remains a
shared role status rather than a taxonomy category.

NETWORKING is deliberately deferred. It can be added later as an external
taxonomy entry when network/endpoint/integration work becomes common enough to
benefit from a distinct route. Adding it must not require Controller or Determiner
source changes.

The Determiner instructions explicitly prohibit planning, execution, model/harness
selection, authority expansion, tool selection, inventing categories, and simple
keyword-only classification.

The profile's adapter is currently `unbound.determiner`; this is intentional and
prevents the foundation pass from silently choosing a provider or local model.

### Next pass — Determiner integration

The next pass is limited to:

1. choose/implement the first concrete local runtime adapter needed for Determiner;
2. bind `determiner-general` to that adapter and external runtime settings;
3. construct the first Controller workflow containing a Determiner role step;
4. run a small set of real classification requests with DEBUG diagnostics enabled;
5. fix only generic Core/Controller/adapter gaps exposed by those real runs.

It will **not** begin Planner implementation.
