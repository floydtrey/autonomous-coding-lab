# Knowledge Core Task 6F — Graph Readiness/Freshness Status

Date: 2026-09-16

## Accepted checkpoint

- Accepted behavior-bearing checkpoint: `e34ca35cb1d2a31bdb7ec45d9799dd1f685c66d5`.
- Base accepted Task 6E merge: `e42ca0278a1d5dafaa21c90a232c98f71059590a`.
- Pull request: #15, `KC Task 6F: graph readiness status`.
- Qualification: GitHub Actions `35062593583`, fully green on the exact behavior checkpoint.

## Qualified files

The behavior checkpoint contains exactly these Task 6F files relative to the accepted Task 6E merge:

- `components/knowledge-core/knowledge_core/application/graph_readiness.py`;
- `components/knowledge-core/knowledge_core/api/consumer_schemas.py`;
- `components/knowledge-core/knowledge_core/api/app.py`;
- `components/knowledge-core/tests/test_task6f_graph_readiness_status.py`.

Later Task 6F commits are documentation/evidence only and do not change these qualified bytes.

## Accepted behavior

`GET /v1/kc/status` preserves all previously accepted canonical/text status fields and adds a bounded `graph` object using the established public graph states:

- `disabled`;
- `no_build`;
- `ready`;
- `stale`;
- `pending`;
- `unvalidated`;
- `failed`;
- `unavailable`.

With no trusted-host graph binding, status reports `disabled` without consulting graph/provider state.

With a graph binding, readiness is classified only from Knowledge Core durable evidence plus the current accepted TEXT generation and the injected adapter descriptor. The classifier reads the existing projection-attempt/validation ledger and uses the same namespace, scope, backend/version, adapter config digest, source-neutral graph profile identity, and independent validation requirement used by trusted graph retrieval.

A graph build is `ready` only when a current-compatible attempt is succeeded, durably validated, and satisfies the adapter's current validation requirement when one exists. A usable ready build remains `ready` even if another compatible attempt is pending or failed, because the accepted trusted retrieval path can still use the validated build.

When no ready build exists, the bounded classifier distinguishes current-compatible pending, unvalidated, and failed evidence; historical/incompatible attempts become `stale`; no durable attempt for the configured graph target becomes `no_build`. Unexpected readiness-inspection failure degrades only the graph status to nondisclosing `unavailable` and does not erase otherwise-valid canonical/text readiness.

Status exposes at most one representative attempt ID. It does not return an unbounded attempt history.

## Explicit non-scope

Task 6F does not:

- call `adapter.search()` or retrieve graph facts;
- call `adapter.project()` or synchronize/build Graphiti;
- query FalkorDB for provider data;
- invoke embeddings, reranking, or a local model;
- discover or start a provider/model;
- create a scheduler, queue, or background work;
- change graph mutation authority;
- change `kc_search` trusted graph retrieval behavior;
- add a database migration;
- prove current provider liveness;
- satisfy the still-pending Task 4 intended-host source-neutral Graphiti/FalkorDB/local-model acceptance barrier.

`ready` therefore means that KC has a current compatible durably validated graph build according to the accepted ledger and adapter contract. Actual provider availability remains a query-time concern.

## Qualification

Actions `35062593583` passed on exact head `e34ca35cb1d2a31bdb7ec45d9799dd1f685c66d5`:

1. PostgreSQL migrations;
2. fast semantic suite, including Task 6F focused state/endpoint tests;
3. PostgreSQL G1–G21 qualification suite;
4. pinned SR-2 G22 real-document pilot;
5. RI-4 local-host restart rehearsal;
6. SR-2 local-host segment restart/replay rehearsal.

The focused Task 6F tests verify no-build/stale/pending/unvalidated/failed/ready classification, enforcement of the current validation requirement, disabled status without a graph binding, additive status endpoint wiring, and absence of provider search/projection calls during readiness classification.

## Next boundary

Task 6F acceptance authorizes Task 6G: establish a separate autonomous memory-candidate/admission boundary while keeping explicit trusted/user-directed `kc_store` semantics unchanged. Task 6F does not itself authorize Task 6H context-compaction work.