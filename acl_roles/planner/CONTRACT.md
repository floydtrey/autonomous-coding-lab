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


## Elevation/resume transport

Planner's semantic disposition and ACL's shared role status are intentionally separate:

- `ELEVATION_REQUIRED` is wrapped as shared `NEEDS_CLARIFICATION`.
- Other valid Planner dispositions are wrapped as shared `COMPLETE`; the Planner payload still tells ACL what semantic result was produced.
- The shared status and Planner disposition must agree. A mismatch is a contract error rather than something ACL guesses around.

Planner elevation answers are persisted as a mapping keyed by the exact Planner `question_id`:

```json
{
  "Q01": "Replace existing"
}
```

A resume answer must cover every question in that elevation and may not introduce unknown question IDs. Answer values are semantically opaque to Controller; Planner interprets them.

Resume preserves the original `PlannerInput` fields and adds the answered question values to
`elevation_answers`. A previously recorded answer may be replayed idempotently but must not be
silently replaced with a different value.

ACL's existing clarification store remains the durable pause/resume mechanism. The pending
clarification record holds the questions and opaque context, the workflow enters `WAITING`, and
answering the clarification returns the same workflow stage to `READY`. The original request is
therefore not re-entered by the operator.


## Development observability

Planner development must be highly observable without making diagnostics part of Planner semantics.

ACL owns this instrumentation. It must be possible to reduce or disable it later without changing
Planner prompts, the Planner result schema, or execution behavior.

During development, retain high-signal structured diagnostics for at least:

- workflow, attempt, role, profile, adapter/harness, runtime, and model identity;
- Planner invocation mode and semantic disposition;
- validation/normalization/correction events and error codes;
- clarification/elevation pause and resume events;
- model/server load, unload, startup, retry, and failure events when available;
- wall-clock/model/adapter timing when available;
- prompt/input tokens, completion/output tokens, and total tokens when the runtime reports them;
- cumulative token totals at useful workflow/role boundaries without requiring Benchmark Lab.

Raw prompt/response artifacts remain a separate deeper-debug option because they are noisier and may
contain sensitive project content. Turning raw artifacts off must not disable ordinary high-level
diagnostics or token/timing telemetry.

A provider that does not report token usage may leave token fields unknown; ACL must not invent token
counts. Token/runtime telemetry is observational only and must not alter Planner semantic output.


## Deterministic response validation

Planner semantic validation is separate from filesystem Authority validation.

PL05 validates the Planner result against the exact `PlannerInput` that produced it. The generic
role-validation boundary passes the original role request into the configured role validator so the
Planner validator can perform request/response consistency checks without moving Planner semantics
into Controller.

For an `EXECUTION_PLAN`, deterministic validation checks at least:

- the plan preserves the accepted Determiner `work_type_id` when one was supplied;
- required outputs and tracking requirements are present;
- every Pass declares expected outputs and Worker evidence requirements;
- Stage, Pass, and Task dependency targets exist and dependency graphs are acyclic;
- Task dependencies remain inside their Pass; cross-Pass ordering belongs on `Pass.depends_on`;
- task IDs are unique across the whole plan;
- every used `reference_id` exists in the plan's declared reference material;
- filesystem declarations are syntactically usable and move/rename operations are not no-ops.

`WORKER_CONSULTATION` may return an answer/query response, elevate to the operator, or decline.
It may not replace the execution plan in V1; dynamic replanning is deferred.

Important: these checks validate contract consistency only. They do not decide whether the Planner
*should* modify a declared file. A structurally valid path proceeds to the separate deterministic
filesystem Authority layer, which grants or denies the operation based only on authority policy.

Stable validation error codes are intentionally specific enough for PL06 corrective prompts. Examples
include `PLANNER_ROUTE_MISMATCH`, `PLANNER_DEPENDENCY_UNKNOWN`,
`PLANNER_DEPENDENCY_CYCLE`, `PLANNER_REFERENCE_UNKNOWN`,
`PLANNER_REQUIRED_OUTPUTS_MISSING`, and `PLANNER_PATH_INVALID`.


