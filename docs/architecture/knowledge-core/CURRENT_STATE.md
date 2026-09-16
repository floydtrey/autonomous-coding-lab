# Knowledge Core — Current State

**Authoritative KC status and restart point. Updated 2026-09-16.**

Branch family: `architecture/knowledge-core`.
Accepted Task 5 merge baseline: `748815927631f512a30ecb70347d6c9476608156`.
Task 6A merge checkpoint: `7cb06d2e6e52e9000cdb96d26413f8f82a685982`.
Task 6B accepted implementation/test checkpoint: `e45822d116eeb087978eb62dee7770638b6393d7`; full Knowledge Core workflow Actions `35041019731` green.
Task 6C accepted implementation/test checkpoint: `5a8fac1d3a2b8caa3798a63f5df75f2a104705d0`; full Knowledge Core workflow Actions `35041876808` green.
Task 6D accepted implementation/test checkpoint: `65943a1e12dd08bf01a1e330ceb43ede1e2e6e13`; full Knowledge Core workflow Actions `35060185109` green.
Task 6E accepted skill/test checkpoint: `0902a906a5c20e48dfcb07009d68eb9f3ccf9392`; Actions `35060788601` run attempt 2 green after an unchanged-head retry of a transient final SR-2 rehearsal setup failure.
Task 6F accepted implementation/test checkpoint: `e34ca35cb1d2a31bdb7ec45d9799dd1f685c66d5`; full Knowledge Core workflow Actions `35062593583` green.
Task 6G accepted implementation/test checkpoint: `80f3804ce2c1a905c3853f9e7c507066a5ca9431`; full Knowledge Core workflow Actions `35064560448` green.

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
| Bootstrap consumer API | Accepted local `kc_store`, `kc_search`, `kc_get_source`, `kc_status`, and non-canonical `kc.memory_propose` admission through explicit `BootstrapAdmission` and fixed bootstrap principal `local_owner`. Bootstrap authentication alone is no longer sufficient for canonical `kc_store`. |
| Direct-note storage | Accepted canonical-first `user_note` ingestion for an explicitly authorized exact write. `kc_store` now additionally requires deterministic `CanonicalStoreAuthority` bound to principal, operation ID, project, content SHA-256, optional source ID, and optional source event time; absent/denied authority fails before canonical mutation. |
| Memory candidate boundary | **Task 6G accepted.** Autonomous observations may be durably proposed under `kc_control` as pending candidates and deterministically reviewed as approved/rejected without creating canonical revisions, Resource/ResourceVersion, TEXT generations, or graph work. Approval is eligibility only and never performs `kc_store`. |
| Historical governed Graphiti | Accepted repository-shaped Graphiti qualification at `6376419e369ea9ecfe58a19fa233bbfca90ad703`. This remains historical evidence for that exact build only. |
| Source-neutral Graphiti implementation | Implemented and CI-qualified through Task 4 plus Task 4.1 runtime hardening; merged into the KC line. **Live intended-host mixed-source acceptance remains pending.** |
| Mason / MindsHub | **Tasks 5 and 6E accepted.** Mason retains the same four literal bridge operations `kc_status`, `kc_search`, `kc_get_source`, `kc_store`; Task 6G does not change the bridge protocol, but bootstrap possession alone can no longer make `kc_store` canonical. Candidate-wrapper integration remains Task 6I. |
| Unified retrieval contract | **Task 6B accepted.** `kc-unified-retrieval-evidence-v1` preserves the lexical response and defines a separate optional graph lane with explicit degradation state and exact KC source correlation. |
| Unified retrieval coordinator | **Task 6C accepted.** Lexical retrieval is mandatory and runs first; optional graph augmentation reuses the existing validated source-neutral graph kernel and degrades independently without starting graph/model work. |
| Bootstrap `kc_search` unified response | **Task 6D accepted.** The existing request shape and lexical fields remain compatible; additive graph evidence/warnings now pass through the same literal `kc_search` route. No graph binding returns lexical evidence with `graph.state="disabled"`. |
| Graph readiness/freshness status | **Task 6F accepted.** `kc_status` now adds bounded graph state derived only from KC projection/validation evidence and can distinguish disabled, no-build, ready, stale, pending, unvalidated, failed, and bounded unavailable states without querying Graphiti or launching a model. |
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

Tasks 6B–6G do not remove or satisfy this barrier. They define, coordinate, expose, interpret, report, and contain the consumer path around compatible graph evidence and worker memory. They do not create or live-qualify a graph build.

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

Live Task 5 qualification proved Mason could invoke the KC skill, run `kc_search`, follow the returned ResourceVersion through `kc_get_source`, and recover exact canonical content. Task 5 deliberately does not depend on source-neutral Graphiti readiness.

