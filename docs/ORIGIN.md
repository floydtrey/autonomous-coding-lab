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
