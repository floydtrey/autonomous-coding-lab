# Knowledge Core — Operations and Evidence

**Authoritative current KC operating reference.** Start with [CURRENT_STATE.md](CURRENT_STATE.md) and preserve [ARCHITECTURE.md](ARCHITECTURE.md). This document distinguishes recorded acceptance from commands for future authorized work.

## Development and verification

Work from `components/knowledge-core` with Python 3.12+ and an appropriate environment:

```powershell
python -m pip install -e ".[test]"
python -m pytest -q -m "not postgresql and not sr2_real_pilot"
```

For database qualification, use a dedicated disposable PostgreSQL database. The test fixtures truncate KC application schemas. Set `KNOWLEDGE_CORE_DATABASE_URL` and, where applicable, `KNOWLEDGE_CORE_POSTGRES_TEST_URL`, then use the existing ordered gates:

```powershell
python -m alembic upgrade head
python -m pytest -q -m "postgresql and not sr2_real_pilot"
python -m pytest -q -m "sr2_real_pilot"
```

G22 remains separate from G1–G21. Preserve full Git history for exact pinned corpus objects. The [KC workflow](../../../.github/workflows/knowledge-core.yml) applies migrations, runs fast/PostgreSQL/G22 selectors and rehearses RI-4 and SR-2 restart tools. CI rehearsal is not a substitute for separately required intended-host evidence.

The older RF-2 exact-corpus pilot deliberately skips when current checkout bytes differ from its pinned corpus. Do not rewrite historical manifests or relabel evidence to make old qualification appear current.

For documentation-only changes, verify scope, links/read order, unchanged evidence blobs, manifest pins and non-document bytes. Do not run models, mutate canonical corpus state or rerun intended-host acceptance merely to reorganize prose. For behavior changes, run the deterministic gates relevant to the changed boundary and any separately authorized host qualification required by that boundary.

## Bootstrap consumer boundary

Task 1 provides a replaceable bootstrap admission facility. It is not a deployed standalone Authority service and is not attached to every low-level KC route.

| Setting | Current meaning |
|---|---|
| `KNOWLEDGE_CORE_BIND_HOST` | Listener/deployment host selection; defaults to `127.0.0.1`. |
| `KNOWLEDGE_CORE_BOOTSTRAP_KEY` | Shared bootstrap API key. Keep the value outside source control, prompts and KC content. |
| `X-Knowledge-Key` | Request header carrying the bootstrap API key. |
| `local_owner` | Fixed bootstrap principal after successful admission. |

Accepted local consumer operations are:

| Operation | HTTP surface | Rule |
|---|---|---|
| `kc_store` | `POST /v1/kc/store` | Requires bootstrap admission plus `Idempotency-Key` **and** a separate fail-closed exact `CanonicalStoreAuthority` decision before canonical mutation. The authority request binds principal, operation ID, project, content SHA-256, optional source ID and optional source event time. |
| `kc.memory_propose` | `POST /v1/kc/memory-candidates` | Separately bootstrap-scoped non-canonical proposal path. Creates only pending candidate/control evidence; it does not create canonical revisions, retrieval generations, or graph work. |
| `kc_search` | `POST /v1/kc/search` | Uses the accepted lexical-first unified coordinator. Existing lexical fields remain top-level; additive `graph`/`warnings` follow `kc-unified-retrieval-evidence-v1`. No graph binding returns lexical evidence with `graph.state="disabled"`. |
| `kc_get_source` | `POST /v1/kc/get-source` | Accepts an exact current-generation `resource_version_ref`; revalidates eligibility and immutable source size/SHA-256/UTF-8. |
| `kc_status` | `GET /v1/kc/status` | Preserves bounded canonical/text readiness and adds bounded graph readiness/freshness derived only from KC durable projection/validation evidence. Status does not query/build Graphiti or launch a model. |

Caller-supplied `X-Knowledge-Caller` does not override the bootstrap principal. The preexisting `/v1/retrieval/search` route remains separate and requires its retrieval Authority evaluator.

