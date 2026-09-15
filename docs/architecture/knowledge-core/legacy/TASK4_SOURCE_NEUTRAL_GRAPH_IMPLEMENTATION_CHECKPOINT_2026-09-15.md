# Task 4 Source-Neutral Graph Synchronization — Implementation Checkpoint

## Status

**IMPLEMENTATION QUALIFIED; LIVE INTENDED-HOST ACCEPTANCE PENDING.**

This record preserves the deterministic implementation checkpoint for KC Usable V1 Task 4. It is evidence, not a competing current-state document. `CURRENT_STATE.md`, `ARCHITECTURE.md`, and `OPERATIONS.md` remain the authoritative current guidance.

Task 4 is **not accepted yet** by this record alone. The remaining acceptance barrier is a bounded real Graphiti/FalkorDB/local-model mixed-source run on the intended host, followed by the existing independent validation and Authority-first trusted retrieval path.

## Baseline and implementation branch

- accepted Task 3 base / Task 4 starting point: `9ee0c0c18391d7b43e1fce0a5da3ba08a7e74e1d`
- implementation branch: `architecture/knowledge-core-task4`
- implementation/tool checkpoint: `09877fa19c46068e517a2dc7485baef268228bcb`
- pull request: #7, `KC Task 4 source-neutral Graphiti synchronization`
- exact-head Knowledge Core workflow: Actions `34942510923`
- workflow result: **success**

The exact-head workflow passed migrations, the fast semantic suite, PostgreSQL qualification, pinned G22, RI-4 restart rehearsal, and SR-2 restart/replay rehearsal.

## Implemented boundary

Task 4 adds a new, explicitly versioned source-neutral graph-planning path without rewriting the historical repository-shaped Graphiti qualification semantics.

The new contract is carried by:

- `knowledge_core/domain/source_neutral_projection.py`
- `knowledge_core/application/source_neutral_graph.py`
- `tools/graphiti_source_neutral_sync.py`
- `tests/test_task4_source_neutral_graph.py`

The historical `projection_orchestration.py`, `graph_retrieval.py`, Graphiti adapter implementation, durable projection-attempt/source-binding/validation ledgers, and accepted historical Graphiti evidence remain unchanged.

## Source-neutral graph plan contract

The new graph plan is `kc-source-neutral-graph-plan-v1`.

`GovernedProjectionSourceSegment` keeps exact canonical segment identity and body while carrying generic KC evidence:

- ResourceVersion and canonical revision;
- exact segment key, coordinates, and source-slice SHA-256;
- generic source identity digest, kind, origin scope, collection, and item identity;
- generic observation ID/digest and producer identity/version;
- governance decision ID/digest, policy, rationale, and decision time;
- governing complete-corpus snapshot digest and governed projection digest;
- project memberships;
- distinct observation/event/revision times;
- optional repository compatibility fields only when an exact legacy mapping exists.

Non-Git sources do not receive fabricated repository, commit, path, document, or manifest identity.

Before graph planning, the new kernel reconstructs and verifies the complete current source-neutral SR-2 lineage against the governing snapshot, `TextGenerationSource` rows, canonical current-generation sources, exact ResourceVersion ownership, governance decisions, and optional repository compatibility mappings. Partial, mixed, or mismatched lineage fails closed.

## Reference-time policy

The new graph reference-time policy is:

`source-event-then-revision-then-observed-v1`

For each generic observation, graph reference time is selected deterministically in this order:

1. source event time, when present;
2. source revision time, when present;
3. KC observation/admission time.

Repository import receipt creation time is **not** treated as a universal event clock in the Task 4 path.

The graph projection profile digest binds the source-neutral graph-plan version, reference-time policy, and current TEXT generation config digest. Therefore a future behavior-changing graph-time policy cannot silently reuse an older validated build as if semantics were unchanged.

## Bounded synchronization

`SourceNeutralGraphProjectionKnowledgeKernel.sync_current_sr2_projection()` is an explicit operator/application boundary. It does not run during `kc_store` and does not create a scheduler or background queue.

- default bound: 100 segments;
- explicit allowed bound: 1–10,000 segments;
- omitted ResourceVersion selection means all current governed SR-2 sources;
- callers may instead select an explicit current ResourceVersion subset;
- an over-bound plan is rejected before opening a projection attempt or invoking the external provider;
- canonical/text state remains independent of graph success.

The operator entrypoint `tools/graphiti_source_neutral_sync.py` uses the existing `GraphitiProjectionAdapter`, Graphiti 0.30.2 contract, durable attempt/source bindings, `GraphitiProjectionValidator`, and Authority-first trusted search. It supports source listing, explicit or complete-current ResourceVersion selection, a segment cap, stable attempt salt, explicit namespace/scope, local Graphiti model/embedder configuration, validation, and trusted-result output with generic KC correlation.

## Deterministic mixed-source qualification

The PostgreSQL Task 4 qualification constructs one current SR-2 generation containing:

- a verified repository document; and
- an authenticated direct `user_note` stating that Mason is the local MindsHub worker model.

The test proves:

- both producer types enter one source-neutral graph plan;
- repository compatibility remains exact for the Git source;
- the direct note has null repository compatibility rather than fabricated Git identity;
- direct-note graph reference time uses its explicit source event time;
- both sources retain the same governing complete-corpus snapshot identity;
- a one-segment cap rejects the mixed plan before any provider call and before a projection-attempt row is opened;
- a successful bounded projection stores exact provider-source bindings;
- successful projection alone is not trusted: graph search does not call the provider before independent validation;
- after independent validation, Authority-first trusted graph retrieval returns a Mason fact correlated to the exact direct-note ResourceVersion and generic governed observation/decision/snapshot/projection evidence;
- an external projection failure is quarantined as durable attempt evidence;
- that graph failure does not change the current SR-2 generation and does not break lexical retrieval of the stored note.

## What this checkpoint does not prove

This checkpoint does **not** claim:

- a real mixed-source Graphiti/FalkorDB build has completed on the intended Windows host;
- Qwen/LLM extraction quality for the mixed-source corpus;
- FalkorDB availability, local model availability, or resource behavior on the current workstation;
- production deployment;
- continuous synchronization;
- a scheduler, workflow engine, generic queue, or GPU/model orchestrator;
- cross-generation graph reuse;
- Mason/MindsHub integration;
- Task 5 acceptance.

Historical accepted Graphiti qualification at `6376419e369ea9ecfe58a19fa233bbfca90ad703` remains valid evidence for its exact repository-shaped build. It is not retroactively relabeled as mixed-source Task 4 acceptance.

## Remaining Task 4 acceptance barrier

Run the new bounded source-neutral tool on the intended host with a current mixed-source SR-2 corpus and the actual Graphiti/FalkorDB/local-model stack. Acceptance requires:

1. successful bounded projection;
2. complete independent validation under the existing provider validation requirement;
3. Authority-first trusted retrieval;
4. at least one trusted graph result;
5. exact correlation of that result to generic KC governed evidence;
6. canonical/text retrieval remaining usable if a separate failed/interrupted graph attempt is exercised or already evidenced by deterministic qualification.

Until that live barrier is closed, **Task 4 remains the current authorized slice and Task 5 is not authorized.**
