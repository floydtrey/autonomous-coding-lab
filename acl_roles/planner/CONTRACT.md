# ACL Planner V1 Contract Boundaries

Status: **Normative V1 design baseline**

This document freezes ownership and control boundaries before Planner implementation.
It is intentionally narrower than the eventual Planner feature set.

## Planner purpose

Planner has two responsibilities:

1. Answer or perform a permitted lightweight query when no Worker execution is needed.
2. Produce a semantic execution plan that ACL can validate, persist, and later deliver one Pass at a time to a Worker.

Planner may also be invoked during execution as a bounded advisory service for a Worker.

Planner does not execute substantial project work, select a concrete model/harness, grant authority, or own runtime budgets.

## Invocation modes

- `INITIAL_PLANNING`: process a user/request objective and decide how it should proceed.
- `WORKER_CONSULTATION`: answer a bounded question raised by a Worker through ACL.

A Worker never calls Planner directly. ACL owns the consultation exchange and state.

## Planner dispositions

Every Planner invocation terminates with exactly one semantic disposition:

- `DIRECT_RESPONSE`: answer from the supplied context without Worker execution.
- `QUERY_RESPONSE`: perform permitted lightweight retrieval/query work and return an answer without Worker execution.
- `EXECUTION_PLAN`: return a structured plan suitable for ACL intake.
- `ELEVATION_REQUIRED`: stop before execution and ask the user one or more material questions.
- `CANNOT_PLAN`: the Planner cannot produce a valid result from the available information/capabilities.

`ELEVATION_REQUIRED` is not failure. ACL persists the pending state, presents the questions to the user, then reinvokes Planner with the answers.

During `WORKER_CONSULTATION`, Planner may either answer the Worker or return `ELEVATION_REQUIRED` when user input is materially required.

## Ownership boundaries

### Planner owns semantic planning

Planner may determine and declare:

- task/work type and required capabilities;
- project name/version information when actually known;
- objective, constraints, assumptions, and out-of-scope boundaries;
- acceptance criteria and required outputs;
- Plan -> optional Stage -> Pass -> Task decomposition;
- Pass/Task ordering and dependencies;
- descriptive complexity;
- required reference material, sources, KC queries/references, and research needs;
- worker working directory and intended final output/artifact directories;
- files/directories to read, create, write, delete, move, or rename;
- evidence/results the Worker should return;
- unresolved questions requiring elevation;
- concise reason codes for decomposition or elevation.

Planner declarations describe what the work requires. They are not grants of authority.

### ACL owns control and enforcement

ACL owns:

- canonical request, workflow, plan, run, attempt, grant, and execution identities;
- persisted execution state and canonical plan versioning;
- model, provider, server, harness, adapter, and runtime selection;
- concrete Worker selection from semantic task requirements;
- actual authority grants and deterministic authority enforcement;
- retry, turn, tool-call, continuation, consultation-exchange, and runtime budgets;
- review policy and whether/when Reviewer is invoked;
- correction/retry policy after contract-validation failure;
- telemetry collection and enable/disable policy;
- model loading/unloading/residency policy;
- interruption, recovery, and resume policy.

Planner must not encode concrete model names, server ports, harness names, retry counts,
token ceilings, tool-call ceilings, continuation counts, or granted permissions into the semantic plan.

## Filesystem authority boundary

Planner states which filesystem operations the plan requires. ACL does **not** judge whether
those file choices are semantically wise; it checks only deterministic authority policy.

Read authority and mutation authority are distinct.

V1 authority design must support:

- permanent mutation-deny locations for operating-system/system resources;
- permanent mutation protection for ACL Core, Controller, and authority-enforcement code/configuration;
- persistent user-protected/frozen files and directories;
- recursive directory protection;
- canonical path resolution sufficient to prevent trivial traversal or link/junction bypass;
- validation of both source and destination for move/rename operations.

If an ordinary project path is not prohibited by authority policy, ACL does not veto it merely
because ACL cannot determine whether changing that file is a good idea.

Planner and Worker may never modify the protection policy that constrains their own authority.

## Execution hierarchy

The V1 semantic hierarchy is:

```
Plan
  -> optional Stage
      -> Pass
          -> Task
```

**Pass is the Worker execution/session boundary.**

A small request is one Pass containing one Task. ACL does not ambiguously choose between
"send a Task" and "send a Pass"; it sends one Pass. Tasks are the ordered/subordinate work
inside that Pass.

## Elevation before execution

If a material ambiguity could change the work, target, output, or intended result, Planner should
return `ELEVATION_REQUIRED` before execution rather than guess.

Planner questions must be concise and structured. ACL owns the pending state and resume flow.

## Worker consultation

A Worker may pause and request Planner assistance through ACL for planning clarification,
additional semantic context, or guidance.

ACL provides Planner a bounded consultation envelope containing the relevant plan/pass/task
identity, the Worker question, reason, current-state summary, and references/evidence needed
to answer.

ACL owns a configurable maximum number of Worker<->Planner exchanges. Exhausting that budget
must produce a recognizable controller state rather than an unbounded model conversation.

## Model residency

Initial execution policy is serial: when Worker/Planner switching is implemented, ACL should
assume only one role model needs to remain resident. ACL must preserve enough durable task/session
state to unload one model, invoke the other role, then reconstruct/resume the prior role.

Future resource-aware concurrent residency is explicitly outside Planner V1.

## V1 exclusions

Planner V1 does not implement:

- multi-specialist parallel/fan-out execution;
- vision/audio/video specialist orchestration;
- Worker execution itself;
- intelligent Worker handoff validation;
- dynamic resource-aware concurrent model residency;
- authority-management GUI;
- Vera/browser/desktop/phone entry points.

The contract should remain extensible enough that these features do not require redefining the
core Planner/ACL ownership boundary.


## V1 machine-contract conventions

The executable schema lives in `acl_roles/planner/contract.py`.

- `work_type_id` preserves the configured Determiner route when one exists.
- `task_type` is the Planner's semantic description of the work and must not name a concrete model.
- `SINGLE_PASS` contains exactly one top-level Pass.
- `MULTI_PASS` contains at least two top-level Passes.
- `STAGED` contains Stages, each containing one or more Passes.
- Every execution plan explicitly declares a Worker working directory and output directory.
- Every Pass declares completion criteria and continuation instructions.
- Task filesystem intent is the source of requested read/write/create/delete/move operations; ACL may aggregate those declarations when constructing Pass authority.
- `required_tools` and `required_services` are semantic requirements, not granted access.
- `unresolved_questions` on an executable plan are non-blocking notes only. A material question that could change the intended work must use `ELEVATION_REQUIRED` instead.
- Planner result payloads do not echo ACL's invocation mode. ACL already owns the invocation context; requiring the model to repeat it would create an unnecessary conflict surface.
