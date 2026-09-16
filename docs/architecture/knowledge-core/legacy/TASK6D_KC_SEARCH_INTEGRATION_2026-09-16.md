# Task 6D — `kc_search` Unified Retrieval Integration Qualification

Date: 2026-09-16

## Accepted behavior-bearing checkpoint

`65943a1e12dd08bf01a1e330ceb43ede1e2e6e13`

Pull request: #13
GitHub Actions qualification run: `35060185109`

## Scope

Task 6D wires the already-accepted Task 6B/6C unified retrieval contract/coordinator behind the existing bootstrap `POST /v1/kc/search` operation.

The request surface remains the existing `RetrievalSearchRequest`: `query`, `limit`, and `include_superseded`. Existing lexical response fields remain top-level with their established `kc-lexical-evidence-v2` meaning. The response now also carries additive `kc-unified-retrieval-evidence-v1` graph evidence and warnings.

The route constructs the accepted lexical-first `UnifiedRetrievalCoordinator`. Optional graph augmentation is supplied only through an explicit trusted-host `UnifiedGraphSearchBinding`. No binding produces valid lexical evidence plus `graph.state="disabled"`; it does not attempt graph access.

The route preserves bootstrap admission and fixed principal `local_owner`. A supplied graph binding is rejected during application composition unless its caller principal exactly matches the bootstrap principal. If a separate lexical retrieval Authority evaluator is configured, `retrieval.search_text` is still evaluated before lexical retrieval and remains fail-closed.

The existing `/v1/retrieval/search`, `kc_store`, `kc_get_source`, and `kc_status` surfaces are not changed by Task 6D.

## Qualification

Actions run `35060185109` completed successfully on exact checkpoint `65943a1e12dd08bf01a1e330ceb43ede1e2e6e13`.

Passed gates:

- PostgreSQL migrations;
- fast semantic suite, including the Task 6D endpoint tests;
- PostgreSQL G1–G21 qualification suite;
- pinned SR-2 G22 real-document pilot;
- RI-4 restart rehearsal;
- SR-2 restart/replay rehearsal.

Focused Task 6D tests verify:

- existing `kc_search` request fields and lexical response fields remain available when graph augmentation is not configured;
- the additive graph lane reports `disabled` without calling graph retrieval when no graph binding exists;
- ready graph evidence can pass through the same literal `kc_search` operation with exact source-neutral KC correlation and without provider source body/full canonical content;
- graph search uses the fixed bootstrap principal `local_owner`;
- a graph binding cannot substitute another principal;
- a configured fail-closed text Authority decision still occurs before lexical retrieval.

## Explicit non-scope and limits

Task 6D does not:

- synchronize or build Graphiti state;
- launch a local model, embedder, provider, scheduler, or background worker;
- establish source-neutral Task 4 intended-host Graphiti acceptance;
- add graph readiness/freshness inspection beyond the Task 6B/6C bounded search states;
- change the Mason bridge or procedural-memory skill;
- add a second graph-search tool;
- change `kc_status`;
- create a lexical/graph score-fusion policy;
- add or modify a database migration.

Task 6D therefore accepts the endpoint integration contract, not an intended-host SQL+Graphiti runtime campaign. Task 6E is the next bounded slice and is limited to Mason bridge/skill interpretation of the additive response while retaining the literal `kc_search` operation and canonical follow-through through `kc_get_source`.
