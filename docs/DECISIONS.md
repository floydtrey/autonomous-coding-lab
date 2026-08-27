# Durable Decisions

This is a compact decision ledger. These decisions remain active until explicitly superseded here.

## D001 — Separate standalone framework

The Autonomous Worker Framework is its own repository. Workers operate on separate consumer repositories and isolated worktrees. Mine Tracker is the first consumer, not framework source.

## D002 — ChatGPT-managed Codex authentication only

Codex workers use the signed-in ChatGPT account. `OPENAI_API_KEY` and `CODEX_API_KEY` fail closed. GitHub credential-like variables are stripped from worker subprocesses.

## D003 — Only two worker sandbox modes

`read-only` is used for analysis and planning. `workspace-write` is used for an exact implementation contract. Danger/full-access and implicit sandbox modes are forbidden.

## D004 — Trusted controller is distinct from restricted workers

The active ChatGPT development conversation is trusted maintainer/controller authority under the user's delegation. Codex subprocesses remain restricted workers. Rules written to constrain workers do not prevent the trusted controller from reviewing, publishing, or merging exact validated candidates.

## D005 — No autonomous publisher authority

The publisher is mechanical and is not a new AI entity. It cannot write code, approve work, or merge. This avoids overlapping authority and unnecessary system complexity.

## D006 — Verification is exact and read-only

Verification binds the task digest, issue, PR, branch, head, current-main base, and exact changed path. It tests the exact merge candidate and has no mutation authority.

## D007 — One-time exact-head merge authorization

Merge permission is recorded only after local validation, independent diff review, protected PR CI, and exact verification. Authorization names one head/base/path and is closed after use. It is not reusable.

## D008 — Stop at the first failed boundary

Identity, scope, auth, sandbox, diff, and validation failures stop the run. Do not silently widen scope, continue to later stages, or treat partial success as readiness.

## D009 — Quick routine loop, full milestone gate

Focused/quick validation is the normal development loop. Full framework or consumer validation runs once the bounded candidate is ready and again through protected integration gates.

## D010 — Prove basics before orchestration

Do not build a large queue, multi-agent hierarchy, publisher intelligence, or generalized recovery system before repeated real tasks demonstrate the need. Add one capability at a time with regression coverage.

## D011 — Mine Tracker protected authority remains outside workers

Workers may not change governance, autonomy machinery, current-direction/baseline records, runtime data, authentication, permissions, schema/migrations, transaction/audit authority, durable identity, consequential Vera authority, dependencies/installers, or checkpoint versions without explicit Patch Controller review.

## D012 — Private repository inspection authorization

The user explicitly authorized ChatGPT-managed Codex workers to inspect the private Mine Tracker repository as needed for this project under the established sandbox, credential, scope, and approval controls. The user also authorized the trusted ChatGPT controller to read and write both project repositories and project folders as needed for this build. This authorization does not remove task-level scope or safety controls.

## D013 — Human-readable approval evidence

The product owner is not expected to validate unfamiliar code. Meaningful changes should be presented with behavior, acceptance evidence, files changed, risks, unresolved concerns, and rollback identity. The trusted controller remains responsible for technical review.

## D014 — Disposable applications before broader Mine Tracker work

Experimental workers will mature on isolated disposable applications before receiving broader Mine Tracker product authority. These exercises do not permanently train the underlying model; they improve the framework, prompts, task contracts, validation, failure catalog, approval evidence, and controller judgment. Mine Tracker product-source worker changes remain paused until the objective graduation gates in `PROVING_PROGRAM.md` are met.

## D015 — Enterprise direction informs boundaries, not premature architecture

Mine Tracker may become the foundation of an enterprise safety systems suite. Current work should favor security, stability, modularity, efficient operation, and clean expansion seams, but must not implement speculative enterprise, multi-site, or generalized safety-suite architecture before current needs and proving evidence justify it.