Bootstrap admission is an authentication/admission layer, not proof of permission for an exact canonical write. Task 6G deliberately makes `kc_store` fail closed when the trusted host does not supply an exact `CanonicalStoreAuthorityEvaluator` decision. Do not install a blanket allow evaluator for an autonomous worker and then describe the resulting writes as user-directed.

If a trusted host supplies `UnifiedGraphSearchBinding` to the composed API, the binding caller principal must exactly match bootstrap `local_owner`. The binding is query-only: it does not authorize graph mutation, provider discovery, synchronization, model launch or background work. If a separate lexical retrieval Authority evaluator is supplied, bootstrap `kc_search` still evaluates `retrieval.search_text` before lexical retrieval.

Do not use bootstrap admission as justification to expose arbitrary entity/assertion/resource CRUD, unrestricted historical source lookup, raw SQL, database credentials, artifact-store authority, FalkorDB credentials, direct Graphiti mutation or remote access.

## Source-neutral evidence and lexical serving

Tasks 2A–2F establish the accepted source-neutral path from producer-specific proof through canonical ResourceVersion, generic governed observation/decision, complete governed snapshot, SR-2 publication and lexical serving.

Operating rules include:

- repository commit/path/blob/manifest verification remains inside the Git producer;
- direct `user_note` evidence is an explicitly authorized local-owner submission plus exact canonical byte custody, not fabricated Git proof;
- source identity, canonical Resource/Version, observation, governance decision, project membership and corpus snapshot remain distinct;
- complete-corpus snapshots feed the one-current-TEXT boundary; producer-local subsets do not replace unrelated current sources;
- publication rechecks predecessor state so stale writers cannot erase newer contributions;
- canonical note evidence settles before derived publication; text failure/pending state does not erase canonical evidence or prior valid serving state;
- current source-neutral SR-2 lexical reads require complete generic lineage and exact canonical artifact/slice verification before serving;
- restriction/erasure eligibility is rechecked at serve time and dominates stale derived rows;
- repository compatibility fields exist only when exact legacy mapping exists; non-Git sources do not receive fabricated repository identity;
- historical RF-2/pre-source-neutral evidence retains its original explicit interpretation.

The public lexical response advertises `evidence_contract_version="kc-lexical-evidence-v2"`; current source-neutral SR-2 segment provenance advertises `governed-source-sr2-v2`.

## Direct-note storage and memory-candidate operating rule

`kc_store` means explicit trusted canonical storage. It is not a generic permission for a model to self-author durable memory.

The canonical request accepts `content`, `project`, `source_type="user_note"`, optional stable `source_id` and optional timezone-aware `source_event_time`. Exact retry with the same idempotency identity converges on the same canonical source/Resource/ResourceVersion/observation/decision evidence; reusing the identity with different inputs fails.

After Task 6G, successful bootstrap authentication is necessary but not sufficient for `kc_store`. Before `DirectNoteStoreKnowledgeKernel` is allowed to mutate canonical state, the API requires an exact `CanonicalStoreAuthorityEvaluator` allow decision bound to the authenticated principal, deterministic operation ID, project, content SHA-256, optional source ID and optional source event time. Missing authority returns bounded unavailable; explicit denial returns bounded denial; both occur before canonical mutation.

Autonomous/self-initiated observations use the separate memory-candidate boundary. `POST /v1/kc/memory-candidates` stores a bounded proposal only in `kc_control` under the `kc.memory_propose` bootstrap operation. Candidate proposal and deterministic review do not create canonical revisions, Resources/ResourceVersions, TEXT generations or graph work.

Candidate review states are `pending`, `approved`, and `rejected`. Review uses a separate trusted evaluator. `approved` means only eligible for a later explicit trusted store decision; review never calls or implies `kc_store`. Task 6G exposes no public review/promote route and no automatic promotion. The detailed accepted record is [Task 6G memory candidate boundary](legacy/TASK6G_MEMORY_CANDIDATE_BOUNDARY_2026-09-16.md).

The Mason bridge itself is not changed by Task 6G. Its historical `kc_store` operation therefore still exists, but bridge/bootstrap possession alone cannot make a write canonical. Task 6I owns worker-wrapper proposal routing and exact user-intent store integration.

## Graphiti operator boundary

Install the optional graph dependency with:

