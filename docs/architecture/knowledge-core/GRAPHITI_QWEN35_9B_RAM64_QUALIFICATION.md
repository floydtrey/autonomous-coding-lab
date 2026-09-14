# Graphiti Qwen3.5 9B / 64 GB Host Qualification

## Purpose

Record the clean 64 GB host rerun of the accepted KC -> Graphiti/FalkorDB/Ollama qualification path using `graphiti-qwen35-9b-32k`, and determine whether the earlier Graphiti semantic-integrity failures were primarily caused by host memory pressure.

## Run identity

- Attempt ID: `419a6bb7-2bec-58cc-843b-fbe4292ad82e`
- Model: `graphiti-qwen35-9b-32k`
- Embedder: `nomic-embed-text:latest`
- Source: `docs/architecture/knowledge-core/CURRENT_STATE.md`
- Planned segments: 17
- Physical partition: `kc_695ab895f947f3c46f93d0f497c6`
- Host RAM: 63.717 GiB
- GPU: NVIDIA GeForce RTX 5060 Ti, 16,311 MiB VRAM

All required preflight checks passed: Docker, KC PostgreSQL container and SQL connectivity, FalkorDB container/service/TCP, Ollama API, extraction model, embedding model, Graphiti 0.30.2, and KC artifact root.

## Result

**Qualification result: FAIL for projection semantic integrity.**

The provider completed all 17 source segments and returned all 17 provider bindings, but the projection was settled `incomplete` because Graphiti emitted integrity-relevant semantic warnings. Validation therefore remained `unvalidated`; trusted retrieval was not entered.

Final derived graph counts:

- Episodes: 17
- Entities: 76
- Edges: 190
- KC provider bindings: 17

## Warning analysis

The run emitted 54 Graphiti warnings:

- 44 `valid_at` date parse warnings
- 6 missing source-entity edge warnings
- 1 missing target-entity edge warning
- 2 invalid `duplicate_facts` index warnings
- 1 missing node-resolution warning

The 10 non-date warnings were tied to these canonical segments/stages:

1. Segment 2, lines 20-35, `ExtractedEdges`: missing source entity `IS_ACCEPTED_WITHOUT_REBUILDING`.
2. Segment 2, lines 20-35, `EdgeDuplicate`: invalid duplicate-fact index `[0]` for an existing-facts range of `0--1`.
3. Segment 4, lines 42-54, `NodeResolutions`: missing resolution for ID `[8]`.
4. Segment 5, lines 55-69, `EdgeDuplicate`: invalid duplicate-fact indices `[0..9]` for an existing-facts range of `0--1`.
5. Segment 8, lines 78-83, `ExtractedEdges`: missing source entities `HAS_CHECKPOINT`, `PRESERVES_SOURCE_DEclarations`, `COMPUTES_MONOTONE_EFFECTIVE_LIFECYCLE`, `REJECTS_STANDALONE_ATTEMPTED_CONTROL_ERRORS`, and `BINDS_EXPLICIT_GOVERNED_OBSERVATION_IDENTITY`.
6. Segment 13, lines 126-153, `ExtractedEdges`: missing target entity `IDENTIFIED_BY_AUDIT`.

The missing-endpoint warnings are the same failure class that previously caused the Graphiti projection to be classified incomplete: an edge-generation stage referenced entity identities that were not present in the extracted node set. The duplicate-fact and missing-resolution warnings are additional cross-stage consistency failures.

## Performance / host evidence

- Wall-clock duration: 489.516 s (~8.16 min)
- LLM requests completed: 196
- Failed LLM requests: 0
- Prompt tokens: 266,163
- Completion tokens: 23,686
- Total tokens: 289,849
- Aggregate completion throughput: 17.622 tok/s
- Longest completed LLM request: 87.125 s
- Peak RAM used: 21.75 GiB (34.14%)
- Peak commit used: 32.749 GiB (30.98%)
- Peak VRAM used: 8,706 MiB (53.38%)
- Peak GPU utilization: 100%
- Peak GPU temperature: 74 C
- Peak GPU power: 168.44 W
- Host telemetry sampling errors: none
- Observer event-journal errors: none

The extraction model and embedder were both resident on the GPU at run completion, and the qualification showed ample RAM and VRAM headroom while completing every source segment and every provider binding.

## Conclusion

The 64 GB rerun does **not** support host-memory pressure as the primary explanation for the earlier semantic-integrity failure. The failure reproduced with substantial RAM and VRAM headroom, zero failed LLM requests, and complete 17/17 episode and provider-binding coverage.

The current leading diagnosis is **cross-stage semantic inconsistency in the Qwen3.5 9B / Graphiti extraction path**, particularly entity-set versus edge-endpoint consistency, plus weaker duplicate-resolution consistency.

Do not weaken KC validation to accept this output. KC correctly fenced the derived projection as incomplete.

## Next gate

Run the exact same 17-segment qualification path with Qwen3.8 27B at 32K context, changing only the extraction model identity/configuration required for that model. Preserve the same canonical source, query, namespace, scope, Graphiti version, embedder, structured-output mode, reasoning setting, and KC validation rules. Clear the derived Falkor partition before the new run so the model comparison begins from an empty derived graph while retaining the canonical KC ledger/evidence from this run.

Primary comparison criterion: reduction or elimination of cross-stage semantic-integrity warnings, especially missing edge endpoints, invalid duplicate-fact references, and missing node resolutions.
