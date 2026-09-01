# Limited To-Do

Small, deferred improvements for when we need to work under tight model or token limits. This is a
backlog, not current implementation authority.

## Resource efficiency

- Define a lightweight task-intake format: goal, allowed files, required tests, stop condition, and
  expected report. Reuse it for bounded worker tasks.
- Tighten the reusable context contract so an active session reads the authoritative entry documents
  once, records the exact versions/commit consulted, and rereads only files affected by a change or a
  new decision.
- Separate durable authority from historical discussion more clearly, so future sessions can load a
  short current-state document before consulting deeper design history.
- Add a concise handoff snapshot format: current branch/commit, uncommitted files, active boundary,
  decisions already made, required next tests, and known risks.
- Identify repeated expensive test setup, especially temporary Git repository creation, and determine
  whether fixtures can be safely reused without weakening isolation or test independence.
- Keep the numbered test profiles current and use the smallest applicable profile during iteration;
  reserve complete suites for milestones and broad cross-cutting changes.

## AI workflow experiments

- Continue measuring bounded Terra implementation runs against High-reasoning review: elapsed time,
  test time, model usage, defects found, and correction cycles.
- Define when a lighter model may safely prepare documentation, test cases, reports, or mechanical
  changes, and when a higher-reasoning reviewer is mandatory.
- Improve worker reports so they are compact but always include changed files, commands, results,
  assumptions, unresolved risks, and final Git state.
- Avoid duplicate reviews: use one focused implementation review, then one merge-gate review for a
  completed boundary rather than repeatedly rereviewing unchanged work.

## Guardrails

- Revisit every deferred item only when it advances a current completion condition or demonstrably
  reduces recurring cost without weakening security, testing, or scope control.
- Do not create a generalized optimization framework merely to solve a small current inconvenience.