```powershell
python -m pip install -e ".[test,graphiti]"
```

The current adapter line pins `graphiti-core[falkordb]==0.30.2`.

Historical accepted Graphiti evidence at `6376419e369ea9ecfe58a19fa233bbfca90ad703` is repository-shaped and remains valid only for its exact recorded build.

Task 4 adds the source-neutral bounded operator path under `components/knowledge-core/tools/`:

| Tool | Purpose |
|---|---|
| `graphiti_source_neutral_sync.py` | Build/list source-neutral current SR-2 plan, project a bounded selection, independently validate, then run Authority-first trusted search. |
| `graphiti_source_neutral_sync_hardened.py` | Reuses the Task 4 flow with the Task 4.1 serialized/hardened Graphiti/Falkor adapter. This is the intended local-runtime entrypoint after Task 4.1. |
| `graphiti_host_phase.py` | Historical governed-document host flow retained for its accepted scope. |
| `sr2_host_qualification.py` | Bounded SR-2 restart/recovery with pinned G22 corpus. |
| `ri4_host_qualification.py` | Historical RI-4 restart/recovery harness. |

The Task 4 source-neutral plan is generation/profile-bound and carries exact generic KC source/observation/decision/snapshot/segment evidence. Non-Git sources receive no fabricated Git metadata. Reference time follows `source-event-then-revision-then-observed-v1`.

Graph synchronization is explicit. It is not part of `kc_store`, not launched by `kc_search`, and does not create a scheduler, background queue or automatic GPU/model orchestrator.

Inspect durable attempt/validation/binding evidence before recovery. Exact settled replay does not reproject. Changing attempt salt intentionally creates another attempt/build and is a recovery decision, not a casual retry. Preserve failed, incomplete, pending and quarantined evidence.

Trusted graph retrieval requires:

1. successful compatible projection;
2. complete independent validation;
3. Authority-first retrieval;
4. exact source bindings/canonical correlation;
5. current compatible generation/profile/config and serving eligibility.

Provider success without independent validation is not trusted retrieval.

### Task 4 qualification status

Task 4 implementation and deterministic CI qualification are merged. Task 4.1 hardened runtime is merged at `23a0794ff396365d0dfd124e0b4a7bbf9174c00d`.

The source-neutral mixed-source path is **not yet formally live-accepted**. The remaining barrier is the bounded intended-host Graphiti/FalkorDB/local-model run followed by independent validation and at least one trusted graph result with exact generic KC correlation.

Tasks 6B–6G do not satisfy that host barrier. They define, expose, interpret, report, and contain consumer behavior around a current compatible validated build; none creates or live-qualifies that graph build.

## Mason / MindsHub operating boundary — Tasks 5, 6E and 6G relevant

Task 5 accepts the project-local Mason -> KC path recorded in [Task 5 qualification](legacy/TASK5_MASON_MINDSHUB_QUALIFICATION_2026-09-15.md).

Accepted path:

```text
MindsHub/Cowork Mason
  -> Anton procedural-memory `knowledge-core` skill
  -> project-local `mason_kc_bridge.py`
  -> loopback KC bootstrap API
  -> canonical / unified retrieval evidence
```

The bridge exposes exactly these literal protocol operations:

```text
kc_status
kc_search
kc_get_source
kc_store
```

Do not shorten/alias the operation identifiers. Unsupported operations fail closed. The bridge does not expose SQL, FalkorDB mutation, Graphiti maintenance, artifact-store access, arbitrary HTTP or arbitrary KC operations.

Task 5 qualification proved a fresh Mason session could call the KC skill, perform `kc_search`, follow the ResourceVersion through `kc_get_source`, and return exact canonical content. Task 6D keeps the same `kc_search` request/operation and changes the response only additively.

Task 6E leaves both bridge transports unchanged because both already preserve additive JSON responses. The accepted skill procedure now treats lexical and graph results as separate evidence lanes. A non-ready graph state does not invalidate otherwise-valid lexical evidence. A ready graph fact is derived evidence, not canonical wording. When exact wording, provenance or conflict resolution matters, follow the relevant returned `resource_version_ref` through `kc_get_source`.

