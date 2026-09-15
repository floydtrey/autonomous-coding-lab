# Knowledge Core — Current State

**Authoritative KC status and restart point. Updated 2026-09-14.**
Branch: `architecture/knowledge-core`. Documentation consolidation baseline:
`2678e7666fbcba50b64d8839ea0592a8d992e916`.
Latest accepted KC Usable V1 checkpoint: `cbfecbfada73e1210ceae0185a31664bf073a479`.

## Read order and authority

After the repository [agent rules](../../../AGENTS.md), read these three current KC documents:

1. **This document** — accepted status, remaining work, and restart boundary.
2. [ARCHITECTURE.md](ARCHITECTURE.md) — current invariants and service/consumer contracts.
3. [OPERATIONS.md](OPERATIONS.md) — development, qualification, evidence index, and checkpoint rules.

These are the only authoritative current KC documents. The component README and repository entry points route here; they do not maintain separate KC status.
[legacy/](legacy/README.md) holds frozen historical documents and accepted evidence, outside the default read order. Its old status, stop gates, and next-task prose describe earlier checkpoints and must not be resumed as current instructions. Archiving a decision or qualification record does not revoke its accepted invariants or evidence.

[Root current state](../../CURRENT_STATE.md) governs ACL runtime and execution authority. KC provides informational evidence; it does not authorize execution. ACL remains **DISABLED**. KC qualification does not activate ACL.

## What is accepted and usable

| Area | Current boundary |
|---|---|
| Kernel V1 and PostgreSQL | Accepted canonical history, identities, exact source provenance, idempotency, concurrency and serving fences. |
| Governed repository import | Accepted bounded exact-object import, stable document identity, governed observations and persistence/recovery. |
| RF-2 lexical retrieval | Accepted whole-document PostgreSQL baseline retained beneath the segment transition. |
| SR-2 segmentation and retrieval | Accepted audit-amended KC-D025/SR-1 implementation; G1–G22 independently green. Current implementation remains repository-coupled in its governed-source lineage and publication path; Task 2 corrects that without invalidating historical acceptance evidence. |
| SR-2 intended host | Accepted Windows/PostgreSQL restart/recovery, exact structural reconstruction, provenance, segment serving and replay. |
| KC Consumer V1 / lexical API | Implemented exact segment-content serving with provenance. `POST /v1/retrieval/search` evaluates injected Authority before protected search. Current response provenance is repository-shaped and will receive a source-neutral version/compatibility boundary during Task 2. |
| KC Usable V1 bootstrap access | **Task 1 accepted.** Configurable bind host defaults to `127.0.0.1`; shared API-key admission maps accepted front-door calls to fixed principal `local_owner`; only store/search/get-source/status operation classes are admitted. This facility is not yet attached to a public Usable V1 front-door route. |
| Source-neutral governed-source contract | **Task 2A accepted.** Typed/versioned pure-domain contract separates logical source identity, canonical Resource/ResourceVersion identity, immutable observations, governance decisions, project membership and complete retrieval snapshots without changing storage or serving. |
| Projection attempt and validation ledgers | Implemented durable, separate provider-attempt and independent validation evidence. Provider success alone is insufficient. |
| Governed Graphiti backend | Accepted real-host governed-document projection, immutable build isolation, lifecycle validation and trusted canonical result correlation. Its current plan input is still repository-shaped; generic mixed-source graph input is deferred until after source-neutral text ingestion works. |
| Public graph consumer API | **Not exposed/promoted.** Trusted graph retrieval exists in the application kernel; the public retrieval route still performs lexical search. |
| ACL consumer boundary | Governed segment evidence can enter Controller Task Packet V1 as informational context; execution remains disabled. Current ACL evidence schema is repository-shaped and is not being generalized in Task 2 unless required for compatibility. |
| Mason / MindsHub | Integration not implemented in this checkout. |
| Vera | Future consumer work. |

