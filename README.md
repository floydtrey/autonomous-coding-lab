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