Task 6F makes the existing `kc_status` operation a bounded graph-readiness surface as well as a canonical/text-readiness surface. Mason still receives no graph maintenance operation, provider credentials, or direct Graphiti/FalkorDB access.

Task 6G leaves the bridge protocol unchanged but removes bootstrap-only canonical-write authority. A worker can no longer turn its own observation into canonical memory merely by invoking the historical `kc_store` bridge operation: the host must independently authorize the exact write. The new non-canonical proposal API is intentionally not wired into Mason in 6G; that integration belongs to Task 6I.

## Unified retrieval and graph status operating contract — Tasks 6B–6F accepted

Task 6B defines `kc-unified-retrieval-evidence-v1`; Task 6C provides the qualified application-level coordinator; Task 6D places that coordinator behind the existing bootstrap `POST /v1/kc/search` route; Task 6E qualifies deterministic Mason bridge passthrough and interpretation of the additive response; Task 6F adds bounded graph readiness/freshness to the existing `GET /v1/kc/status` route.

The unified search contract preserves every accepted lexical response field and its `kc-lexical-evidence-v2` meaning. It adds a separately stateful graph lane and bounded degradation warnings.

Public graph states are:

- `disabled`
- `no_build`
- `ready`
- `stale`
- `pending`
- `unvalidated`
- `failed`
- `unavailable`

Only `ready` may contain graph results. A ready search lane must identify explicit namespace/scope, one or more validated attempt IDs and the exact same TEXT generation as the lexical snapshot. Every non-ready search graph lane returns zero graph results and requires a bounded reason code plus the matching warning.

Do not expose graph authorization denial as a distinct public state. The accepted coordinator maps denied/unreachable graph access to nondisclosing `unavailable`; it does not use graph degradation to weaken lexical authorization.

Graph hits carry exact canonical correlation but not duplicated full source text. Consumers use the returned `resource_version_ref` with `kc_get_source` when exact content is required.

Do not create a combined lexical/graph score. The accepted contract does not define a graph score or a fusion/reranking policy.

Accepted coordinator/endpoint/consumer behavior:

- lexical retrieval runs first through the existing consumer-read kernel and retains its existing failure semantics;
- graph augmentation is optional and uses the existing validated source-neutral graph retrieval kernel rather than another index or graph implementation;
- only current, same-TEXT-generation graph evidence may augment the response;
- historical `include_superseded` search remains lexical-only rather than mixing historical lexical evidence with current graph facts;
- no compatible validated graph attempt, graph Authority/provider/integrity failure, or generation mismatch degrades only the graph lane and preserves valid lexical evidence;
- graph result mapping keeps exact source-neutral KC correlation and does not expose provider source body/content;
- provider/Authority/namespace/scope are explicit host-injected dependencies;
- the bootstrap route request remains `query`, `limit`, `include_superseded`; existing lexical fields remain top-level;
- no graph binding returns additive `graph.state="disabled"` without a graph call;
- graph binding principal must equal bootstrap `local_owner`;
- a separately configured text retrieval Authority evaluator remains fail-closed before lexical retrieval;
- `/v1/retrieval/search` and `kc_get_source` are not redefined by Tasks 6B–6F; Task 6G separately hardens `kc_store` authority;
- both Mason bridges pass the additive search/status response fields through unchanged;
- Mason's accepted skill uses valid lexical evidence when graph is non-ready, treats ready graph facts as derived evidence, and uses `kc_get_source` for exact canonical follow-through;
- the coordinator/endpoint/consumer procedure does not discover providers, synchronize Graphiti, launch a model, start a scheduler, or mutate graph state.

Accepted Task 6F status behavior:

- no graph binding returns `graph.state="disabled"` without reading graph/provider state;
- configured readiness is classified from KC's durable projection-attempt/validation ledger, current TEXT generation/profile, and injected adapter descriptor;
- current-compatible succeeded+validated attempts must also satisfy the adapter's current independent validation requirement when one exists;
- a usable ready build wins over simultaneous pending/failed attempts;
- absent durable build is `no_build`; incompatible historical build is `stale`; current compatible nonterminal/untrusted evidence distinguishes `pending`, `unvalidated`, and `failed`;
- unexpected readiness-inspection failure becomes nondisclosing `unavailable` without erasing canonical/text status;
- status exposes at most one representative attempt ID;
- readiness inspection never calls graph search/projection, FalkorDB fact retrieval, embeddings/reranking, or a local model, and never starts graph synchronization/background work;
- status `ready` is durable KC build/validation readiness, not proof of current provider liveness.

