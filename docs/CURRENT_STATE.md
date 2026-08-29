# Current State

**Status:** Active checkpoint authority
**Read when:** Starting or resuming any project task.
**Last updated:** 2026-08-29
**Current boundary:** The Worker Lab adapter has a sealed read-only CLI execution path awaiting one
explicitly authorized synthetic proposal; workspace-write remains disabled.

## Exact repository state

### Autonomous Worker Framework

- Path: `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`
- Branch: `main`
- Integrated and tagged foundation commit: `2b31a96a872ee7d042614b5be917b1b4f3c1d57c`
- Named milestone: `v0.1.0-foundation`
- Documentation-refresh base: `31c27d6c2fad0c7365806c9cc643eef2f122f93b`
- Reviewed Worker Lab adapter milestone: `v0.2.0-worker-lab-adapter`.
- Milestone validation: 158 tests passed on 2026-08-29.
- Complete recoverable bundle: `C:\Users\MineTrackerWorker\backups\autonomous-worker-framework\autonomous-worker-framework-20260827-d83854f.bundle`
- Tagged foundation bundle: `C:\Users\MineTrackerWorker\backups\autonomous-worker-framework\autonomous-worker-framework-v0.1.0-foundation.bundle`
- Remote: none configured; the framework is currently local-only.
- The foundation inventory remains 123 tests; the adapter milestone inventory is 158 tests.

### Worker Lab

- Path: `C:\Users\MineTrackerWorker\repos\worker-lab`
- Integrated branch: `main`
- Phase 2 merge: `bcfb1562c3f274c0256ed4105d5f443ab0749ace` / PR `#4`
- Named milestone: `v0.2.0-phase2`
- Active Phase 3 design branch: `phase3/framework-interface-spec-v1`
- Active Phase 3 task: tracked `TERRA_PHASE3A.md` at the branch's verified starting HEAD
- Private remote: `https://github.com/floydtrey/worker-lab`
- Milestone validation: 257 tests passed; six expected Windows symlink capability tests skipped in
  both the candidate workspace and an independent rollback checkout.
- Final tagged bundle:
  `C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-v0.2.0-phase2.bundle`
- Final bundle SHA-256:
  `4325bdcc681cce2e47c6e8b271bb8e0661902d95e220c6a1083eb48531a56f7a`
- Phase 2 proves strict exercise/attempt records, isolated staged workspace preparation, restart
  verification, quarantine-backed disposal, interruption recovery, durable backup exclusions, CLI
  acceptance, and rollback recovery.

Recent capability checkpoints:

- `b2ae10f` — bounded general code-task execution
- `a79d244` — read-only Mine Tracker context probe
- `26e6bd9` — deterministic L1 task contract
- `2a6f36e` — trusted consumer validation evidence
- `9b46318` — verified local candidate publication
- `56fc18e` — identity-bound repository handoff
- `f8dbcb8` — one bounded fixture-repair attempt
- `84586f8` — bounded Codex execution seam
- `2f7b376` — deterministic local worker harness

### External product repositories

Mine Tracker and every other product repository are outside the active Phase 3A scope. Their current
branches, commits, issues, pull requests, and backups were not refreshed for this checkpoint and must
not be inferred from older framework history. Consult a consumer's own current authority only when a
future task explicitly authorizes that consumer. Phase 3A must not access one.

## Framework capability versus current authority

The framework already contains a proven bounded Codex execution seam. That technical capability does
not authorize Worker Lab to invoke it.

## Proven capabilities

The following have been demonstrated, not merely unit tested:

1. Deterministic local fixture mutation and validation in a separate repository.
2. ChatGPT-authenticated Codex execution with API-key rejection and GitHub credential stripping.
3. Explicit read-only and workspace-write worker modes; forbidden full-access modes fail closed.
4. Exact path boundary enforcement, unchanged Git HEAD enforcement, and dirty-workspace rejection.
5. Trusted quick/full consumer validation and structured worker evidence.
6. Identity-bound candidate commit, branch, draft PR, exact verification, one-time authorization, merge, post-merge CI, and cleanup.
7. A commissioning marker create/merge/remove cycle in a separate consumer without product behavior
   changes.
8. Read-only source analysis through a content-addressed consumer profile.
9. General one-task code execution outside the fixture harness.
10. One exact-path consumer regression task carried through controlled integration.

Historical external-product runs remain evidence that the framework boundary has operated, but their
consumer identities are not active Phase 3 context and grant no present authority.

## Current Worker Lab authority

- The Phase 3C framework adapter retains strict preparation, preflight, and read-only execution
  modes; all require the exact Worker Lab invocation protocol and fixed runtime identity.
- One explicitly authorized synthetic read-only proposal may use this path after Worker Lab's
  matching custody and lifecycle gates pass. Workspace-write remains disabled.
- Worker Lab may invoke the framework only after trusted review accepts contained process custody,
  identity verification, bounded retention, and recovery behavior at a new framework milestone.
- Existing historical worker runs prove framework capability; they do not grant a new Worker Lab
  integration permission.

## What it cannot yet do reliably

For the active Worker Lab integration, the unavailable capabilities are:

- invoke the framework or Codex;
- transition `READY -> RUNNING` through an integration adapter;
- persist strict invocation/result records;
- manage read-only proposals or workspace-write worker attempts;
- run evaluators or generate approval packets;
- retry, repair, schedule, coordinate, publish, merge, or access an external product repository.

## Current security posture

- Codex CLI audited version: `0.149.1`
- Managed authentication: ChatGPT login only
- Forbidden API-key environment variables: `OPENAI_API_KEY`, `CODEX_API_KEY`
- GitHub credential-like worker variables: stripped
- Allowed worker sandbox modes: `read-only`, `workspace-write`
- Windows sandbox configuration pinned by the runtime
- Worker target must be a different Git repository from the framework
- Workers have no GitHub publishing or merge role

Changing any item above is a separate framework security decision. A Worker Lab interface
specification may depend on these controls but may not copy, weaken, or silently replace them.

## Active development policy

Workers mature only on isolated synthetic exercise repositories. External product work remains outside
the proving path until objective graduation gates are met and the current task explicitly authorizes
that consumer.

Worker Lab owns curriculum, attempt, authority, lifecycle, evidence, failure, evaluation, playbook,
and graduation records. The framework owns Codex authentication, credential isolation, sandboxing,
runtime configuration, subprocess execution, target-repository boundaries, and execution timeout.
Neither repository may silently duplicate or widen the other's authority.

## Immediate next recommendation

Recommended next sequence:

1. Resolve the exact commit tagged `v0.2.0-worker-lab-adapter` and pin that full identity in Worker Lab.
2. Checkpoint and validate the reviewed Worker Lab Phase 3C client/custody candidate.
3. Keep CLI preflight/execution and real `READY -> RUNNING` disabled.
4. Require a separate explicit authorization before one live synthetic read-only proposal.

## New-chat handoff prompt

Use this concise prompt when a new conversation is required:

> In `C:\Users\MineTrackerWorker\repos\worker-lab`, read `docs/START_HERE.md`, verify Git state, and
> follow the tracked `TERRA_PHASE3A.md` handoff. Read this framework's `AGENTS.md`,
> `docs/START_HERE.md`, current limitations here, and only the framework contracts routed by the
> handoff. Framework capability exists, but Worker Lab invocation is not authorized. Keep the
> framework read-only, use synthetic project-agnostic scope, and stop before implementation or any
> worker execution.
