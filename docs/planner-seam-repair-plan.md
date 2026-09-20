# Planner Seam Repair Plan

Branch: `planner-seam-repair-development`
Base: `task7-pipeline-connection-development`

## Scope

Repair the model-facing Planner path without replacing ACL's Controller-owned authority,
runtime routing, persisted workflow state, internal ExecutionPlan representation, Worker
Pass execution, or bounded Worker-to-Planner consultation.

The guiding boundary is:

- Models own semantic reasoning, decomposition, questions, and bounded Worker instructions.
- ACL owns authority, runtime/provider selection, IDs, persistence, execution state,
  retries, continuation bookkeeping, and compilation into internal Controller structures.

## Bounded tasks

### R01 — Lock the ownership boundary

- Treat the existing rich `ExecutionPlan` contract as internal Controller IR.
- Do not add more model-facing fields to repair local-model serialization.
- Keep the existing rich parser/validator available for compatibility until the new seam
  is connected.

Acceptance:
- This plan exists in-repo.
- No repair task expands the old model-facing Controller schema.

### R02 — Make production Planner inspection match its configured tool profile

- Fix the production Planner read grant so `filesystem.search` is actually granted when
  the Planner tool profile includes it.
- Add regression coverage proving Planner has list/read/search but no mutation authority.

Acceptance:
- Production and benchmark both expose the same read-only inspection primitives.
- Mutation remains denied.

### R03 — Bound model-visible tool-result size

- Add a generic agent-runtime limit for tool-result content returned to the model.
- Preserve full tool execution semantics; only the model-visible serialized result is
  bounded.
- Record truncation in telemetry/result metadata.
- Configure a conservative Planner limit and a larger Worker limit.

Acceptance:
- A single read/search result cannot consume an unbounded share of model context.
- The model is told when a result was truncated and can request a narrower read/search.

### R04 — Separate configured context capacity from observed runtime context

- Stop presenting configured `context_window` as though it proves provider-loaded
  context.
- Preserve backward-compatible telemetry while adding explicit configured/observed
  fields.
- Let provider-specific benchmark telemetry report the real loaded context when known.

Acceptance:
- ACL never claims a configured 16K route proves Ollama actually loaded 16K.
- Context-pressure calculations have an explicitly named capacity source.

### R05 — Introduce the small Planner submission boundary

- Replace Controller-shaped execution output with a small semantic Planner submission.
- Prefer terminating semantic tools such as `planner.submit_plan` and
  `planner.ask_operator` if the generic tool loop can support terminal tools cleanly.
- Keep direct/query responses small and independent of Controller IR.

Acceptance:
- Planner no longer emits workspace serialization, authority arrays, runtime/provider
  details, Controller IDs, dependency bookkeeping, or empty/default Controller fields.

### R06 — Compile Planner submission into internal ExecutionPlan

- Add deterministic translation from the semantic Planner submission into the existing
  internal `ExecutionPlan`/Pass/Task structures.
- Derive IDs, positional ordering, workspace, known route, defaults, and Controller
  bookkeeping mechanically.
- Fail/elevate if translation would require inventing semantic work.

Acceptance:
- Existing plan persistence and Worker execution consume compiled internal plans without
  learning the new model protocol.

### R07 — Restore benchmark fidelity

Maintain two clearly distinct test surfaces:

1. semantic Planner benchmark — intentionally loose, grades planning quality;
2. integration Planner benchmark — exact production instructions, tools, authority,
   context route, and submission boundary.

Acceptance:
- A model cannot pass integration using tools or output behavior unavailable in
  production.
- Semantic quality and transport/integration quality are scored separately.

### R08 — Add session/context-pressure foundation

- Introduce an append-only model-interaction event/session abstraction.
- Track projected next-request pressure from the effective route capacity.
- Add pre-turn warning/stop hooks and a compaction interface, but do not implement a
  large summarization system in this repair series.

Acceptance:
- Agent history is no longer conceptually owned only by one mutable in-memory
  `messages` list.
- Future compaction can replace the model-visible surface while preserving durable
  interaction history.

## Explicit stopping points

Stop for operator input if any repair would:

- change permanent filesystem protection semantics;
- change the meaning of Worker mutation authority;
- remove persisted plan/workflow compatibility rather than adapting it;
- require choosing a new production model/provider;
- require destructive migration of existing state.

Otherwise continue through the bounded tasks in order.