Task 6C implementation/test checkpoint `5a8fac1d3a2b8caa3798a63f5df75f2a104705d0` passed the complete Knowledge Core workflow in Actions `35041876808`. The detailed record is [Task 6C unified retrieval coordinator](legacy/TASK6C_UNIFIED_RETRIEVAL_COORDINATOR_2026-09-15.md).

Task 6D implementation/test checkpoint `65943a1e12dd08bf01a1e330ceb43ede1e2e6e13` passed the complete Knowledge Core workflow in Actions `35060185109`. The detailed record is [Task 6D `kc_search` integration](legacy/TASK6D_KC_SEARCH_INTEGRATION_2026-09-16.md).

Task 6E skill/test checkpoint `0902a906a5c20e48dfcb07009d68eb9f3ccf9392` is accepted from Actions `35060788601` run attempt 2. Attempt 1 had already passed the Task 6E fast tests, PostgreSQL G1–G21, G22 and RI-4 before the unchanged SR-2 host harness failed while migrating its fresh isolated Postgres database. No Task 6E code changed; attempt 2 reran the exact same head and passed all gates including SR-2 restart/replay. The detailed record is [Task 6E Mason unified interpretation](legacy/TASK6E_MASON_UNIFIED_INTERPRETATION_2026-09-16.md).

Task 6F implementation/test checkpoint `e34ca35cb1d2a31bdb7ec45d9799dd1f685c66d5` passed the complete Knowledge Core workflow in Actions `35062593583`. The detailed record is [Task 6F graph readiness status](legacy/TASK6F_GRAPH_READINESS_STATUS_2026-09-16.md).

Task 6G implementation/test checkpoint `80f3804ce2c1a905c3853f9e7c507066a5ca9431` passed the complete Knowledge Core workflow in Actions `35064560448`. The detailed record is [Task 6G memory candidate boundary](legacy/TASK6G_MEMORY_CANDIDATE_BOUNDARY_2026-09-16.md). This accepted checkpoint includes the post-review correction that binds optional `source_event_time` into the exact canonical-store authority request.

This acceptance qualifies deterministic contract/coordinator/bootstrap endpoint/bridge/status/memory-containment behavior only. It does not establish source-neutral Task 4 intended-host Graphiti acceptance, current graph-provider liveness, or a live Task 6J Mason quality campaign.

## Task 6 operating sequence

The current phase is Task 6 dogfooding. Follow [CURRENT_STATE.md](CURRENT_STATE.md) for the exact authorized slice.

The intended sequence is:

- 6A reconcile authoritative state — accepted;
- 6B define unified lexical + optional validated-graph retrieval contract — accepted;
- 6C implement the coordinator by reusing existing lexical and graph kernels — accepted;
- 6D place it behind existing `kc_search` without breaking Task 3/5 consumers — accepted;
- 6E update Mason interpretation without adding direct graph authority — accepted;
- 6F expose bounded graph readiness/freshness state — accepted;
- 6G separate autonomous memory proposals from explicit canonical `kc_store` — accepted;
- 6H build wrapper-side context compaction/checkpointing — current authorized slice;
- 6I integrate compaction/proposals with MindsHub wrapper;
- 6J run intended-host/worker qualification after resource contention permits.

Do not auto-run local models merely because implementation code is ready. In particular, graph synchronization and Task 6J qualification remain explicit operator actions.

## Accepted evidence

These are recorded checkpoints. Historical files retain their exact scope; [CURRENT_STATE.md](CURRENT_STATE.md) controls current interpretation.

