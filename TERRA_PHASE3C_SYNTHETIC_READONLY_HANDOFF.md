# Terra Handoff — Synthetic Read-Only Proposal Contract and Evaluator Evidence

**Status:** Bounded, non-executing implementation candidate; stop for Sol review
**Worker Lab base:** `8ee1d00325b9a345d9bad353405b261e562bbaf6` on `main`
**Framework base:** `2d8c93312103015125f0eef9e2afdc697a45d244` / `v0.2.0-worker-lab-adapter`
**Execution authority:** Disabled

## Objective

Complete the last non-executing prerequisites for a separately authorized, single synthetic
read-only proposal: a precise test contract and a Worker Lab-owned, durable evaluator-evidence
collector.  The collector must produce evidence that `accept_execute_response` can use without
trusting caller-constructed validation success or worker prose.

This is preparation only.  Do not invoke Codex, check live authentication, start the framework
adapter, create a real invocation, send an adapter request, or move any real attempt from `READY`
to `RUNNING`.

## Starting checks and protected boundary

1. Read `AGENTS.md`, `docs/START_HERE.md`, this handoff, and the Phase 3 sections of
   `docs/CURRENT_STATE.md`, `docs/PHASE3_SPEC.md`, and `docs/PHASE3C_SECURITY_DECISIONS.md`.
2. Confirm Worker Lab is at the base above, on `main`, and has no tracked changes.  The sole
   permitted untracked path is `docs/8_27_26_ChatGPT_History`; do not open, scan, hash, stage,
   modify, or otherwise touch it.
3. Confirm the framework tag still resolves to the base above and is clean.  Do not change the
   framework in this handoff unless Sol separately expands scope.
4. Stop if repository identity, the protected history exception, or authority differs.  Preserve
   every existing change; do not reset, clean, restore, stash, commit, tag, push, create a PR, or
   perform backup/cleanup.

## Contract to implement

Add one narrowly scoped Worker Lab evaluator-evidence collector, preferably in a new module such
as `worker_lab/read_only_evidence.py`.  It receives only sealed inputs: the exact
`InvocationRecord`, a canonical workspace path, Worker Lab state root, and an injected sealed test
executor for tests.  It returns the existing `WorkspaceEvidence` plus a tuple of existing
`ValidationStage` objects, or raises `LabValidationError`.  It must not accept worker-controlled
commands, paths, test IDs, expected/observed text, pass/fail fields, environment, or configuration.

The collector must independently:

1. Reload and validate the receipt using the protected state store, then verify its digest, attempt,
   starting commit, workspace root/path digests, and `PREPARED` state against the invocation.
2. Inspect the workspace after custody absence proof using the established safe Git/path inspection
   boundary.  Require detached `HEAD` equal to `starting_commit`, empty status, no Git config,
   remote, alternate-object, receipt, or workspace-byte drift, and no reparse-path substitution.
3. Recompute the immutable catalog/test-plan binding from protected Worker Lab records.  The test
   IDs and order must be exactly `record.test_ids`; the worker may not select, skip, reorder, or
   supply a command.
4. Invoke only a test-executor selected by the protected catalog/profile mapping.  The executor
   contract must be explicit and injectable for focused tests, receive no worker text, and return
   controller-observed exit/status facts.  A test failure, missing stage, duplicate stage,
   unexpected stage, malformed result, timeout, or exception fails closed.
5. Build each `ValidationStage` entirely from collector observations.  `expected` and `observed`
   must be bounded controller-authored summaries; no raw stdout, stderr, absolute paths,
   credentials, or worker prose may be retained.
6. Reinspect the workspace after validation.  The before/after protected observations must match;
   any change rejects acceptance.  The collector must not write the workspace or alter the receipt.

The collector returns no durable success record by itself.  `accept_execute_response` remains the
sole acceptance seam and must receive this collector directly (not an externally supplied success
tuple).  Retain the existing injected fake seams for unit tests, but do not leave a production
caller able to fabricate `WorkspaceEvidence` or passing `ValidationStage` objects.

## Required focused tests

Extend the directly bound integration tests and add a focused collector test file if that keeps the
security boundary clear.  Prove at least:

- valid inert fixtures generate ordered, controller-authored evidence and acceptance succeeds only
  after the exact durable custody proof;
- caller-supplied passing evidence is rejected or is impossible through the public acceptance API;
- changed `HEAD`, status, workspace bytes, receipt fields, root/path digest, Git configuration,
  remotes, or alternates fail before a candidate can be accepted;
- a catalog/test-plan digest mismatch, reordered/missing/extra test ID, unsealed test command, or
  worker-provided command fails closed;
- executor nonzero exit, timeout, malformed outcome, exception, duplicate/missing stage, and
  post-validation mutation each fail with no proposal acceptance;
- retained expected/observed summaries reject over-limit, NUL, absolute Windows/UNC path, and
  credential/token-marker content; and
- the collector never invokes an adapter/Codex/runtime path and never makes a real lifecycle
  transition.  Use only fakes and inert local fixtures.

Keep `worker-lab-v3` immutable.  Add cases only to its already bound test files where applicable;
do not change catalog definitions, schemas, policies, roles, exercises, CLI behavior, workspace
preparation/disposal, backup scope, or framework source.

## Validation and report

Run only the smallest relevant Worker Lab tests: the collector/integration slice, then directly
affected storage/workspace/test-plan tests if required.  Compile changed Python and run
`git diff --check`.  Do not run a full suite, live preflight, authentication check, adapter process,
synthetic proposal, backup/restore, rollback, remote operation, or cleanup.

Create `TERRA_PHASE3C_SYNTHETIC_READONLY_REPORT.md` in Worker Lab.  Record starting identity,
documents/source read, exact changed files, test commands/results, all skips/failures, the public
collector API, and the remaining explicit stop: live synthetic proposal still needs separate Sol
review and user authorization.

Leave the candidate uncommitted for Sol review.
