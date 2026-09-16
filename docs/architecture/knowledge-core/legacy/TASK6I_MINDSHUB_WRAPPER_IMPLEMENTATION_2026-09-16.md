# Knowledge Core Task 6I — MindsHub/Cowork Wrapper Integration

Date: 2026-09-16

## Deterministic implementation checkpoint

- Behavior/test checkpoint: `9258a9d54cdcf2be382c27a9e875210c30abac99`.
- Base accepted Task 6H merge: `0533d643861a7a4f686f983d9ff1d3e97bacf345`.
- Pull request: #18, `KC Task 6I: MindsHub Cowork wrapper integration`.
- Deterministic qualification: GitHub Actions `35066768385`, fully green on the exact checkpoint.

This is an implementation/CI checkpoint, not live Mason/Cowork acceptance. Repository execution authority remains disabled, and no local model/provider was invoked by this qualification.

## Implemented behavior

### Mason -> KC memory boundary

Both the packaged and project-local Mason bridges now expose five literal operations:

- `kc_status`;
- `kc_search`;
- `kc_get_source`;
- `kc_store`;
- `kc_propose_memory`.

`kc_propose_memory` routes to `POST /v1/kc/memory-candidates`. The bridge supplies `proposer_ref="mason"`; model input cannot supply or override proposer identity. Proposal idempotency uses a separate `mason-kc-memory-v1:` digest namespace from explicit `kc_store`.

The wrapper keeps explicit store and autonomous proposal as different methods. It does not silently convert either intent into the other. Explicit store remains subject to the accepted Task 6G exact canonical-store authority gate. Autonomous proposal remains non-canonical.

### Local Cowork endpoint wrapper

`knowledge_core.integrations.cowork_wrapper` implements the current local Cowork REST shape used by this task:

- loopback HTTP only;
- base path exactly `/api/v1`;
- `POST /conversations` for new conversations;
- `POST /responses` with `stream=false` for bounded JSON turns;
- optional project/model/skill identifiers supplied by trusted wrapper configuration;
- response normalization with bounded status and usage parsing.

The wrapper does not call Cowork `/memories`.

### Context rotation

Task 6H compaction is integrated as explicit conversation rotation rather than appending a summary to the same Cowork conversation.

A caller may configure an explicit `ContextRotationPolicy` with a context limit and lower compaction trigger. The wrapper compares the observed Cowork input+output token usage to that trigger. When the caller supplies an accepted `WorkingContextCheckpoint`, the wrapper creates a new Cowork conversation whose goal contains the deterministic checkpoint and then switches subsequent turns to that new conversation ID.

Rotation fails if Cowork returns the same conversation ID. The wrapper does not synthesize the checkpoint itself and does not guess omitted history.

### Mason procedural skill

The skill now teaches:

- all five literal bridge operations;
- current Task 6F `kc_status.graph` semantics;
- explicit user-directed canonical store versus autonomous non-canonical proposal;
- prohibition on Cowork/MindsHub native memory as a bypass around KC governance;
- Task 6H checkpoint continuation semantics and exact raw-output-reference discipline.

## Qualification history

Actions `35066634113` failed only because a historical Task 6E skill test still required the pre-Task-6F sentence `Do not claim graph readiness from this response`. Task 6F had already superseded that requirement by adding bounded graph readiness to `kc_status`.

The stale assertion was updated to the already-accepted Task 6F contract; no new wrapper behavior was changed by that correction. Actions `35066768385` then passed:

1. PostgreSQL migrations;
2. fast semantic suite, including Task 6I bridge/Cowork/context-rotation tests;
3. PostgreSQL G1–G21 qualification suite;
4. pinned SR-2 G22 real-document pilot;
5. RI-4 local-host restart rehearsal;
6. SR-2 local-host segment restart/replay rehearsal.

## Explicit non-scope / remaining acceptance barrier

This checkpoint does not prove:

- that the user's installed Cowork build accepts these calls at runtime;
- that Mason receives the intended model/skill configuration;
- that Cowork usage accounting behaves as expected on the intended host;
- that conversation rotation materially improves Mason instruction adherence;
- that the real bridge can reach the running KC service from Mason's project workspace;
- that `kc_propose_memory` is correctly used by the live model rather than `kc_store` for autonomous observations;
- Task 6J comparative quality results.

Task 6I therefore remains **live-host acceptance pending**. The next action is a bounded intended-host Cowork/Mason qualification using this exact implementation. Do not advance to Task 6J until that host path is separately accepted.