Acceptance applies to recorded checkpoints and bounded scenarios. It is not a claim of production deployment, comprehensive answer quality, or fresh qualification of every file added afterward. Exact records are indexed in [OPERATIONS.md](OPERATIONS.md#accepted-evidence).

## Latest accepted Graphiti result

The [2026-09-14 acceptance record](legacy/GRAPHITI_GOVERNED_QUALIFICATION_2026-09-14.md) seals implementation checkpoint `6376419e369ea9ecfe58a19fa233bbfca90ad703`:

- Graphiti `0.30.2`, LLM alias `graphiti-qwen38-27b-32k`, embedder `nomic-embed-text:latest`.
- Ruleset `kc-graphiti-governed-document-v3`; validator `kc-graphiti-live-validator`, version `3`.
- Attempt `ea7eba74-912f-5e88-9271-f59670066d88`; validation `df9eabde-5a63-5f70-9478-27b74bd07684`.
- Projection `succeeded`, validation `validated`, 17/17 source bindings, 7/7 checks passed, zero integrity warnings.
- 10/10 returned search results had canonical attribution.
- Complete inventory of 48 edges / 48 source contributions; zero retired, missing-attribution, unknown-source, wrong-partition or multi-source anomalies.

This closes the governed-document semantic invalidation/provider-controlled retirement defect. Retrieval ranking and answer quality remain separate concerns. The tool defaults still name the earlier 9B alias; the accepted 27B run must not be confused with those defaults.

The accepted fixture was an already-governed canonical version of `docs/architecture/knowledge-core/CURRENT_STATE.md`. The replacement page you are reading is new documentation, not those 17 segments. The pre-consolidation page is preserved [in the archive](legacy/CURRENT_STATE.md), and earlier versions remain in Git; exact replay must use the existing canonical artifacts/generation and recorded source identities.

## KC Usable V1 — current objective

The next phase is to make KC useful enough to preserve and retrieve project context before expanding its infrastructure further.

**Usable V1 goal:** a local consumer can store governed information, retrieve it in a fresh session, inspect exact canonical source evidence, and later use validated Graphiti retrieval without direct access to PostgreSQL, the artifact store, or FalkorDB.

Bootstrap choices are intentionally replaceable. The initial service address is configurable and starts at `127.0.0.1`; localhost is a deployment choice, not a permanent architecture rule. Initial access uses shared-key authentication and the bootstrap principal `local_owner`. The existing Authority seam remains intact, but a generalized Authority service is deferred until broader consumers, permissions, remote access, or an observed policy problem justifies it. If the bootstrap authority becomes insufficient, stop and separate Authority rather than extending ad-hoc permissions.

Initial consumer operations are limited to:

```text
kc_store
kc_search
kc_get_source
kc_status
```

Graph maintenance is separate. Normal storage must not require a large model or immediate Graphiti projection:

```text
store -> canonical Resource/ResourceVersion -> governed text retrieval
      -> graph pending -> explicit Graphiti sync -> validation -> trusted graph
```

Graph failure or delay must not invalidate successfully stored canonical evidence or otherwise valid text retrieval.

## Task 2 source-model audit checkpoint — 2026-09-14

A read-only independent audit at checkpoint `f6f049f54789381ffa581ca9b28930a4d98ee450` confirmed that canonical Resource/ResourceVersion/artifact storage is already largely source-neutral, while the governed SR-2 retrieval path is not. Repository/Git assumptions currently leak into governed source selection, durable foreign keys, generation construction/publication, lexical serving/public schemas, Graphiti plan reconstruction/reference time, and downstream ACL evidence schemas.

The correction is **not** to weaken repository verification or replace canonical identity. Repository import remains a strongly verified Git-specific producer. The missing boundary is a source-neutral governed-source model between canonical ResourceVersion evidence and derived retrieval.

The corrected model must keep these meanings distinct:

1. **Resource** — KC logical canonical object.
2. **ResourceVersion** — exact canonical bytes/content identity.
3. **Governed source identity** — logical origin item with typed producer/origin/container/item identity; project is not source identity.
4. **Observation/admission evidence** — a specific capture/submission of an exact ResourceVersion with producer proof and relevant times.
5. **Governance decision/state** — lifecycle/classification/rank inputs admitted by KC; source claims are evidence, not authority by themselves.
6. **Governed retrieval snapshot** — immutable complete selected corpus and policy inputs used to build one serving generation.
7. **Project/context membership** — separate from origin identity and permitted to associate one source with multiple projects.

Time semantics must also remain distinct where available: source event time, source revision time, KC observation/admission time, and any derived-provider reference-time policy. Import/publication time must not silently become universal event time.

SR-2 retains one-current-generation fencing. Therefore independent producers must not publish partial source subsets that displace other current knowledge. Task 2 must assemble and atomically publish a **complete governed corpus snapshot**, with predecessor/snapshot checking so concurrent or sequential producers cannot erase each other's contributions or resurrect excluded sources.

Historical repository manifests, observations, digests, accepted generations, migrations, and qualification records retain their original meaning. New generic semantics require versioned new evidence/contracts; do not relabel historical evidence as if it qualified the source-neutral model.

The old public RF-2 repository-import publication path shares the same global TEXT generation slot and must be deliberately constrained or migrated during Task 2 so it cannot later replace an accepted SR-2 current generation unexpectedly.

## Bounded task sequence

Work sequentially. Do not silently absorb later tasks into an earlier task.

### Task 1 — bootstrap access contract — ACCEPTED

Accepted at implementation checkpoint `b9e708f2892f3a7303fa50ccadc64c26f5b9bf46`, with full Knowledge Core workflow [Actions 34877670577](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34877670577) green.

Implemented scope:

- configurable `KNOWLEDGE_CORE_BIND_HOST`, defaulting to `127.0.0.1`;
- bootstrap API key supplied through `X-Knowledge-Key`, with configuration sourced from `KNOWLEDGE_CORE_BOOTSTRAP_KEY`;
- accepted bootstrap requests map to the fixed principal `local_owner`;
- client-supplied `X-Knowledge-Caller` cannot replace/spoof the bootstrap principal;
- the admitted operation set is limited to `kc.store`, `kc.search`, `kc.get_source`, and `kc.status`;
- missing/invalid key is rejected before a semantic handler executes; authenticated but unadmitted operations are also rejected before execution;
- no KC domain/storage code, migrations, manifests, Graphiti behavior, or existing retrieval Authority seam changed.

The bootstrap facility is deliberately not attached to every existing low-level KC API route. Task 2 will attach it to the new bounded front door. This checkpoint is not a generalized Authority service or remote-exposure qualification.

The full existing workflow passed: fast semantic suite, PostgreSQL G1–G21, G22, RI-4 restart rehearsal, and SR-2 restart rehearsal.

### Task 2 — source-neutral governed ingestion + `kc_store` — NEXT AUTHORIZED TASK

Task 2 is no longer treated as a single endpoint change. The audit showed that a correct direct-note front door first requires removal of repository-specific assumptions from the generic governed retrieval path. Execute only the bounded slice explicitly authorized below.

#### Task 2A — freeze the generic governed-source contract — ACCEPTED

Accepted at implementation checkpoint `cbfecbfada73e1210ceae0185a31664bf073a479`, with full Knowledge Core workflow [Actions 34923452994](https://github.com/floydtrey/autonomous-coding-lab/actions/runs/34923452994) green.

The accepted pure-domain contract defines:

- `GovernedSourceIdentity` for stable source/origin identity, independent of content and project membership;
- `GovernedSourceBinding` for explicit source-identity → canonical Resource mapping;
- `SourceEvidenceRef` for typed SHA-256-bound producer-specific proof references;
- `GovernedSourceObservation` for immutable capture/admission of one exact ResourceVersion, with source event/revision times distinct from KC observation time;
- `GovernedSourceDecision` for immutable KC classification/lifecycle/rank decisions separate from capture evidence;
- `GovernedSnapshotMember` / `GovernedSnapshotExclusion` for exact selected and excluded evidence;
- `GovernedRetrievalSnapshot` for complete, predecessor-bound, versioned corpus selection.

The contract is challenged with Git repository, local-note, chat-message, email-message and benchmark-run-shaped fixtures. Those fixtures establish shape compatibility only; they do not implement the future connectors.

Snapshot membership is order-independent for digest identity, project membership is separate from source identity, one observation cannot be selected twice under competing governance decisions, and a decision must bind the selected observation. Snapshot record creation time is retained as evidence but excluded from the semantic snapshot digest so exact reconstruction/replay of the same predecessor/policy/membership remains stable.

No database model, migration, existing SR-2 serving/publication behavior, Graphiti contract, public route, repository manifest or historical evidence changed in 2A.

#### Task 2B — generic durable evidence + legacy mapping — NEXT AUTHORIZED SLICE

Add the source-neutral durable evidence/snapshot layer and new versioned digests. Preserve all existing repository evidence. Deterministically map eligible Git evidence into the generic layer with explicit legacy references; serving remains unchanged.

**Accept when:** reconstruction/replay of mapped repository evidence is deterministic, historical records are untouched, failed/pending/quarantined evidence does not become serving-eligible, and direct-note-shaped evidence can exist without fake repository fields.

**Stop:** do not change SR-2 serving/publication, make repository import consume the new layer, expose `kc_store`, or generalize Graphiti in 2B.

#### Task 2C — repository import becomes a verified producer

Keep exact commit/path/blob verification, configured readers, manifests, continuity/retirement policy and receipt semantics inside the repository adapter. Translate accepted repository evidence into the generic governed-source layer.

**Accept when:** existing repository guarantees remain intact and repository-specific proof no longer defines the downstream generic contract. Reconcile both legacy RF-2 and SR-2 publication writers so neither can silently replace the intended current TEXT mode.

#### Task 2D — source-neutral SR-2 selection, lineage and publication

Make SR-2 consume generic governed observations/snapshots instead of repository foreign keys/manifests. Preserve canonical artifact verification, deterministic segmentation, lifecycle monotonicity, exact lineage and one-current-generation fencing.

Publish complete mixed-source corpus snapshots atomically with expected-predecessor checks.

**Accept when:** repository-only behavior remains equivalent, mixed-source candidate construction is deterministic, no producer can accidentally drop another producer's current contribution, failed publication leaves the previous current generation serving, and no fake Git proof is required for non-Git sources.

#### Task 2E — direct-note producer + `kc_store`

Build the first non-Git producer using authenticated local submission. Reuse canonical Resource/ResourceVersion storage and the generic governed-source layer. Attach the Task 1 bootstrap admission to the bounded `kc_store` front door.

Consumers provide useful content/source/project metadata and idempotency context, not internal revisions, generation IDs, hashes, artifact locations, or repository-shaped fields.

**Accept when:** a plain-text note creates exact durable canonical evidence, retry/idempotency is correct, restart preserves it, repository knowledge and the note are both present in the complete SR-2 corpus, and the response reports understandable canonical/text/graph state. If derived publication fails after canonical storage, keep the canonical note and previous valid text generation; report text pending/failed rather than destroying evidence.

**Stop:** no synchronous Graphiti/model execution.

#### Task 2F — source-neutral lexical evidence contract and Task 2 qualification

Version or otherwise explicitly bound the lexical response/evidence contract so non-Git provenance is represented honestly. Preserve a deliberate compatibility path for repository-only consumers; never fabricate repository fields for notes.

Run deterministic/restart/mixed-corpus/idempotency/privacy/publication-failure qualification appropriate to the changed boundary and update the authoritative checkpoint docs.

**Accept when:** direct-note and repository evidence are jointly searchable through the accepted text generation after restart/replay, exact canonical provenance is available, restrictions remain dominant, old accepted historical evidence retains its original interpretation, and the full required KC workflow is green.

**Current authorization:** Task 2B only. Checkpoint it before 2C.

### Task 3 — simple read surface

Expose the Usable V1 `kc_search`, `kc_get_source`, and `kc_status` front-door operations using the source-neutral lexical evidence contract produced by Task 2.

**Accept when:** a fresh client retrieves newly stored information and follows the result to exact canonical evidence without knowing KC database/storage internals.

**Usability milestone:** store `Mason is my local MindsHub worker model`, start a fresh session, ask `What is Mason?`, and receive the fact plus exact KC provenance.

### Task 4 — separate Graphiti synchronization

Generalize graph plan input/reference-time semantics only as required for generic governed SR-2 sources, then add an explicit bounded sync for eligible canonical/text material. Preserve the accepted projection ledger, immutable-build isolation, required validation checks, Authority-first trusted retrieval and exact canonical correlations. New knowledge may remain graph-pending without blocking storage.

**Accept when:** a bounded mixed-source batch projects successfully through independent validation; failed/interrupted graph work leaves canonical/text retrieval usable; only validated builds enter trusted graph retrieval; at least one graph result resolves to exact generic KC evidence.

**Stop:** no permanent scheduler, generalized queue/workflow platform, cross-generation graph reuse, or GPU/model orchestrator unless separately justified and qualified.

### Task 5 — Mason / MindsHub tools

Expose only `kc_store`, `kc_search`, `kc_get_source`, and `kc_status` to Mason through the governed front door. Keep Graphiti synchronization operator-controlled initially.

**Accept when:** a fresh Mason session can store/retrieve KC context and answer a stored project question without direct database, artifact-store, FalkorDB, or Graphiti mutation access.

### Task 6 — dogfood KC on KC

Ingest the authoritative KC context and selected active project knowledge and use normal retrieval during project work.

**Accept when:** KC provides enough context to resume bounded work without loading large historical handoffs. If actual use exposes retrieval weakness, improve that demonstrated weakness. If access control proves inadequate, separate Authority. Do not pre-build either problem.

## Explicitly deferred from Usable V1

Do not expand this phase into generalized Authority, multiple roles, direct remote KC exposure, Vera/ACL permission systems, continuous Graphiti processing, model/GPU scheduling infrastructure, broad automatic account/web ingestion, complex UI/workflow infrastructure, destructive autonomous maintenance, or arbitrary provider/database access.

The source-neutral contract may use small chat/email/file/benchmark-shaped fixtures to prevent obvious source-model mistakes, but Task 2 does **not** implement those connectors. Binary/PDF/MIME extraction, assistant-summary derivation, broad multi-project policy, and cross-generation graph reuse remain future bounded work unless a concrete Task 2 acceptance dependency requires them.

The goal is the smallest safe path from infrastructure project to useful knowledge tool. KC should then help preserve the context needed to finish KC, ACL, Vera, and related projects.

## Documentation and graph context

Keep these three documents sufficient to start work without a running graph. Store detailed historical context/evidence under `legacy/` and retrieve it only for the bounded question at hand. Update these documents at every material checkpoint instead of adding another current-state/handoff file.

Moving a file into `legacy/` **does not change KC lifecycle or an existing graph**. A future governed import must explicitly classify historical documents as `superseded`, handle prior document identities/retirements deliberately, and publish the resulting retrieval generation. Neither filenames nor archive prose determine lifecycle. Do not silently edit pinned qualification manifests or relabel historical evidence to make it current.