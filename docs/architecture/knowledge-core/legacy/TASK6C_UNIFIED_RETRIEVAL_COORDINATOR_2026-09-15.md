# Task 6C Unified Retrieval Coordinator — 2026-09-15

## Status

**ACCEPTED IMPLEMENTATION CHECKPOINT.**

This record preserves the Task 6C application-coordinator qualification. It does not wire the coordinator into the live `/v1/kc/search` route and does not run or qualify a live Graphiti/FalkorDB/local-model build.

## Baseline and checkpoint

- accepted Task 6B merge baseline: `22f75e1139d5ac6ed14ae092fb8f6fa31af3613c`
- Task 6C implementation/test checkpoint: `5a8fac1d3a2b8caa3798a63f5df75f2a104705d0`
- pull request: #12, `KC Task 6C: unified retrieval coordinator`
- exact-head Knowledge Core workflow: Actions `35041876808`
- workflow result: **success**

The exact-head workflow passed migrations, the fast semantic suite, PostgreSQL G1–G21 qualification, pinned G22, RI-4 restart rehearsal, and SR-2 restart/replay rehearsal.

An earlier exact-head run, Actions `35041771603`, stopped in the fast suite with 169 passed / 1 failed because one focused test expected the raw caller query even though its fake lexical snapshot intentionally contained a different normalized query. The coordinator behavior did not change in response; only the incorrect assertion was corrected so the test now verifies that the graph lane receives the lexical snapshot query.

## Accepted coordinator boundary

`UnifiedRetrievalCoordinator` is lexical-first and produces the accepted `kc-unified-retrieval-evidence-v1` domain contract.

It reuses:

- `ConsumerReadKnowledgeKernel.search_text()` for the mandatory lexical lane; and
- `SourceNeutralGraphProjectionKnowledgeKernel.search_validated_projection()` for optional trusted graph augmentation.

The coordinator does not duplicate the existing graph validation/canonical-correlation logic.

### Lexical behavior

Lexical retrieval executes first and outside all graph-degradation handling. If canonical/text trust or lexical serving fails, unified retrieval fails with the existing lexical failure rather than masking that failure with graph state.

If valid lexical evidence exists, graph-side absence or failure cannot invalidate it.

### Explicit graph binding

Graph augmentation requires an explicitly injected `UnifiedGraphSearchBinding` containing:

- projection adapter;
- retrieval Authority evaluator seam;
- caller principal;
- namespace; and
- scope.

The coordinator does not discover providers, open Graphiti/FalkorDB, synchronize a graph, start a model, or create background work.

With no graph binding, the result is lexical evidence plus public graph state `disabled`.

### Current-only graph augmentation

The accepted trusted graph path is current-only. Requests with `include_superseded=True` remain lexical-only and return graph state `disabled` rather than mixing current graph evidence into a historical lexical request.

If no current TEXT generation exists, graph state is `no_build` without a graph-provider call.

### Validated-build handling

The coordinator calls only the existing trusted graph-search kernel. A returned graph snapshot must match the exact lexical TEXT generation.

- generation mismatch -> `stale`, zero graph results;
- compatible trusted snapshot with validated attempt IDs -> `ready`;
- no compatible validated attempt IDs -> `unavailable`, reason `no-compatible-validated-graph-build`.

The no-attempt case is deliberately **not** labeled `no_build`: trusted search proves only that no compatible validated build is available. It cannot distinguish an actually absent build from stale, pending, failed, or unvalidated durable attempts. Task 6F is reserved for that evidence-based state classification.

### Failure containment and nondisclosure

Provider, graph-Authority, graph-integrity, or mapping exceptions after successful lexical retrieval collapse to public graph state `unavailable`, reason `graph-evidence-unavailable`, with no raw exception text exposed.

Graph failures therefore remain bounded to the optional lane. Python system/cancellation exceptions outside ordinary `Exception` are not intentionally swallowed.

### Graph result mapping

Ready trusted hits must carry `GovernedProjectionSourceSegment` source-neutral KC evidence. The coordinator maps exact ResourceVersion/segment/source-identity/observation/decision/snapshot/projection/reference-time correlation into the Task 6B graph contract.

Provider source body/full canonical content is not copied into the graph response. Exact content continues through `kc_get_source`.

The coordinator uses the normalized lexical snapshot query for the graph lane, keeping both evidence lanes bound to the same interpreted request string.

## Focused qualification

`tests/test_task6c_unified_retrieval_coordinator.py` uses fake provider-neutral lexical/graph seams only. It proves:

- graph not configured -> lexical + disabled state and no graph call;
- lexical failure is not masked;
- no TEXT generation avoids graph access;
- historical lexical request does not mix current graph evidence;
- no compatible validated build degrades nondisclosingly;
- generation mismatch drops graph results as stale;
- graph exception does not expose provider details or break lexical evidence;
- ready graph hits map exact source-neutral KC correlation without body/content;
- malformed/non-source-neutral trusted-hit correlation is quarantined to the graph lane.

No Graphiti package, FalkorDB instance, or local model is needed by the focused coordinator tests.

## Explicit non-scope

Task 6C does **not**:

- change `/v1/kc/search` behavior or response model;
- alter `kc_status`;
- alter the Mason bridge or skill;
- synchronize Graphiti;
- start a model/provider;
- create a scheduler/background queue;
- add a migration;
- distinguish durable graph readiness states beyond what trusted search can prove;
- accept the pending Task 4 intended-host source-neutral Graphiti barrier.

The next bounded slice is Task 6D: wire the accepted coordinator/response contract behind the existing bootstrap `/v1/kc/search` route while preserving existing Task 3/5 lexical consumers and keeping graph augmentation optional.