| Boundary | Exact checkpoint / evidence | Accepted scope |
|---|---|---|
| Kernel V1 | `9e904f49480055615bb0cf32360dbdc8400e117c`; [completion](legacy/IMPLEMENTATION_PLAN_V1.md) | Gates 1–19; frozen kernel semantics. |
| PostgreSQL | `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`; [record](legacy/POSTGRES_QUALIFICATION.md) | Real migrations, locking/races, idempotency, rollback and generation fencing. |
| RF-2 | `479a918762e919851e19fee3b36cc1d95e78f3e8`; [record](legacy/RETRIEVAL_FOUNDATION_RF2.md) | Historical whole-document lexical retrieval. |
| RI-2 | `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`; [record](legacy/REPOSITORY_IMPORT_RI2.md) | Bounded governed repository import. |
| RI-3 / RI-4 | [RI-3](legacy/REPOSITORY_IMPORT_RI3.md), [RI-4](legacy/REPOSITORY_IMPORT_RI4.md), [host evidence](legacy/RI4_INTENDED_HOST_EVIDENCE.md) | Durable reconstruction and historical intended-host replay evidence. |
| SR-2 G1–G21 | `7570425231c0f1804c800ad4c6809f6261d82416`; [coverage](legacy/SR2_G1_G21_COVERAGE_MATRIX.md) | Accepted prerequisite coverage. |
| SR-2 G22 | `c75a6be2e832bdc29fda0e4a6eab7de28da90668`; [record](legacy/SR2_G22_QUALIFICATION.md) | Tiny pinned three-document pilot; G1–G22 accepted. |
| SR-2 intended host | `c3bfac41eb3a1787d5b770274370b5e59f082eb4`; [record](legacy/SR2_INTENDED_HOST_QUALIFICATION.md) | Windows restart/recovery, serving and exact provenance/integrity. |
| Historical governed Graphiti | `6376419e369ea9ecfe58a19fa233bbfca90ad703`; [record](legacy/GRAPHITI_GOVERNED_QUALIFICATION_2026-09-14.md) | Repository-shaped governed projection; 17 bindings, 7 validation checks, attributed trusted results. |
| KC Task 1 | `b9e708f2892f3a7303fa50ccadc64c26f5b9bf46` | Bootstrap bind/key, `local_owner`, bounded operations. |
| KC Task 2A | `cbfecbfada73e1210ceae0185a31664bf073a479` | Source-neutral governed-source domain contract. |
| KC Task 2B | `6910e9abba320e272b34b0528846f289d3d8eb14` | Durable generic evidence/snapshot persistence. |
| KC Task 2C | `30d1ec2ce13ae8c95afc4ac2b9d54d959f36b3bd` | Repository as verified producer of generic evidence. |
| KC Task 2D | `08d76ab86f011c30a103b080b7fce821bf71c45c` | Source-neutral SR-2 lineage/publication. |
| KC Task 2E | `9c89e30b9f0fa264180ac57a3e41d01ca0c74699` | Authenticated direct-note `kc_store`. |
| KC Task 2E.1 | `c0864a1d1ed76bdd5e289308f85f2b8b4d0499ba` | Audit corrections before read-side qualification. |
| KC Task 2F | `f48200f50ee1c2652e32b56592f6ad86fe83c898` | Source-neutral lexical evidence/serving. |
| KC Task 3 | `5f6cdef96c9d4fcd36db8821df9c0156148080ae` | Bootstrap `kc_search`, `kc_get_source`, `kc_status`; fresh-client lexical/source milestone. |
| KC Task 4 implementation | `8fea3d5d0200cc76018008711cea40a14b72ec13`; [checkpoint](legacy/TASK4_SOURCE_NEUTRAL_GRAPH_IMPLEMENTATION_CHECKPOINT_2026-09-15.md) | Source-neutral graph planning/sync/trusted-retrieval implementation; deterministic qualification only, not live intended-host acceptance. |
| KC Task 4.1 hardening | `23a0794ff396365d0dfd124e0b4a7bbf9174c00d` | Serialized Falkor/Graphiti runtime and hardened operator; intended-host source-neutral acceptance still pending. |
| **KC Task 5 Mason / MindsHub** | **merge `748815927631f512a30ecb70347d6c9476608156`; [qualification](legacy/TASK5_MASON_MINDSHUB_QUALIFICATION_2026-09-15.md)** | **Project-local strict four-operation Mason bridge; live skill/status and `kc_search` -> `kc_get_source` canonical retrieval accepted. Does not qualify Graphiti.** |
| **KC Task 6B unified retrieval contract** | **`e45822d116eeb087978eb62dee7770638b6393d7`; [record](legacy/TASK6B_UNIFIED_RETRIEVAL_CONTRACT_2026-09-15.md); [Actions 35041019731](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35041019731)** | **Additive `kc-unified-retrieval-evidence-v1`; lexical compatibility preserved; ready-only same-generation validated graph evidence; exact canonical graph correlation; bounded degradation; no score fusion. Contract-only, no endpoint wiring or model/Graphiti execution.** |
| **KC Task 6C unified retrieval coordinator** | **`5a8fac1d3a2b8caa3798a63f5df75f2a104705d0`; [record](legacy/TASK6C_UNIFIED_RETRIEVAL_COORDINATOR_2026-09-15.md); [Actions 35041876808](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35041876808)** | **Lexical-first coordinator reusing accepted lexical and trusted graph kernels; same-generation/current-only graph augmentation; bounded nondisclosing graph degradation; no provider discovery, sync, model launch, endpoint wiring, migration, or local-runtime qualification.** |
| **KC Task 6D `kc_search` integration** | **`65943a1e12dd08bf01a1e330ceb43ede1e2e6e13`; [record](legacy/TASK6D_KC_SEARCH_INTEGRATION_2026-09-16.md); [Actions 35060185109](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35060185109)** | **Existing bootstrap `kc_search` request and lexical fields preserved; additive unified graph/warning response wired through the accepted coordinator; graph binding principal tied to `local_owner`; no graph build/model launch/status change/migration.** |
| **KC Task 6E Mason unified interpretation** | **`0902a906a5c20e48dfcb07009d68eb9f3ccf9392`; [record](legacy/TASK6E_MASON_UNIFIED_INTERPRETATION_2026-09-16.md); [Actions 35060788601](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35060788601), successful attempt 2** | **Both bridges preserve the additive response unchanged; Mason skill treats lexical/graph as separate lanes, preserves lexical evidence on graph degradation, and uses `kc_get_source` for exact source follow-through. No new graph tool, bridge transport, endpoint, model/runtime or status change.** |
| **KC Task 6F graph readiness status** | **`e34ca35cb1d2a31bdb7ec45d9799dd1f685c66d5`; [record](legacy/TASK6F_GRAPH_READINESS_STATUS_2026-09-16.md); [Actions 35062593583](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35062593583)** | **Additive `kc_status.graph` classification from durable KC projection/validation evidence; distinguishes disabled/no-build/ready/stale/pending/unvalidated/failed/unavailable without provider query, graph sync, model launch, migration, or change to `kc_search`. Does not qualify Task 4 intended-host Graphiti.** |
| **KC Task 6G memory candidate containment** | **`80f3804ce2c1a905c3853f9e7c507066a5ca9431`; [record](legacy/TASK6G_MEMORY_CANDIDATE_BOUNDARY_2026-09-16.md); [Actions 35064560448](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/35064560448)** | **Durable non-canonical candidate proposal/review boundary plus fail-closed exact canonical-store authority. Proposal/review cannot create canonical/retrieval/graph state; canonical store authority binds principal, operation, project, content digest, source ID and source event time. No automatic promotion, bridge integration, model launch or live worker qualification.** |

## Archive and source identity

[legacy/README.md](legacy/README.md) maps historical document paths to preserved evidence and Git blobs. Historical cross-references may retain original paths; resolve them through the archive map or exact Git history.

The retained machine-readable manifests are evidence inputs, not additional current guidance. File moves do not alter canonical records, lifecycle or graph state.

## Checkpoint discipline — EG-001 / EG-002

Reserve enough task capacity to update durable documentation, record validation/unresolved issues, commit intended changes and verify final branch/HEAD/diff before starting another bounded task.

At every material checkpoint update current status/next boundary, update architecture only when its contract changed, and update this evidence index with exact commits/runs and limits. Do not create a competing current-state or pause-handoff document.

A task is not complete while its only state record is a chat. Preserve incomplete work honestly rather than claiming acceptance.
