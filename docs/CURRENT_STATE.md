# Current State

**Status:** Active checkpoint authority
**Read when:** Starting or resuming any project task.
**Last updated:** 2026-08-27
**Status:** Foundation tagged; Worker Lab selected as the next durable product; experimental Mine Tracker product work paused.

## Exact repository state

### Autonomous Worker Framework

- Path: `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`
- Branch: `main`
- Integrated and tagged foundation commit: `2b31a96a872ee7d042614b5be917b1b4f3c1d57c`
- Named milestone: `v0.1.0-foundation`
- Complete recoverable bundle: `C:\Users\MineTrackerWorker\backups\autonomous-worker-framework\autonomous-worker-framework-20260827-d83854f.bundle`
- Tagged foundation bundle: `C:\Users\MineTrackerWorker\backups\autonomous-worker-framework\autonomous-worker-framework-v0.1.0-foundation.bundle`
- Remote: none configured; the framework is currently local-only.
- Test inventory: 123 tests; all passed on integrated `main` before this state refresh.

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

### Mine Tracker

- Permanent checkout: `C:\Users\MineTrackerWorker\repos\advanced-mine-asset-inspection`
- Permanent checkout branch: `chore/worker-result-v1` (intentionally not advanced during worker tasks)
- GitHub repository: `floydtrey/advanced-mine-asset-inspection`
- Certified remote `main`: `a7b2c560c22ed13442cddc9c2e3caa0b4fcaa96a`
- Protected required check: `Python tests`, strict against current `main`
- Admin enforcement and conversation resolution are enabled; force pushes and deletions are disabled.

Known backup:

- `C:\Users\MineTrackerWorker\backups\mine-tracker\mine-tracker-20260826-190202-fa2f92b57463.bundle`
- Bundle was verified complete when created. It predates the worker commissioning and first real task; GitHub history contains the later milestones.

## Proven capabilities

The following have been demonstrated, not merely unit tested:

1. Deterministic local fixture mutation and validation in a separate repository.
2. ChatGPT-authenticated Codex execution with API-key rejection and GitHub credential stripping.
3. Explicit read-only and workspace-write worker modes; forbidden full-access modes fail closed.
4. Exact path boundary enforcement, unchanged Git HEAD enforcement, and dirty-workspace rejection.
5. Trusted quick/full consumer validation and structured worker evidence.
6. Identity-bound candidate commit, branch, draft PR, exact verification, one-time authorization, merge, post-merge CI, and cleanup.
7. Mine Tracker commissioning marker create/merge/remove cycle without product behavior changes.
8. Read-only Codex analysis of real private Mine Tracker source using a content-addressed repository profile.
9. General one-task code execution outside the fixture harness.
10. First real Mine Tracker task: Codex identified and added archived-asset historical-retrieval regression coverage in `tests/test_assets.py`.

First real task evidence:

- Task: GitHub issue `#32`
- Candidate: PR `#33`
- Worker candidate head: `2a9ffa047ab051cf6659f21eac33d38deed144b2`
- Task digest: `sha256:cbd19f224b5feaf130c355966216edfbbc25fd150b3fa198022ed454a767c6e3`
- Context digest: `sha256:8aedc42a5668654b08b40ff3da250733ba9263913eb97700e5df250bbe0372ac`
- Exact verification run: `33066488282` — passed
- Post-merge CI run: `33066719376` — passed
- Resulting `main`: `a7b2c560c22ed13442cddc9c2e3caa0b4fcaa96a`
- Product behavior changed: no; regression coverage only

## What the system can do now

- Inspect a bounded Mine Tracker area and propose one low-risk task.
- Bind the proposal to exact repository/context identity.
- Let a restricted worker implement one exact-path task.
- Reject out-of-scope files, worker commits, stale heads, dirty repositories, bad diffs, or failed tests.
- Carry a validated candidate through controlled GitHub integration under trusted-controller authority.

## What it cannot yet do reliably

- Convert arbitrary natural-language product requests into trusted task contracts without controller review.
- Select context and writable files automatically for every Mine Tracker subsystem.
- Perform independent semantic AI code review as a formal framework stage.
- Generate a standardized plain-language approval packet with screenshots/demonstrations for UI work.
- Safely execute multi-file product behavior changes as a repeatedly proven routine.
- Decompose and coordinate parent/child task graphs.
- Generalize repair/recovery beyond the earlier single deterministic fixture retry.
- Publish formal Mine Tracker checkpoints or version changes.

## Current security posture

- Codex CLI audited version: `0.149.1`
- Managed authentication: ChatGPT login
- Forbidden API-key environment variables: `OPENAI_API_KEY`, `CODEX_API_KEY`
- GitHub credential-like worker variables: stripped
- Allowed worker sandbox modes: `read-only`, `workspace-write`
- Windows sandbox configuration pinned by the runtime
- Worker target must be a different Git repository from the framework
- Workers have no GitHub publishing or merge role

## Active development policy

Meaningful Mine Tracker worker changes are paused while workers build and use Worker Lab plus its disposable exercise repositories. Mine Tracker remains available for trusted-controller development and may receive emergency/manual fixes, but experimental workers should not alter its product behavior until the proving gates in `PROVING_PROGRAM.md` are met.

The first Mine Tracker task remains useful evidence, but one successful test-only task is not enough to establish broad trust.

## Immediate next recommendation

Recommended next sequence:

1. Create the separate local `worker-lab` repository from the design in `WORKER_LAB_DESIGN.md`.
2. Follow `PHASE_1_SPEC.md` and `TESTING_AND_AUTHORITY.md`; implement only the headless protected records, canonical identity, storage, lifecycle, CLI, backup, and numbered-test planning boundary.
3. Add the Local Record Ledger as the first curriculum family rather than as an unrelated application.
4. Let workers complete multiple bounded tasks across its domain, persistence, import/export, reporting, failure, and recovery boundaries.
5. Add a read-only evidence dashboard only after the headless workflow produces real attempt data.
6. Do not resume Mine Tracker product-source worker changes until the graduation gates in `PROVING_PROGRAM.md` are satisfied.

## New-chat handoff prompt

Use this concise prompt when a new conversation is required:

> Read `AGENTS.md` and `docs/START_HERE.md` in `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`. Verify Git state, then follow the Worker Lab Phase 1 route to `PHASE_1_SPEC.md` and `TESTING_AND_AUTHORITY.md`. Do not load unrelated or historical documents by default. Preserve all security and authority boundaries, keep experimental protected-project changes paused until the proving gates are met, and update `CURRENT_STATE.md` at the next milestone.
