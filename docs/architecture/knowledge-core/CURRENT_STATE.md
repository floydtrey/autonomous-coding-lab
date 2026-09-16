# Knowledge Core — Current State

**Authoritative KC status and restart point. Updated 2026-09-15.**

Branch family: `architecture/knowledge-core`.
Accepted Task 5 merge baseline: `748815927631f512a30ecb70347d6c9476608156`.
Current bounded work branch: `architecture/knowledge-core-task6a-state-reconciliation`.

## Read order and authority

After the repository [agent rules](../../../AGENTS.md), read these three current KC documents:

1. **This document** — accepted status, unresolved qualification, and exact restart boundary.
2. [ARCHITECTURE.md](ARCHITECTURE.md) — current invariants and service/consumer contracts.
3. [OPERATIONS.md](OPERATIONS.md) — development, qualification, evidence index, and checkpoint rules.

These are the only current KC authorities. [legacy/](legacy/README.md) preserves frozen historical records and accepted evidence; old status/next-task prose there is not current instruction.

[Root current state](../../CURRENT_STATE.md) governs ACL execution authority. KC supplies informational evidence only. ACL remains **DISABLED**; KC work does not activate ACL execution.

## Current accepted boundary

| Area | Current boundary |
|---|---|
| Kernel / PostgreSQL | Accepted canonical history, identity, immutable evidence, idempotency, concurrency and serving fences. |
| Governed repository import | Accepted verified Git producer feeding source-neutral governed evidence. |
| Source-neutral governed evidence | Accepted source identity, Resource/ResourceVersion, observation, decision, project membership and complete snapshot separation. |
| SR-2 text publication | Accepted source-neutral complete-corpus selection/publication with predecessor fencing and exact canonical lineage. |
| Lexical retrieval | Accepted `kc-lexical-evidence-v2` over current source-neutral SR-2 evidence with exact canonical/provenance correlation. |
| Bootstrap consumer API | Accepted local `kc_store`, `kc_search`, `kc_get_source`, and `kc_status` through explicit `BootstrapAdmission` and fixed bootstrap principal `local_owner`. |
| Direct-note storage | Accepted canonical-first `user_note` ingestion; derived text failure does not erase canonical evidence or prior valid serving state. |
| Historical governed Graphiti | Accepted repository-shaped Graphiti qualification at `6376419e369ea9ecfe58a19fa233bbfca90ad703`. This remains historical evidence for that exact build only. |
| Source-neutral Graphiti implementation | Implemented and CI-qualified through Task 4 plus Task 4.1 runtime hardening; merged into the KC line. **Live intended-host mixed-source acceptance remains pending.** |
| Mason / MindsHub | **Task 5 accepted.** Mason reaches KC through the project-local strict bridge and the four literal operations `kc_status`, `kc_search`, `kc_get_source`, `kc_store`. |
| Public graph consumer surface | Not exposed. Current Mason `kc_search` remains lexical-only. Trusted graph retrieval exists behind the application kernel/operator path. |
| Vera | Future consumer work. |

Acceptance is bounded to recorded evidence. It is not a claim of production deployment, comprehensive answer quality, machine reboot/backup qualification, or qualification of future files/configurations.

## Task 4 / Graphiti status — implementation merged, live acceptance pending

Task 4 generalized graph planning and correlation to current source-neutral SR-2 evidence. The implementation checkpoint is recorded in [Task 4 source-neutral graph synchronization](legacy/TASK4_SOURCE_NEUTRAL_GRAPH_IMPLEMENTATION_CHECKPOINT_2026-09-15.md).

Merged Task 4 / Task 4.1 behavior includes:

- source-neutral graph plan `kc-source-neutral-graph-plan-v1`;
- exact ResourceVersion/segment/source-observation/governance/snapshot correlation;
- deterministic reference-time policy `source-event-then-revision-then-observed-v1`;
- bounded explicit graph synchronization rather than graph work during `kc_store`;
- independent projection validation before trusted graph retrieval;
- Authority-first graph search;
- hardened serialized Falkor/Graphiti runtime and explicit async-client cleanup;
- canonical/text retrieval remaining independent of graph success.

The merged Task 4.1 checkpoint is `23a0794ff396365d0dfd124e0b4a7bbf9174c00d`.

**Remaining Task 4 acceptance barrier:** run the bounded source-neutral Graphiti/FalkorDB/local-model path on the intended host using a current mixed-source SR-2 corpus, complete independent validation, obtain at least one trusted graph result, and prove exact generic KC evidence correlation. Until that succeeds, source-neutral graph retrieval is implemented but not formally live-accepted.

This pending host qualification does not invalidate Tasks 1–3 or Task 5 because those consume the accepted canonical/lexical KC front door.

## Task 5 / Mason status — ACCEPTED

Task 5 is accepted at the merge baseline `748815927631f512a30ecb70347d6c9476608156`; its qualification record is [Task 5 Mason / MindsHub qualification](legacy/TASK5_MASON_MINDSHUB_QUALIFICATION_2026-09-15.md).

Accepted path:

```text
MindsHub/Cowork Mason
  -> Anton procedural-memory skill
  -> project-local mason_kc_bridge.py
  -> loopback KC bootstrap API
  -> accepted canonical / lexical evidence
```

The bridge exposes exactly:

```text
kc_status
kc_search
kc_get_source
kc_store
```

It does not expose SQL, artifact-store access, FalkorDB mutation, Graphiti maintenance, arbitrary HTTP, or arbitrary KC operations.

Live qualification proved Mason could invoke the KC skill, run `kc_search`, follow the returned ResourceVersion through `kc_get_source`, and recover exact canonical content. Task 5 deliberately does not depend on source-neutral Graphiti readiness.