Task 6D keeps the same literal `kc_search` request surface and adds graph evidence only to its response. Task 6E keeps both bridge transports unchanged and qualifies the procedural interpretation needed for that additive response: lexical results remain usable when the graph lane is non-ready; ready graph facts are derived evidence; exact or conflicting evidence follows returned `resource_version_ref` values through `kc_get_source`. Task 6E does not add a second retrieval operation or direct graph authority.

Task 6G also leaves the Mason bridge protocol unchanged, but it changes canonical write admission: successful bootstrap authentication is no longer enough for `kc_store`. The trusted host must provide a deterministic exact-write authority decision before canonical state can change. The non-canonical proposal API exists at KC now; exposing/using it through the worker wrapper is reserved for Task 6I.

## Current objective — Task 6: dogfood KC through Mason

The current consumer architecture is:

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

The lexical lane remains the required baseline. Graph evidence is additive and must fail/degrade independently: disabled, unavailable, absent, stale, pending, unvalidated or failed graph state must never make otherwise-valid canonical/text retrieval unavailable.

Do not invent a synthetic score that treats lexical and graph scores as equivalent. Preserve the two evidence lanes and their native evidence/provenance.

Do not create a second Mason graph-search tool unless a later demonstrated need justifies it. Mason's accepted protocol continues to use the literal `kc_search` operation, with `kc_get_source` for exact canonical follow-through.

For worker memory, distinguish **proposal** from **canonical write**. Autonomous observations belong in the non-canonical candidate path. An explicit trusted/user-directed write may use `kc_store` only after the exact deterministic store-authority gate succeeds.

## Task 6 bounded sequence

Work sequentially. Do not silently absorb later slices into an earlier task.

### Task 6A — authoritative-state reconciliation — ACCEPTED

Documentation-only reconciliation from the accepted Task 5 merge.

Completed scope:

- recorded Task 5 as accepted;
- recorded Task 4/4.1 implementation as merged but live intended-host qualification still pending;
- removed the stale Task 4 -> Task 5 restart instruction;
- established the Task 6 sequence below;
- made no runtime, schema, provider, model, graph, corpus or authorization changes.

