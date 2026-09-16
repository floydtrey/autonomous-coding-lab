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
| `kc_store` | `POST /v1/kc/store` | Requires bootstrap admission plus `Idempotency-Key`; canonical evidence settles before derived publication. |
| `kc_search` | `POST /v1/kc/search` | Current live behavior still reuses `kc-lexical-evidence-v2`; Task 6B defines the additive unified response contract, but endpoint wiring is deferred to Task 6D. |
| `kc_get_source` | `POST /v1/kc/get-source` | Accepts an exact current-generation `resource_version_ref`; revalidates eligibility and immutable source size/SHA-256/UTF-8. |
| `kc_status` | `GET /v1/kc/status` | Reports bounded canonical/text readiness. Task 6F may add bounded graph readiness/freshness fields. |

Caller-supplied `X-Knowledge-Caller` does not override the bootstrap principal. The preexisting `/v1/retrieval/search` route remains separate and requires its retrieval Authority evaluator.

Do not use bootstrap admission as justification to expose arbitrary entity/assertion/resource CRUD, unrestricted historical source lookup, raw SQL, database credentials, artifact-store authority, FalkorDB credentials, direct Graphiti mutation or remote access.

## Source-neutral evidence and lexical serving

Tasks 2A–2F establish the accepted source-neutral path from producer-specific proof through canonical ResourceVersion, generic governed observation/decision, complete governed snapshot, SR-2 publication and lexical serving.

Operating rules include:

- repository commit/path/blob/manifest verification remains inside the Git producer;
- direct `user_note` evidence is authenticated local-owner submission plus exact canonical byte custody, not fabricated Git proof;
- source identity, canonical Resource/Version, observation, governance decision, project membership and corpus snapshot remain distinct;
- complete-corpus snapshots feed the one-current-TEXT boundary; producer-local subsets do not replace unrelated current sources;
- publication rechecks predecessor state so stale writers cannot erase newer contributions;
- canonical note evidence settles before derived publication; text failure/pending state does not erase canonical evidence or prior valid serving state;
- current source-neutral SR-2 lexical reads require complete generic lineage and exact canonical artifact/slice verification before serving;
- restriction/erasure eligibility is rechecked at serve time and dominates stale derived rows;
- repository compatibility fields exist only when exact legacy mapping exists; non-Git sources do not receive fabricated repository identity;
- historical RF-2/pre-source-neutral evidence retains its original explicit interpretation.

The public lexical response advertises `evidence_contract_version="kc-lexical-evidence-v2"`; current source-neutral SR-2 segment provenance advertises `governed-source-sr2-v2`.

## Direct-note storage operating rule

`kc_store` currently means explicit trusted canonical storage, not a generic permission for a model to self-author durable memory.

The accepted V1 request accepts `content`, `project`, `source_type="user_note"`, optional stable `source_id` and optional timezone-aware `source_event_time`. Exact retry with the same idempotency identity converges on the same canonical source/Resource/ResourceVersion/observation/decision evidence; reusing the identity with different inputs fails.

Task 6G is reserved for a separate autonomous memory-candidate/admission boundary. Until that work is accepted, do not reinterpret `kc_store` as an autonomous worker-memory proposal mechanism.

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

This pending graph acceptance does not invalidate canonical/text retrieval or Task 5 Mason acceptance.

## Mason / MindsHub operating boundary — Task 5 accepted

Task 5 accepts the project-local Mason -> KC path recorded in [Task 5 qualification](legacy/TASK5_MASON_MINDSHUB_QUALIFICATION_2026-09-15.md).

Accepted path:

```text
MindsHub/Cowork Mason
  -> Anton procedural-memory `knowledge-core` skill
  -> project-local `mason_kc_bridge.py`
  -> loopback KC bootstrap API
  -> canonical / lexical evidence
```

The bridge exposes exactly these literal protocol operations:

```text
kc_status
kc_search
kc_get_source
kc_store
```

Do not shorten/alias the operation identifiers. Unsupported operations fail closed. The bridge does not expose SQL, FalkorDB mutation, Graphiti maintenance, artifact-store access, arbitrary HTTP or arbitrary KC operations.

Qualification proved a fresh Mason session could call the KC skill, perform `kc_search`, follow the ResourceVersion through `kc_get_source`, and return exact canonical content. Task 5 consumes the accepted canonical/lexical path and does not imply Task 4 graph acceptance.

## Unified retrieval operating contract — Task 6B accepted

Task 6B defines `kc-unified-retrieval-evidence-v1` without changing the live endpoint yet.

The unified contract preserves every accepted lexical response field and its `kc-lexical-evidence-v2` meaning. It adds a separately stateful graph lane and bounded degradation warnings.

Public graph states are:

- `disabled`
- `no_build`
- `ready`
- `stale`
- `pending`
- `unvalidated`
- `failed`
- `unavailable`

Only `ready` may contain graph results. A ready lane must identify explicit namespace/scope, one or more validated attempt IDs and the exact same TEXT generation as the lexical snapshot. Every non-ready graph lane returns zero graph results and requires a bounded reason code plus the matching warning.

Do not expose graph authorization denial as a distinct public state. A coordinator may map denied/unreachable graph access to nondisclosing `unavailable`; it may not use that degradation to weaken lexical authorization.

Graph hits carry exact canonical correlation but not duplicated full source text. Consumers use the returned `resource_version_ref` with `kc_get_source` when exact content is required.

Do not create a combined lexical/graph score. Task 6B does not define a graph score or a fusion/reranking policy.

For Task 6C specifically:

- reuse the accepted lexical kernel and existing validated source-neutral graph kernel;
- produce the accepted Task 6B domain contract only; do not wire `/v1/kc/search` yet;
- graph state inspection/search must never launch Graphiti synchronization, a model, or a background job;
- lexical retrieval remains mandatory and independent;
- graph/provider/authority failures are bounded to the graph lane according to the accepted nondisclosing contract;
- do not claim source-neutral Task 4 live acceptance merely because the coordinator can consume a validated build when one exists.

## Task 6 operating sequence

The current phase is Task 6 dogfooding. Follow [CURRENT_STATE.md](CURRENT_STATE.md) for the exact authorized slice.

The intended sequence is:

- 6A reconcile authoritative state — accepted;
- 6B define unified lexical + optional validated-graph retrieval contract — accepted;
- 6C implement the coordinator by reusing existing lexical and graph kernels — current authorized slice;
- 6D place it behind existing `kc_search` without breaking Task 3/5 consumers;
- 6E update Mason interpretation without adding direct graph authority;
- 6F expose bounded graph readiness/freshness state;
- 6G separate autonomous memory proposals from explicit canonical `kc_store`;
- 6H build wrapper-side context compaction/checkpointing;
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

## Archive and source identity

[legacy/README.md](legacy/README.md) maps historical document paths to preserved evidence and Git blobs. Historical cross-references may retain original paths; resolve them through the archive map or exact Git history.

The retained machine-readable manifests are evidence inputs, not additional current guidance. File moves do not alter canonical records, lifecycle or graph state.

## Checkpoint discipline — EG-001 / EG-002

Reserve enough task capacity to update durable documentation, record validation/unresolved issues, commit intended changes and verify final branch/HEAD/diff before starting another bounded task.

At every material checkpoint update current status/next boundary, update architecture only when its contract changed, and update this evidence index with exact commits/runs and limits. Do not create a competing current-state or pause-handoff document.

A task is not complete while its only state record is a chat. Preserve incomplete work honestly rather than claiming acceptance.
