# Knowledge Core — Current State

**Authoritative KC status and restart point. Updated 2026-09-14.**
Branch: `architecture/knowledge-core`. Reviewed implementation/documentation baseline:
`d9966e2cfc89b62d7597aee9af085e31e8732878`.
This consolidation changes documentation only; it does not rerun qualification or promote a new implementation.

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

## Next bounded work

The next architectural task is to define the smallest governed graph consumer interface, then implement and qualify that boundary before connecting Mason/MindsHub. Preserve Authority-first admission, explicit namespace/scope, validated current-build selection, and exact canonical provenance. Use the existing lexical/segment consumer as the established reference.

This is a direction for subsequent authorized work, not a claim that a public graph endpoint, MindsHub tool, import queue, GPU scheduler, or context assembler already exists. No new implementation or host/model run is authorized by this documentation update.

Do not restart fresh SR-2 implementation, reopen completed G22/host gates solely because an old handoff says they are pending, or continue optimizing accepted Graphiti qualification without a concrete consumer need. The rejected SR-2 prototype `2c48a0e73c560fad62028776f375c94162e138be` remains abandoned and must not be reused for implementation or test design.

## Documentation and graph context

Keep these three documents sufficient to start work without a running graph. Store detailed historical context/evidence under `legacy/` and retrieve it only for the bounded question at hand. Update these documents at every material checkpoint instead of adding another current-state/handoff file.

Moving a file into `legacy/` **does not change KC lifecycle or an existing graph**. A future governed import must explicitly classify historical documents as `superseded`, handle prior document identities/retirements deliberately, and publish the resulting retrieval generation. Neither filenames nor archive prose determine lifecycle. Do not silently edit pinned qualification manifests or relabel historical evidence to make it current.