## Corrective feedback

Planner correction is an ACL-owned retry input, not a Planner-owned runtime policy.

When deterministic parsing or validation rejects a Planner response, ACL may construct a new
`PlannerInput` containing an optional `correction` object. The original request, accepted routing
context, consultation state, and answered elevations remain unchanged.

The correction object carries:

- ACL's correction-attempt number;
- the most specific validation/error code and message;
- error details/location when available;
- the previous model response;
- a digest of that previous response when it can be canonicalized;
- the editable correction instruction selected from `config/planner_corrections.json`;
- whether the same error/response signature has already been seen.

Correction prompts are configuration, not Python business logic. Exact error-code rules may give
targeted repair guidance; other configured repairable Planner/role errors use the default instruction.

The normal repair instruction tells Planner to preserve valid sections and return one **complete**
corrected Planner response. ACL does not accept patch fragments because downstream validation needs a
complete contract.

If the same error code/location occurs against the same previous-response digest again, ACL can
supply the repeated-failure instruction instead of blindly issuing the identical repair prompt.
ACL still owns the actual retry ceiling.

Authority failures are not ordinary Planner formatting corrections. A Worker/Planner cannot use the
correction loop to rewrite or bypass filesystem Authority policy.

The correction policy is loaded from `config/planner_corrections.json`. ACL's control-config
directory is permanently protected from Worker mutation; later operator/GUI configuration may edit
these prompts outside Worker authority.


## Runtime and path neutrality

Planner runtime is exposed through one stable semantic port:

`PlannerRuntimeRequest -> PlannerRuntimeBackend -> PlannerRuntimeResponse`.

The request contains Planner semantic input plus ACL correlation/authority identifiers. It does not
contain a provider name, model name, server URL, port, quantization, harness name, or transport
format. The Controller-backed implementation resolves the configured Planner profile and uses the
existing generic role/adapter boundary. A deterministic function backend implements the same port,
so fake and real Planner implementations can be exchanged without changing Planner semantics.

Concrete runtime/model/harness choices remain external configuration. Runtime metadata may report
which configured implementation actually ran, but that information is observational and is not part
of the semantic plan.

Machine-specific absolute paths are never defaults in the Planner runtime contract. Project,
workspace, output, artifact, reference, state, and configuration locations come from caller input,
Planner semantic output, or configuration. ACL package-protection paths are derived from the
installed package locations at runtime rather than assuming a particular drive or repository path.

The Controller accepts an explicit `project_root`. The traditional layout where `config/` lives
directly beneath the project root remains only a compatibility default; it is not required by the
Planner contract.

Source control is optional. Git and GitHub are not Planner, Controller, or runtime prerequisites.
If a particular job requires source-control or repository-hosting operations, Planner may declare
those as ordinary required tools/services/resources and ACL may provide an appropriate configured
implementation. A local folder, non-Git workspace, another VCS, or another hosting provider must
remain valid without contract changes.


## Fast non-Worker dispositions

ACL exposes a Planner fast path through `ControllerService.run_planner(...)`.

The fast path never starts a Worker or Reviewer:

- `DIRECT_RESPONSE` returns the Planner answer and completes the workflow.
- `QUERY_RESPONSE` returns the Planner's permitted lightweight-query answer and completes the workflow.
- `ELEVATION_REQUIRED` creates a durable clarification record and places the workflow in `WAITING`.
- `EXECUTION_PLAN` returns `PLAN_READY` with the semantic plan intact; no Worker is started. Plan persistence/intake belongs to PL10.
- `CANNOT_PLAN` blocks the workflow with the Planner reason codes/notes rather than silently falling through to execution.

A newly created workflow is mechanically moved to `READY` before Planner invocation. The generic
Controller state machine permits a `READY` workflow to complete without entering Worker execution,
because a direct/query Planner answer is a valid terminal workflow outcome.

