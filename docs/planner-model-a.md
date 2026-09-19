# Planner Model A — PL12 Integration

Model A for the first real Planner integration is **Qwen 3.8 27B**.

The concrete model identifier is not embedded in Planner, Controller, or adapter
source. The `planner-model-a` profile reads `ACL_PLANNER_MODEL`, so the exact
server-visible alias remains runtime configuration. On the current development
machine the intended first candidate is `qwen3.8:27b`; use the alias exposed by
the active OpenAI-compatible server if it differs.

## Purpose of PL12

PL12 is not a broad model benchmark. It proves that one real local model can use
the already-frozen Planner V1 contract through the generic runtime boundary.

The same profile is routed for every accepted V1 work type and for null/SMALL/
MEDIUM/LARGE Determiner complexity values. This is deliberate: domain-specific
Planner models are deferred until the generic contract is proven.

## Runtime configuration

Required runtime configuration remains external:

- `ACL_PLANNER_MODEL` — server-visible Model A identifier.
- `ACL_OPENAI_COMPAT_BASE_URL` — OpenAI-compatible endpoint already used by ACL.
- API key configuration, when needed, remains in the existing adapter/service
  environment configuration.
- `ACL_PLANNER_CONTEXT_WINDOW` is optional and is used for runtime configuration
  and telemetry. If omitted, context utilization remains unknown rather than
  being guessed.

The profile uses a 300-second request timeout and a 12,000-token output ceiling
for integration. Those are runtime limits, not semantic Planner policy.

If the selected OpenAI-compatible runtime dynamically serves multiple models,
`ACL_PLANNER_MODEL` is enough to select Model A. If the runtime is a single-model
server such as a one-model llama.cpp process, that server must already be
started with Model A (or its launcher configured to start Model A) before the
Planner integration runner is used. ACL does not pretend that changing a model
name can hot-swap a single-model server.

## Manual integration runner

`python -m acl_runtime.planner` drives the real path:

1. ensure configured local services are reachable;
2. create an ACL workflow;
3. construct `INITIAL_PLANNING` input from the accepted work type;
4. invoke Planner through Controller -> profile -> adapter -> real model;
5. apply DIRECT/QUERY/ELEVATION/PLAN/CANNOT_PLAN disposition behavior;
6. persist a valid execution plan through PL10 unless `--no-intake` is supplied;
7. print workflow state and Planner telemetry.

Use `--debug` for high-level JSONL diagnostics. Add `--raw-role-artifacts`
only when the high-level log is insufficient.

## First integration context

A 32K context is a reasonable first smoke setting because PL12 is proving the
contract rather than establishing the final Planner context ceiling. Increase it
after observing real prompt size/context utilization; the architecture does not
depend on 32K.

## What counts as a useful failure

PL12 expects some model/contract mismatches. Failed attempts retain high-level
telemetry and the rejected response where required for the targeted correction
loop. ACL may make up to the configured correction-attempt ceiling in
`planner_corrections.json`.

The correction loop is not allowed to repair Authority denial or Controller
policy by prompting the model around it.


## Residency note

PL12 now uses Controller runtime residency rather than the generic service
bootstrap to choose the model server. A healthy server is reused only when
`/models` reports the exact configured Planner model. Otherwise the
`planner-model-a` profile may launch the model through
`ACL_PLANNER_LAUNCHER` (and optional `ACL_PLANNER_LAUNCHER_CWD`).

If no Planner launcher is configured while another model is resident, the run
fails with a model-mismatch error. This is intentional: ACL must not silently
run Planner on whichever model happened to survive a prior Worker/Determiner
session.

Runtime checkpoints preserve the resolved in-flight model so disconnect
recovery does not bootstrap Determiner or adopt a newly edited model setting.
