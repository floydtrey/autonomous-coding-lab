# Graphiti Qwen3.8 27B Host Qualification

## Purpose

Record the exact 17-segment KC -> Graphiti/FalkorDB/Ollama qualification rerun using `graphiti-qwen38-27b-32k`, and compare it against the completed Qwen3.5 9B / 64 GB baseline.

## Run identity

- Attempt ID: `fc9eaadc-596d-586d-a2ec-e970c34baac9`
- Model: `graphiti-qwen38-27b-32k`
- Embedder: `nomic-embed-text:latest`
- Source: `docs/architecture/knowledge-core/CURRENT_STATE.md`
- Planned segments: 17
- Physical partition: `kc_695ab895f947f3c46f93d0f497c6`
- Host RAM: 63.717 GiB
- GPU: NVIDIA GeForce RTX 5060 Ti, 16,311 MiB VRAM
- Graphiti: 0.30.2

All required preflight checks passed before launch.

## Result

**Qualification result: FAIL for projection semantic integrity.**

The provider completed all 17 source segments and returned all 17 KC provider bindings, but the projection settled `incomplete`. Validation therefore remained `unvalidated`; trusted retrieval was not entered.

Final derived graph counts:

- Episodes: 17
- Entities: 40
- Edges: 102
- KC provider bindings: 17

## Warning analysis

The run emitted exactly 6 Graphiti warnings, all of the same hard semantic-integrity class:

- 6 missing source-entity edge warnings
- 0 missing target-entity edge warnings
- 0 invalid `duplicate_facts` index warnings
- 0 missing node-resolution warnings
- 0 `valid_at` parse warnings

All 6 warnings occurred on the same canonical segment:

- Segment key: `sha256:888f27ecb4abbbff0e0a9740ead036eb69e6cc0ec95ba5f8a45689ee0e146b47`
- Segment ordinal: 11
- Source lines: 102-125
- Body size: 1,774 bytes
- Stage immediately preceding warnings: `ExtractedEdges`

The stage sequence on this segment was:

1. `ExtractedEntities` returned 6 entities.
2. `NodeResolutions` returned 1 resolution.
3. `ExtractedEdges` returned 6 edges.
4. Graphiti rejected all 6 edge outputs because their source entities were not present in the node set.
5. The segment completed with 6 nodes and 0 committed edges.

Rejected edge relations:

- `IMPLEMENTATION_CHECKPOINT`
- `TRANSACTION_SYSTEM`
- `MANAGES_RECEIPTS`
- `COEXISTS_WITH`
- `QUALIFIED_BY`
- `REQUIRES_MIGRATION`

This is the same fundamental cross-stage consistency class that disqualified the 9B run: edge generation referenced entity identities not resolvable against the extracted node set.

## Performance / host evidence

- Wall-clock duration: 982.016 s (~16.37 min)
- LLM requests completed: 80
- Failed LLM requests: 0
- Prompt tokens: 166,731
- Completion tokens: 10,836
- Total tokens: 177,567
- Aggregate completion throughput: 8.953 tok/s
- Longest completed LLM request: 76.641 s
- Peak RAM used: 28.545 GiB (44.8%)
- Peak commit used: 45.844 GiB (43.36%)
- Peak VRAM used: 14,711 MiB (90.19%)
- Peak GPU utilization: 100%
- Peak GPU temperature: 69 C
- Peak GPU power: 126.35 W
- Host telemetry sampling errors: none
- Observer event-journal errors: none

At completion Ollama reported the 27B model split approximately 39% CPU / 61% GPU at 32K context. The embedder remained 100% GPU resident.

## Comparison with Qwen3.5 9B

Qwen3.8 27B improved the failure profile substantially but did **not** clear the KC acceptance gate.

| Metric | Qwen3.5 9B | Qwen3.8 27B |
| --- | ---: | ---: |
| Wall time | 489.516 s | 982.016 s |
| LLM requests | 196 | 80 |
| Total tokens | 289,849 | 177,567 |
| Completion tok/s | 17.622 | 8.953 |
| Peak RAM | 21.75 GiB | 28.545 GiB |
| Peak VRAM | 8,706 MiB | 14,711 MiB |
| Total warnings | 54 | 6 |
| Missing source endpoints | 6 | 6 |
| Missing target endpoints | 1 | 0 |
| Invalid duplicate indices | 2 | 0 |
| Missing node resolutions | 1 | 0 |
| Date parse warnings | 44 | 0 |
| Final disposition | `incomplete` | `incomplete` |

The 27B model eliminated several secondary warning classes and concentrated the remaining failure on one dense canonical segment. However, the primary acceptance criterion was elimination of missing edge endpoints, and that criterion was not met.

The 27B run also took about twice the wall-clock time and roughly half the aggregate completion throughput of the 9B run on this host.

## Conclusion

Qwen3.8 27B is materially more consistent than Qwen3.5 9B under this Graphiti workload, but it still fails the exact semantic-integrity invariant KC requires.

The evidence no longer supports simply escalating model size as the next default action. Both models fail the same core endpoint-resolvability invariant, and the 27B failure is tightly localized to one segment and one Graphiti stage boundary.

KC should continue to classify this projection as incomplete. Do not relax the validator.

## Next gate

Before testing another model, inspect the exact failing segment and Graphiti's structured outputs for the `ExtractedEntities` -> `NodeResolutions` -> `ExtractedEdges` transition. The immediate question is whether the failure is primarily:

1. model cross-stage semantic inconsistency;
2. Graphiti prompt/schema identity conventions that encourage incompatible entity references across stages; or
3. an interaction between the two.

A bounded diagnostic should capture the structured entity and edge outputs for this one segment only, without hidden reasoning, and compare the referenced endpoint identities deterministically before Graphiti attempts to commit the edges.

If the segment-level diagnostic shows the model alone is producing incompatible IDs/names despite a coherent schema, then continue model qualification. If it shows the prompt/schema contract itself is ambiguous or mismatched, fix that contract once rather than repeatedly escalating model size.