## Current objective — Task 6: dogfood KC through Mason

The next phase is not another storage/retrieval rewrite. It is to use the accepted KC foundation through Mason and improve only the demonstrated gaps.

The intended consumer architecture is:

```text
Mason
  |
  | kc_search(query)
  v
KC unified retrieval coordinator
  |\
  | +-- accepted PostgreSQL lexical/current evidence
  |
  +---- optional validated Graphiti evidence
  |
  v
canonical correlation / lifecycle checks
  |
  v
one bounded evidence package
```

The lexical lane remains the required baseline. Graph evidence is additive and must fail/degrade independently: unavailable, stale, unvalidated or failed graph state must never make otherwise-valid canonical/text retrieval unavailable.

Do not invent a synthetic score that treats lexical and graph scores as equivalent. Preserve the two evidence lanes and their native evidence/provenance.

Do not create a second Mason graph-search tool unless a later demonstrated need justifies it. The target is to keep Mason's existing literal `kc_search` operation and improve its internal retrieval behavior.

## Task 6 bounded sequence

Work sequentially. Do not silently absorb later slices into an earlier task.

### Task 6A — authoritative-state reconciliation — CURRENT SLICE

Documentation-only reconciliation from the accepted Task 5 merge.

Scope:

- record Task 5 as accepted;
- record Task 4/4.1 implementation as merged but live intended-host qualification still pending;
- remove the stale Task 4 -> Task 5 restart instruction;
- establish the Task 6 sequence below;
- make no runtime, schema, provider, model, graph, corpus or authorization changes.

**Accept when:** current KC status has one unambiguous restart point, no current document says Mason is unimplemented, and no current document falsely claims source-neutral Task 4 live acceptance.

### Task 6B — unified retrieval contract

Define a versioned domain/API contract for one `kc_search` request returning:

- accepted lexical evidence;
- optional validated graph evidence;
- graph readiness/freshness state;
- warnings/degradation state;
- exact canonical correlation/provenance for both lanes.

No runtime wiring in 6B.

**Accept when:** the contract is explicit about fail-open-to-lexical behavior, graph trust requirements, provenance and backward compatibility with existing Mason `kc_search` consumers.

### Task 6C — unified retrieval coordinator

Add one application-level coordinator that reuses the existing lexical consumer kernel and existing validated source-neutral graph kernel. Do not build another index or graph platform.

**Accept when:** lexical-only operation is unchanged when graph evidence is unavailable; graph augmentation occurs only from validated compatible graph attempts; failures remain bounded to the graph lane.

### Task 6D — `kc_search` integration

Place the coordinator behind the existing bootstrap `/v1/kc/search` route. Keep the existing request surface and lexical fields backward compatible; graph evidence is additive.

**Accept when:** existing Task 3/5 lexical consumers still work unchanged and a graph-unavailable state does not break `kc_search`.

### Task 6E — Mason bridge / skill interpretation

Keep the literal bridge operation `kc_search`. Update Mason's KC skill/instructions only as needed to understand additive graph evidence and continue canonical follow-through through `kc_get_source`.

**Accept when:** Mason does not need direct Graphiti/FalkorDB access or a second retrieval tool.

### Task 6F — graph readiness and freshness status

Expose enough bounded status to distinguish at least:

- no graph build;
- current validated compatible graph;
- stale/incompatible graph;
- failed/pending/unvalidated graph.

Do not auto-launch graph synchronization or a local model from status/search.

### Task 6G — memory-candidate boundary

Separate autonomous worker observations from explicit trusted `kc_store` writes. Preserve direct canonical storage for explicit trusted/user-directed storage; add a bounded proposal/candidate path for self-initiated model memory.

**Accept when:** a model cannot silently turn an autonomous observation into trusted canonical memory without the defined admission/validation path.

### Task 6H — context-compaction core

Build wrapper-side working-context checkpointing and deterministic tool-output reduction. KC owns durable knowledge; the worker wrapper owns short-term working context.

A checkpoint should preserve objective, immutable constraints/evidence refs, completed work, current state, blockers, recent actions and exact source/output references.

### Task 6I — MindsHub wrapper integration

Wire context compaction/checkpointing and memory-candidate handling into the endpoint wrapper around Mason/Cowork. This is the first slice that necessarily depends on the local worker runtime for end-to-end qualification.

### Task 6J — qualification campaign

After implementation and after local benchmark/resource contention permits, qualify:

- SQL-only versus SQL+validated-graph retrieval;
- graph unavailable/stale/failure degradation;
- raw versus compacted worker context;
- autonomous memory proposal containment;
- instruction drift, retrieval quality and token/context use.

Do not claim Task 6 acceptance from implementation tests alone.

## Deferred optimization — graph eligibility classifier

Do **not** add a small model that decides which records belong in Graphiti during this first Task 6 pass.

The current graph profile is generation/profile-bound and the accepted KC source model already has durable lifecycle/governance semantics. Adding per-record graph eligibility now would require a new durable selection/version/rebuild contract before there is evidence that graph cost requires it.

If later measurements show graph construction is materially too expensive, treat selective graph eligibility as a separate bounded optimization with explicit snapshot/version semantics.

## Restart boundary

For any new KC worker/session:

1. Read `AGENTS.md`.
2. Read this file.
3. Read `ARCHITECTURE.md`.
4. Read `OPERATIONS.md` only for the bounded operating/evidence question.
5. Treat `legacy/` as evidence, not current instructions.

Current implementation branch baseline before Task 6A: `748815927631f512a30ecb70347d6c9476608156`.

**Current authorized slice:** Task 6A documentation reconciliation only.

**Next after Task 6A acceptance:** Task 6B unified retrieval contract.