Merged checkpoint: `7cb06d2e6e52e9000cdb96d26413f8f82a685982` (PR #10).

### Task 6B — unified retrieval contract — ACCEPTED

Accepted implementation/test checkpoint: `e45822d116eeb087978eb62dee7770638b6393d7`.
Qualification: [Actions 35041019731](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35041019731) green across migrations, fast semantic suite, PostgreSQL G1–G21, pinned G22, RI-4 restart rehearsal and SR-2 restart/replay rehearsal. The detailed contract record is [Task 6B unified retrieval contract](legacy/TASK6B_UNIFIED_RETRIEVAL_CONTRACT_2026-09-15.md).

Accepted contract:

- version `kc-unified-retrieval-evidence-v1`;
- all existing lexical `RetrievalSearchResponse` fields remain top-level and retain `kc-lexical-evidence-v2` semantics;
- graph evidence is additive and separately stateful;
- public graph states are `disabled`, `no_build`, `ready`, `stale`, `pending`, `unvalidated`, `failed`, and `unavailable`;
- only `ready` may return graph results;
- ready graph evidence requires namespace/scope, validated attempt identity and the exact same TEXT generation returned by the lexical lane;
- every non-ready state returns zero graph results and carries a bounded reason plus matching degradation warning;
- graph authorization details are not exposed as a distinct public state; coordination may collapse denied/unavailable graph access into nondisclosing `unavailable` while lexical authorization remains independent;
- each graph fact retains exact ResourceVersion/segment/governance/snapshot correlation but does not duplicate full canonical source text; consumers use `kc_get_source` for exact source follow-through;
- no combined lexical/graph score exists.

### Task 6C — unified retrieval coordinator — ACCEPTED

Accepted implementation/test checkpoint: `5a8fac1d3a2b8caa3798a63f5df75f2a104705d0`.
Qualification: [Actions 35041876808](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35041876808) green across migrations, fast semantic suite, PostgreSQL G1–G21, pinned G22, RI-4 restart rehearsal and SR-2 restart/replay rehearsal. Detailed evidence is [Task 6C unified retrieval coordinator](legacy/TASK6C_UNIFIED_RETRIEVAL_COORDINATOR_2026-09-15.md).

Accepted coordinator behavior:

- lexical retrieval executes first and outside graph-degradation handling; a lexical trust/serving failure still fails the request;
- optional graph augmentation requires explicit host injection of adapter, retrieval Authority seam, caller principal, namespace and scope;
- no graph binding produces lexical evidence plus `graph.state="disabled"` without graph access;
- `include_superseded=True` remains lexical-only because the accepted graph path is current-only;
- no current TEXT generation produces `no_build` without graph access;
- graph search reuses `SourceNeutralGraphProjectionKnowledgeKernel.search_validated_projection()` rather than duplicating validation/correlation logic;
- graph generation mismatch with the lexical snapshot produces `stale` and zero graph results;
- no compatible validated attempt IDs produces nondisclosing `unavailable`, not `no_build`, because trusted search cannot distinguish absent vs stale/pending/failed/unvalidated durable builds; Task 6F owns that later classification;
- ordinary graph provider/Authority/integrity/mapping exceptions degrade to nondisclosing `unavailable` while valid lexical evidence remains usable;
- ready graph hits must retain source-neutral `GovernedProjectionSourceSegment` correlation and omit provider source body/full canonical content;
- the graph lane uses the normalized lexical snapshot query;
- the coordinator does not synchronize Graphiti, start a provider/model, mutate graph state, or create background work.

An earlier qualification run, Actions `35041771603`, stopped with 169 fast tests passed and one incorrect focused assertion. The assertion expected the raw caller query despite the fake lexical snapshot containing a different normalized query. Coordinator behavior was unchanged; the corrected test now verifies use of the lexical snapshot query.

### Task 6D — `kc_search` integration — ACCEPTED

Accepted implementation/test checkpoint: `65943a1e12dd08bf01a1e330ceb43ede1e2e6e13`.
Qualification: [Actions 35060185109](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35060185109) green across migrations, fast semantic suite, PostgreSQL G1–G21, pinned G22, RI-4 restart rehearsal and SR-2 restart/replay rehearsal. Detailed evidence is [Task 6D `kc_search` integration](legacy/TASK6D_KC_SEARCH_INTEGRATION_2026-09-16.md).

Accepted endpoint behavior:

- the bootstrap `POST /v1/kc/search` request remains the existing `query` / `limit` / `include_superseded` request;
- every previously accepted lexical response field remains top-level with `kc-lexical-evidence-v2` semantics;
- the additive response now also carries `kc-unified-retrieval-evidence-v1`, `graph`, and `warnings`;
- the route constructs the accepted Task 6C coordinator rather than duplicating lexical or graph trust logic;
- no graph binding returns valid lexical evidence plus `graph.state="disabled"` and does not call graph retrieval;
- an explicitly injected graph binding may return ready trusted graph evidence through the same literal `kc_search` operation;
- the graph binding caller principal must exactly match the bootstrap principal `local_owner`; application composition rejects a mismatched principal;
- when a separate text retrieval Authority evaluator is configured, `retrieval.search_text` remains an additional fail-closed pre-check before lexical retrieval;
- `/v1/retrieval/search`, `kc_store`, `kc_get_source`, and `kc_status` remain outside the Task 6D behavior change;
- no graph sync, model launch, provider discovery, scheduler, migration, or score fusion was added.

### Task 6E — Mason bridge / skill interpretation — ACCEPTED

Accepted skill/test checkpoint: `0902a906a5c20e48dfcb07009d68eb9f3ccf9392`.
Qualification: Actions `35060788601`, run attempt 2, green across migrations, fast semantic suite, PostgreSQL G1–G21, pinned G22, RI-4 restart rehearsal and SR-2 restart/replay rehearsal. Detailed evidence, including the unchanged-head transient failure and retry, is [Task 6E Mason unified interpretation](legacy/TASK6E_MASON_UNIFIED_INTERPRETATION_2026-09-16.md).

Accepted behavior:

- both existing bridge transports remain unchanged and preserve the complete additive `kc_search` JSON response;
- the skill keeps exactly `kc_status`, `kc_search`, `kc_get_source`, and `kc_store` as literal bridge operations;
- lexical and graph results are separate evidence lanes;
- non-ready graph state does not invalidate otherwise-relevant lexical evidence;
- ready graph facts are derived retrieval evidence, not canonical source wording;
- exact wording, provenance, conflict resolution and verification follow returned `resource_version_ref` values through `kc_get_source`;
- `kc_status` is not treated as graph readiness before Task 6F;
- no direct Graphiti/FalkorDB/raw HTTP/SQL/filesystem fallback or second graph-search operation is permitted.

Actions `35060788601` attempt 1 passed the Task 6E fast suite, PostgreSQL G1–G21, G22 and RI-4 but its final SR-2 rehearsal failed while the unchanged SR-2 harness was preparing its fresh isolated Postgres database (`alembic upgrade head` returned non-zero before SR-2 apply/recovery). No Task 6E code changed. The exact-head job rerun (attempt 2) passed every gate, so the first final-step failure is retained as transient qualification infrastructure rather than a behavior defect.

Task 6E deterministic acceptance does not claim a live Mason/Cowork behavior campaign; that remains Task 6J unless separately authorized earlier.

### Task 6F — graph readiness and freshness status — ACCEPTED

Accepted implementation/test checkpoint: `e34ca35cb1d2a31bdb7ec45d9799dd1f685c66d5`.
Qualification: [Actions 35062593583](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35062593583) green across migrations, fast semantic suite, PostgreSQL G1–G21, pinned G22, RI-4 restart rehearsal and SR-2 restart/replay rehearsal. Detailed evidence is [Task 6F graph readiness status](legacy/TASK6F_GRAPH_READINESS_STATUS_2026-09-16.md).

Accepted behavior:

- `GET /v1/kc/status` preserves the existing canonical/text fields and adds a bounded `graph` object using the established public graph states;
- no graph binding reports `disabled` without reading provider or projection state;
- configured graph readiness is derived only from KC's durable projection-attempt and validation ledger plus the current TEXT generation/profile and the injected adapter descriptor;
- the classifier distinguishes `no_build`, `ready`, `stale`, `pending`, `unvalidated`, and `failed`; unexpected readiness-inspection failure degrades only graph status to nondisclosing `unavailable`;
- a `ready` build must be succeeded, validated, current-profile/current-config compatible, and satisfy the adapter's current independent validation requirement when one exists;
- status exposes at most one representative attempt ID so historical attempt volume cannot make the response unbounded;
- an existing ready build wins over simultaneous pending/failed attempts because trusted retrieval can still use the ready build;
- `kc_status` does not call `adapter.search()`, project/synchronize Graphiti, query FalkorDB for facts, invoke embeddings/reranking, launch a provider/model, or create background work;
- graph readiness does not weaken or replace canonical/text readiness and does not satisfy the still-pending Task 4 intended-host mixed-source Graphiti acceptance barrier.

### Task 6G — memory-candidate boundary — ACCEPTED

Accepted implementation/test checkpoint: `80f3804ce2c1a905c3853f9e7c507066a5ca9431`.
Qualification: [Actions 35064560448](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35064560448) green across migration, fast semantic suite, PostgreSQL G1–G21, pinned G22, RI-4 restart rehearsal and SR-2 restart/replay rehearsal. Detailed evidence is [Task 6G memory candidate boundary](legacy/TASK6G_MEMORY_CANDIDATE_BOUNDARY_2026-09-16.md).

Accepted behavior:

- autonomous/self-initiated observations have a durable non-canonical `kc_control.memory_candidate` path instead of being treated as `user_note` canonical knowledge;
- proposal is separately bootstrap-scoped as `kc.memory_propose`; proposal/review operations create no canonical revision, Resource/ResourceVersion, TEXT generation, or graph work;
- candidate states are `pending`, `approved`, and `rejected`; deterministic review uses a separate trusted review evaluator, and approval is eligibility only—it never invokes or implies `kc_store`;
- there is no public review/promote endpoint and no automatic promotion in Task 6G;
- canonical `kc_store` remains available for explicit trusted/user-directed storage but now requires both bootstrap admission and a separate fail-closed `CanonicalStoreAuthorityEvaluator` before any canonical mutation;
- the exact store-authority request is bound to caller principal, deterministic operation ID, project, content SHA-256, optional source ID, and optional timezone-aware source event time;
- missing authority returns bounded unavailable before writes; denied authority returns bounded denial before writes;
- Task 6G does not change the Mason bridge protocol, add a worker-visible proposal operation, perform context compaction, launch a model/provider, or change graph behavior. Worker-wrapper proposal routing is Task 6I.

The first Task 6G green implementation head `9597da247beb4924cc3618c3da151e2d03ea5573` proved the containment design. Review then found that the exact canonical-store authority request did not yet bind optional `source_event_time`, even though that timestamp becomes durable provenance and influences graph reference-time policy. The authority request, API binding, and focused fast test were corrected without changing the candidate model, and the complete KC workflow was rerun green on the accepted head above.

### Task 6H — context-compaction core — NEXT AUTHORIZED SLICE

Build wrapper-side working-context checkpointing and deterministic tool-output reduction. KC owns durable knowledge; the worker wrapper owns short-term working context.

A checkpoint should preserve objective, immutable constraints/evidence refs, completed work, current state, blockers, recent actions and exact source/output references.

Do not wire the compaction core into MindsHub/Cowork in Task 6H; integration is Task 6I.

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

Task 6G's accepted behavior-bearing checkpoint is `80f3804ce2c1a905c3853f9e7c507066a5ca9431`, qualified by Actions `35064560448`. Later Task 6G documentation records do not change the qualified candidate/authority bytes.

**Current authorized slice:** Task 6H context-compaction core.

Do not begin Task 6I MindsHub-wrapper integration until Task 6H is separately accepted.
