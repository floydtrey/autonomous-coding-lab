# Standalone extraction provenance

Knowledge Core began as a component of `floydtrey/autonomous-coding-lab`.

It was extracted after the following access-control/graph milestones were sealed:

- KC-A — principal and service-credential foundation;
- KC-B — scope and authorization model;
- KC-C — hardened principal-aware consumer API;
- KC-D — production Graphiti runtime wiring.

Source branch:

`kc-graphiti-production-wiring`

Source extraction commit:

`699384b2291440067e30bdbba4042f846ef422f2`

KC-D implementation head qualified before the final documentation commit:

`dc312b21ea9f3e828801646cc6b487bfe4253fd1`

Qualification workflow:

Knowledge Core GitHub Actions run `35486786169`.

The standalone extraction deliberately excludes former client/harness integrations (Mason, MindsHub/Cowork, context-rotation helpers) and historical corpus pilots that were pinned to the parent ACL repository's commit history.

Those exclusions do not remove KC service behavior. They separate the reusable knowledge service from specific consumers and historical monorepo qualification artifacts.


## Standalone extraction qualification

Standalone branch: `knowledge-core-standalone`

Qualified standalone code head:

`b0e98794a8642293a18195810a0f1a950258bc8d`

Standalone GitHub Actions qualification:

`35489568825` — PASS

The standalone workflow ran from repository root and passed:

- package installation;
- all Alembic migrations;
- fast semantic tests;
- PostgreSQL qualification tests.

The qualification branch contained no paths named for ACL, Worker Lab, Mason, MindsHub, Cowork, or autonomous-worker components. Historical monorepo-pinned corpus pilots were intentionally excluded rather than relabeled as standalone evidence.

The next physical step is to copy this root tree into its own GitHub repository (recommended repository name: `knowledge-core`). The source ACL repository should retain its historical KC branches/evidence until the standalone repository has been copied and independently verified.
