# Task 6E — Mason Unified Retrieval Interpretation Qualification

Date: 2026-09-16

## Accepted behavior-bearing checkpoint

`0902a906a5c20e48dfcb07009d68eb9f3ccf9392`

Pull request: #14
GitHub Actions run: `35060788601`
Successful qualification: run attempt 2, job `104681272301`

## Scope

Task 6E keeps Mason's existing four literal Knowledge Core bridge operations unchanged:

- `kc_status`
- `kc_search`
- `kc_get_source`
- `kc_store`

Neither the packaged bridge nor the project-local standalone bridge required a transport change. Both already return the complete KC JSON response unchanged, so the additive Task 6B–6D unified retrieval fields naturally pass through the existing `kc_search` operation.

The Anton `knowledge-core` procedural skill now teaches Mason to interpret the top-level lexical results and additive graph lane as separate evidence lanes. A non-ready graph state does not invalidate otherwise-valid lexical evidence. A ready graph fact is derived retrieval evidence rather than canonical source wording. When exact wording, provenance, conflict resolution or verification matters, Mason follows the returned graph or lexical `resource_version_ref` through the existing literal `kc_get_source` operation.

The skill explicitly forbids direct Graphiti/FalkorDB access, raw HTTP/SQL fallbacks, filesystem substitution, provider credentials, graph synchronization, and creation of a second graph-search tool.

`kc_status` is not reinterpreted as graph readiness in Task 6E. Until the separately bounded Task 6F status contract is accepted, bounded graph readiness/degradation for a search is represented by the `graph.state` returned from `kc_search`.

## Deterministic qualification

Focused Task 6E tests verify:

- the packaged `MasonKnowledgeCoreBridge` returns a unified `kc_search` response unchanged;
- the project-local `tools/mason_kc_bridge.py` returns the same additive response unchanged;
- the existing `kc_search` request body remains unchanged;
- the procedural skill includes all eight accepted graph states;
- non-ready graph state instructs Mason to preserve relevant lexical evidence;
- graph source correlation uses `resource_version_ref` and exact-source follow-through through `kc_get_source`;
- graph facts are described as derived evidence rather than canonical wording;
- only the existing four literal operations remain documented;
- no `kc_graph_search`, `graphiti_sync`, or `sql_query` operation is introduced.

## Qualification attempts

### Attempt 1 — infrastructure failure after all behavior gates passed

Actions run `35060788601`, attempt 1, job `104680456001` used the exact accepted behavior head `0902a906a5c20e48dfcb07009d68eb9f3ccf9392`.

Passed before the final rehearsal:

- migrations;
- fast semantic suite: 177 passed, 1 skipped, 66 deselected;
- PostgreSQL G1–G21: 63 passed, 2 skipped, 179 deselected;
- pinned G22: 1 passed;
- RI-4 restart rehearsal.

The final SR-2 restart/replay rehearsal failed before its SR-2 apply/recovery logic while preparing its fresh isolated PostgreSQL instance. `sr2_host_qualification.py` reported that its inner `python -m alembic upgrade head` subprocess returned non-zero. The harness captures that subprocess output and the outer workflow did not expose the inner Alembic stderr on this failure path.

Task 6E changed only the Mason skill Markdown and its focused test file. The SR-2 host-qualification harness and database/runtime code were unchanged from the fully green Task 6D baseline. No Task 6E code change was made in response to this failure.

### Attempt 2 — exact-head retry succeeded

The same failed workflow job was rerun without changing the branch or commit. Actions run `35060788601`, run attempt 2, job `104681272301` completed successfully on the same head `0902a906a5c20e48dfcb07009d68eb9f3ccf9392`.

Attempt 2 passed:

- migrations;
- fast semantic suite;
- PostgreSQL G1–G21;
- pinned G22;
- RI-4 restart rehearsal;
- SR-2 restart/replay rehearsal.

The successful unchanged-head retry establishes the first final-step failure as transient qualification infrastructure rather than a Task 6E behavior defect. Both attempts are retained here rather than hiding the failed attempt.

## Explicit non-scope and limits

Task 6E does not:

- add or rename a bridge operation;
- change either bridge transport implementation;
- change a KC HTTP endpoint;
- synchronize or build Graphiti state;
- launch a local model, embedder or provider;
- qualify the pending Task 4 intended-host source-neutral graph runtime;
- add graph readiness/freshness fields to `kc_status`;
- run a live Mason/Cowork behavioral campaign;
- create a new migration or database contract.

Task 6E therefore accepts deterministic bridge compatibility and the Mason procedural interpretation contract. Live Mason behavior and SQL-only versus SQL+graph quality remain part of the later Task 6J qualification campaign unless separately authorized earlier.

Task 6F is the next bounded slice: expose graph readiness/freshness status without launching graph synchronization or a local model.
