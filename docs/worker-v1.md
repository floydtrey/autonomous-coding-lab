# Worker V1 — bounded implementation path

Worker V1 begins from the accepted Planner plan. Planner owns semantic
decomposition; ACL owns deterministic Pass selection, authority, runtime
selection, persistence, recovery, continuation, and Reviewer handoff.

## Scope lock

This branch implements only the minimum Worker path needed to advance toward
Reviewer:

1. one Worker invocation consumes exactly one deterministic next Planner Pass;
2. Worker input is bound to plan ID/version/digest and Pass identity;
3. Worker result is structured and deterministically validated;
4. Worker may return READY_FOR_REVIEW, NEEDS_CONTINUATION, NEEDS_PLANNER,
   BLOCKED, or FAILED;
5. Worker never approves its own Pass;
6. READY_FOR_REVIEW persists an immutable Reviewer intake packet while the
   Planner Pass remains PENDING;
7. NEEDS_PLANNER can be routed into the already-built bounded Planner
   consultation path;
8. continuation is explicit and reconstructs Worker input from durable prior
   results;
9. model/runtime/harness choices remain external configuration;
10. runtime residency/recovery continues to pin in-flight execution to the
    resolved model identity.

Not in this slice:

- Reviewer judgment or Pass approval/rejection;
- automatic retry/continuation budgets;
- dynamic model selection;
- benchmark scoring;
- KC retrieval;
- UI work;
- live reasoning display;
- Git/GitHub requirements;
- a new tool harness implementation.

## Pass boundary

Pass remains the Worker execution/session boundary. Worker receives the full
Pass, including ordered Tasks, plus compact plan-level context:

- plan objective and acceptance criteria;
- required outputs and constraints;
- workspace;
- references/sources;
- semantic capabilities/tools/services/research requirements;
- completed dependency Pass IDs.

ACL does not reinterpret whether Planner's semantic choices are wise.

## Worker outcomes

### READY_FOR_REVIEW

Worker reports all assigned Tasks complete and supplies evidence. ACL persists
the result, moves the workflow to `review-ready`, and leaves the Planner Pass
PENDING. Only Reviewer/controller policy may later advance Pass state.

### NEEDS_CONTINUATION

Worker needs another execution segment without a semantic decision. ACL persists
the partial result and moves the workflow to `worker-continuation-ready`.
Continuation is explicit; no automatic budget policy is introduced yet.

### NEEDS_PLANNER

Worker cannot safely make a semantic decision. ACL persists the request and
moves the workflow to `worker-planner-needed`. The Controller can route the
saved question into the existing bounded Planner consultation service, then
continue Worker with that guidance.

### BLOCKED / FAILED

ACL persists the result and blocks the workflow. It does not silently mark the
Planner Pass failed; Reviewer/controller retry policy is still to be added.

## Reviewer seam

`acl-worker-review-packet:v1` binds:

- workflow/plan/version/digest;
- Pass identity and exact Pass contract;
- compact plan context;
- Worker run ID and structured Worker result;
- runtime/model/harness metadata;
- prior Worker results for the same Pass.

This is the input boundary for the next Reviewer implementation. It intentionally
does not treat Worker self-report as authoritative evidence of success.

## Runtime and adapter status

The generic Worker profile is `worker-v1-generic`. Model selection is external
through `ACL_WORKER_MODEL`; launcher configuration uses
`ACL_WORKER_LAUNCH_COMMAND_JSON`, `ACL_WORKER_LAUNCHER`, and
`ACL_WORKER_LAUNCHER_CWD`.

Worker should reuse the existing configured harness/tool path rather than invent
a second Worker harness. Tool availability is an execution capability supplied by
the bound harness and ACL authority configuration.

The current OpenAI-compatible transport carries ACL role/tool identity, but the
Planner probe did not exercise tool execution. Worker integration must therefore
verify that the existing harness tools are actually bound through the ACL Worker
runtime path. If a particular run genuinely lacks a required tool, Worker must
BLOCK rather than claim hypothetical execution. Building a new harness is not a
Worker V1 requirement.

## Deferred Planner verification

Planner Model A (Qwen 3.8 27B) passed the real PL12 integration gate. The
previous PL13 plan to prove an alternate adapter/harness with the same Planner
model is intentionally deferred. It remains a portability verification item,
not a blocker for Worker/Reviewer construction.

## Current acceptance gate when tower access resumes

The first local Worker gate should be deliberately small:

1. Planner produces the existing one-file probe Pass;
2. ACL selects that exact Pass;
3. Worker runtime resolves the configured Worker profile/model and reuses the
   existing harness/tool capability;
4. verify the harness exposes the expected mutation tools through ACL authority;
5. require a real changed-file result plus evidence;
6. generate the Reviewer packet;
7. only then begin Reviewer live integration.

No broad pytest cycle is required for this development phase; use the existing
high-level diagnostics and targeted failures to drive fixes.