For elevation, the clarification context retains the Planner input, Planner result, runtime
metadata, and active authority-grant identity needed by the resume path. The clarification mechanism
remains the same generic ACL WAITING/READY mechanism used elsewhere; Planner does not create a
second approval system. `ControllerService.resume_planner_elevation(...)` validates the operator's
answers against the pending Planner questions, restores the same Planner input with
`elevation_answers`, preserves the authority grant, and invokes Planner again.

`QUERY_RESPONSE` describes the outcome, not a special Worker. Any lightweight file/KC/search/tool
access used to produce that answer must come from Planner's authorized tools/runtime. If the Planner
cannot answer with its permitted resources, it should elevate, return `CANNOT_PLAN`, or produce an
execution plan as appropriate.


## Bounded Worker-to-Planner consultation

PL09 establishes the advisory conversation path without wiring a real Worker.

A synthetic or future real Worker question is represented as `WORKER_CONSULTATION` and includes
the active plan/pass/task identity, the Worker question, why guidance is needed, a concise current
state summary, relevant reference IDs/evidence, and the bounded prior consultation exchanges needed
to understand follow-up questions.

ACL persists each consultation independently under Controller state and owns the exchange budget.
The default is currently four Worker-to-Planner exchanges and is editable in
`config/planner_consultation.json`.

One exchange means:

`Worker question -> Planner's eventual answer`.

If Planner returns `ELEVATION_REQUIRED`, ACL asks the operator through the existing clarification
mechanism. The operator answer resumes Planner and completes the **same** Worker-to-Planner exchange;
it does not consume another exchange.

Allowed consultation outcomes are:

- `DIRECT_RESPONSE` or `QUERY_RESPONSE`: guidance is returned for relay to the Worker;
- `ELEVATION_REQUIRED`: consultation pauses in `WAITING_USER` until operator input;
- `CANNOT_PLAN`: ACL returns a recognizable `CANNOT_ANSWER` consultation outcome;
- exchange ceiling reached: ACL returns `EXCHANGE_LIMIT_REACHED` and does not invoke Planner again.

An `EXECUTION_PLAN` is invalid during `WORKER_CONSULTATION` in V1. Consultation may advise the
active work; it does not silently replace the approved plan.

Consultation does not complete the workflow when Planner answers. It is advisory traffic inside an
existing execution flow. Only operator elevation changes workflow state, using the generic
`WAITING -> READY` clarification path.

PL09 does not load or execute a Worker. `ControllerService.create(...)` accepts an optional
`PlannerRuntimeService` override so the consultation flow can be exercised with the deterministic
function Planner backend before a real Planner model is selected. The same interface will be used
when Worker integration arrives.

Serial Planner/Worker model unload/reload remains deferred until a real Worker is connected. At that
point ACL will preserve Worker session state, unload the Worker model, invoke Planner, then restore
the Worker role as previously agreed.


## Execution-plan intake and next-Pass state

PL10 converts a validated semantic `EXECUTION_PLAN` into durable ACL-owned execution state without
starting a Worker.

ACL assigns:

- an opaque canonical `plan_id`;
- `plan_version = 1` for Planner V1;
- the workflow association;
- a digest of the immutable semantic Planner plan;
- ordered Pass execution state.

The complete semantic `Plan -> Stage -> Pass -> Task` structure is persisted unchanged. ACL does
not rewrite Planner's tasks or invent a different decomposition during intake.

Before persistence, ACL re-applies deterministic Planner semantic validation and separately checks
all declared filesystem operations through the filesystem Authority layer. This is an authority
check only. ACL still does not decide whether a permitted file *should* be changed.

Planner V1 intentionally supports one accepted semantic plan per workflow. Re-intaking the identical
plan is idempotent and returns the same ACL plan identity. Attempting to replace it with a different
semantic plan is a conflict. Dynamic replanning/version increments remain deferred.

Pass execution state is mechanical:

- `PENDING`
- `COMPLETE`
- `FAILED`

ACL resolves the next Pass deterministically in declaration order. A Pass is eligible only when its
declared Pass dependencies are complete and, for staged plans, every Pass belonging to each declared
Stage dependency is complete. Independent eligible Passes are still serialized in V1: the first
eligible Pass is the one ACL exposes as `READY`.

Only that deterministic next eligible Pass may be marked complete or failed. This prevents a caller
from skipping ahead in plan state. Terminal updates are idempotent when replayed with the same value.

A failed Pass puts the persisted plan into `BLOCKED`. Completing all Passes puts the persisted plan
into `COMPLETE`. These are plan-state facts only; PL10 does not start a Worker, invoke Reviewer, or
decide retry/recovery policy.

`next_planner_pass(...)` produces one of:

- `READY` with the full semantic Pass and optional Stage ID;
- `PLAN_COMPLETE`;
- `BLOCKED` with failed Pass IDs;
- `NO_ELIGIBLE_PASS` with dependency blockers if persisted state cannot currently advance.

Plan state lives beneath the configured Controller state root. It contains no Git/GitHub requirement
and no machine-specific repository path assumption beyond paths already supplied semantically by the
Planner/caller.


## Planner observability and token accounting

PL11 adds optional persisted Planner telemetry in addition to ACL's existing structured diagnostic
log.

Development telemetry is enabled by `config/planner_telemetry.json`. Setting `enabled` to
`false` stops new Planner telemetry records without changing Planner semantics, routing, authority,
or execution behavior. Telemetry configuration/persistence failures are treated as diagnostic
failures only and must not stop the underlying Planner request.

Each Planner invocation can retain high-level identity and performance data when available:

- workflow, attempt, invocation mode, disposition, correction attempt, consultation/exchange IDs;
- Planner backend, profile, adapter/runtime family, configured harness identity, and model identity;
- prompt/input tokens, completion/output tokens, and provider-reported total tokens;
- configured context window and derived prompt-context utilization when both values are known;
- Planner end-to-end elapsed time and adapter HTTP/runtime elapsed time;
- request/response byte counts and finish reason;
- future runtime-supplied model load/unload time, tool-call count, and turn count;
- error code/message for failed Planner invocations.

Token counts are never guessed. The OpenAI-compatible adapter normalizes only token values actually
reported by the runtime (`prompt_tokens`/`input_tokens`,
`completion_tokens`/`output_tokens`, and `total_tokens`). If a runtime omits a value, that
field remains unknown. Workflow summaries include report counts so a partial token total cannot be
mistaken for complete coverage.

Context utilization is reported only when the configured runtime/profile supplies a positive
`context_window` and the runtime reports prompt/input tokens. Model load/unload, tool-call, and
turn fields likewise remain unknown until the active runtime/harness reports them.

The OpenAI-compatible adapter preserves runtime usage metadata instead of discarding the outer
response after extracting model content. That metadata flows through generic AdapterResponse,
RoleResponse/RoleDispatch metadata, and the Planner runtime without changing the semantic role
contract.

Planner telemetry records live beneath the configured ACL state root. They intentionally exclude raw
prompts and raw model responses. Full request/response artifacts remain a separate deep-debug option
controlled by `RoleDiagnostics`.

Existing structured ACL diagnostics remain independently controllable. The runtime CLI's
`--debug` option enables high-level JSONL Core/Controller/role logs; omitting it leaves that log
off. Raw role artifacts require their separate explicit option. This lets normal high-level
telemetry/logging and deep raw debugging be controlled independently.

`ControllerService.planner_telemetry_summary(workflow_id)` exposes cumulative workflow-level
counts/timing/tokens, and the normal runtime/clarification command output includes that summary.
Missing measurements remain `null` rather than being reported as zero.

PL11 reserves load/unload telemetry fields now, but actual serial Worker/Planner model switching is
still deferred until the Worker integration phase.
