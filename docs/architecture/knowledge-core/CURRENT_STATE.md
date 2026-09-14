# Knowledge Core — Current State

**Authoritative KC status and restart point. Updated 2026-09-14.**
Branch: `architecture/knowledge-core`. Documentation consolidation baseline:
`2678e7666fbcba50b64d8839ea0592a8d992e916`.
Latest accepted KC Usable V1 checkpoint: `b9e708f2892f3a7303fa50ccadc64c26f5b9bf46`.

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
| SR-2 segmentation and retrieval | Accepted audit-amended KC-D025/SR-1 implementation; G1–G22 independently green. |
| SR-2 intended host | Accepted Windows/PostgreSQL restart/recovery, exact structural reconstruction, provenance, segment serving and replay. |
| KC Consumer V1 / lexical API | Implemented exact segment-content serving with provenance. `POST /v1/retrieval/search` evaluates injected Authority before protected search. |
| KC Usable V1 bootstrap access | **Task 1 accepted.** Configurable bind host defaults to `127.0.0.1`; shared API-key admission maps accepted front-door calls to fixed principal `local_owner`; only store/search/get-source/status operation classes are admitted. This facility is not yet attached to a public Usable V1 front-door route. |
| Projection attempt and validation ledgers | Implemented durable, separate provider-attempt and independent validation evidence. Provider success alone is insufficient. |
| Governed Graphiti backend | Accepted real-host governed-document projection, immutable build isolation, lifecycle validation and trusted canonical result correlation. |
| Public graph consumer API | **Not exposed/promoted.** Trusted graph retrieval exists in the application kernel; the public retrieval route still performs lexical search. |
| ACL consumer boundary | Governed segment evidence can enter Controller Task Packet V1 as informational context; execution remains disabled. |
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

### Task 2 — `kc_store` front door — NEXT AUTHORIZED TASK

Expose one simple store operation that accepts content plus minimal source/project metadata and translates it into the accepted Resource/ResourceVersion machinery. Consumers must not need internal revision IDs, hashes, generation IDs, or storage locations.

**Accept when:** one plain-text request creates durable exact evidence; restart preserves it; replay remains consistent with KC identity/idempotency rules; content becomes available to accepted text retrieval; the response reports understandable canonical/text/graph state.

**Stop:** storage must not require synchronous Graphiti/model execution.

**Current authorization:** Task 2 only. Checkpoint it before Task 3.

### Task 3 — simple read surface

Expose `kc_search`, `kc_get_source`, and `kc_status`, initially using the accepted lexical/SR-2 path where appropriate.

**Accept when:** a fresh client retrieves newly stored information and follows the result to exact canonical evidence without knowing KC database/storage internals.

**Usability milestone:** store `Mason is my local MindsHub worker model`, start a fresh session, ask `What is Mason?`, and receive the fact plus exact KC provenance.

### Task 4 — separate Graphiti synchronization

Add an explicit bounded sync for eligible canonical/text material. New knowledge may remain graph-pending without blocking storage.

**Accept when:** a bounded batch projects successfully through existing immutable-build isolation and independent validation; failed/interrupted graph work leaves canonical/text retrieval usable; only validated builds enter trusted graph retrieval; at least one graph result resolves to exact KC evidence.

**Stop:** no permanent scheduler, generalized queue/workflow platform, or GPU/model orchestrator unless explicit batching proves insufficient.

### Task 5 — Mason / MindsHub tools

Expose only `kc_store`, `kc_search`, `kc_get_source`, and `kc_status` to Mason through the governed front door. Keep Graphiti synchronization operator-controlled initially.

**Accept when:** a fresh Mason session can store/retrieve KC context and answer a stored project question without direct database, artifact-store, FalkorDB, or Graphiti mutation access.

### Task 6 — dogfood KC on KC

Ingest the authoritative KC context and selected active project knowledge and use normal retrieval during project work.

**Accept when:** KC provides enough context to resume bounded work without loading large historical handoffs. If actual use exposes retrieval weakness, improve that demonstrated weakness. If access control proves inadequate, separate Authority. Do not pre-build either problem.

## Explicitly deferred from Usable V1

Do not expand this phase into generalized Authority, multiple roles, direct remote KC exposure, Vera/ACL permission systems, continuous Graphiti processing, model/GPU scheduling infrastructure, broad automatic account/web ingestion, complex UI/workflow infrastructure, destructive autonomous maintenance, or arbitrary provider/database access.

The goal is the smallest safe path from infrastructure project to useful knowledge tool. KC should then help preserve the context needed to finish KC, ACL, Vera, and related projects.

## Documentation and graph context

Keep these three documents sufficient to start work without a running graph. Store detailed historical context/evidence under `legacy/` and retrieve it only for the bounded question at hand. Update these documents at every material checkpoint instead of adding another current-state/handoff file.

Moving a file into `legacy/` **does not change KC lifecycle or an existing graph**. A future governed import must explicitly classify historical documents as `superseded`, handle prior document identities/retirements deliberately, and publish the resulting retrieval generation. Neither filenames nor archive prose determine lifecycle. Do not silently edit pinned qualification manifests or relabel historical evidence to make it current.
