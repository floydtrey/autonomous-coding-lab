# Task 6B Unified Retrieval Contract — 2026-09-15

## Status

**ACCEPTED CONTRACT CHECKPOINT.**

This record preserves the Task 6B contract qualification for the future unified `kc_search` response. It does not wire graph retrieval into the live endpoint and does not qualify a live source-neutral Graphiti build.

## Baseline and checkpoint

- accepted Task 6A merge baseline: `7cb06d2e6e52e9000cdb96d26413f8f82a685982`
- Task 6B implementation/test checkpoint: `e45822d116eeb087978eb62dee7770638b6393d7`
- pull request: #11, `KC Task 6B: unified retrieval contract`
- exact implementation-head Knowledge Core workflow: Actions `35041019731`
- workflow result: **success**

The workflow passed migrations, the fast semantic suite, PostgreSQL G1–G21 qualification, pinned G22, RI-4 restart rehearsal, and SR-2 restart/replay rehearsal.

## Accepted contract

Task 6B introduces `kc-unified-retrieval-evidence-v1` as an additive response contract for the existing future `kc_search` surface.

The accepted design keeps the Task 3/5 lexical response fields unchanged and adds two top-level fields:

- `graph` — a separately stateful graph-evidence lane;
- `warnings` — bounded degradation warnings for non-ready graph state.

`unified_evidence_contract_version` identifies the new additive contract while the inherited lexical `evidence_contract_version` remains `kc-lexical-evidence-v2`.

## Mandatory lexical lane

Lexical retrieval remains the required baseline. Task 6B does not create a second text index, alter lexical ranking, change source eligibility, or make lexical success depend on Graphiti/FalkorDB.

A future coordinator must not convert a lexical trust/serving failure into a nominal unified success merely because graph data exists. Graph degradation is fail-open only to independently valid lexical evidence.

## Optional graph lane

Public graph states are:

- `disabled`
- `no_build`
- `ready`
- `stale`
- `pending`
- `unvalidated`
- `failed`
- `unavailable`

Only `ready` may expose graph results. A ready graph lane requires explicit namespace/scope, a graph generation ID, one or more validated attempt IDs, and the graph generation must exactly match the lexical TEXT generation returned in the same unified snapshot.

Every non-ready graph state must:

- expose zero graph results;
- carry a bounded non-blank `reason_code`;
- have the corresponding bounded warning code.

Authorization denial is deliberately not exposed as a distinct public graph state. A future coordinator may collapse graph authorization/unavailability into the nondisclosing public `unavailable` lane while preserving independent lexical authorization.

## Graph result evidence

A graph hit carries the provider hit ID, fact, validity times and at least one exact KC source correlation.

Each source correlation carries:

- ResourceVersion and source revision;
- segment key/ordinal, line range and exact source-slice SHA-256;
- generic source identity fields and project memberships;
- governed observation/decision IDs and digests;
- governing snapshot and projection digests;
- graph reference time/policy;
- repository compatibility only when exact legacy mapping exists.

Full canonical source text is deliberately not duplicated into graph correlation output. Consumers continue to follow `resource_version_ref` through the accepted `kc_get_source` operation when exact canonical content is needed.

## Ranking and score semantics

Task 6B does not define a combined lexical/graph score and does not place a synthetic score on graph facts. Lexical ranking and graph retrieval semantics remain distinct evidence lanes.

Any future ranking/fusion policy would require a separate explicit contract and qualification.

## Files

Contract implementation:

- `knowledge_core/domain/unified_retrieval.py`
- `knowledge_core/api/unified_retrieval_schemas.py`

Focused qualification:

- `tests/test_task6b_unified_retrieval_contract.py`

The tests lock additive lexical compatibility, required graph degradation warnings/reasons, prohibition on non-ready graph results, current-generation binding for ready graph evidence, exact source correlation shape, absence of duplicated canonical body/content and absence of a synthetic combined score.

## Explicit non-scope

Task 6B does **not**:

- wire `/v1/kc/search` to Graphiti;
- execute a graph query;
- run Graphiti/FalkorDB/local models;
- change Mason's bridge or skill;
- add graph readiness to `kc_status`;
- add a scheduler/background queue;
- add a migration;
- accept the pending Task 4 intended-host source-neutral Graphiti barrier.

The next bounded slice is Task 6C: implement an application-level coordinator that produces this contract by reusing the accepted lexical kernel and the existing validated source-neutral graph kernel, while preserving lexical-only behavior when graph evidence is not ready.
