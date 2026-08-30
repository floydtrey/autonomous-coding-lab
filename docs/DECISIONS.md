# Durable Decisions

Entries remain active until explicitly superseded.

## ACL-D001 — One private integration repository

**Status:** Active

Autonomous Coding Lab will become one private program and repository containing
Worker Lab, the execution framework, and local-model evaluation tools. Original
repositories remain unchanged recovery sources during migration.

## ACL-D002 — Internal boundaries replace repository boundaries

**Status:** Active

Consolidation does not consolidate authority. Worker Lab, execution security,
and model evaluation remain separate packages and trust boundaries with explicit
dependency direction and tests.

## ACL-D003 — Audit before import

**Status:** Active

No component code is copied before M1 accepts its source identity, provenance,
exclusions, directory path, path repairs, license treatment, and parity plan.

## ACL-D004 — Migration does not change behavior

**Status:** Active

Import and structural migration are separated from refactoring, new features,
prompt changes, dependency upgrades, and authority expansion.

## ACL-D005 — Disposable repositories remain external

**Status:** Active

Worker target repositories and validation workspaces remain separate disposable
Git repositories. The controlling monorepo cannot be its own worker target.

## ACL-D006 — Stable component roots through integration

**Status:** Proposed for M1 acceptance

The three sources land under `components/<source-name>/` and remain there through
M6. Import, prefix repair, restructuring, refactoring, and feature development
are separate changes. A later move to `apps/`, `packages/`, or `tools/` must show
an actual benefit and repeat affected parity checks.

## ACL-D007 — Full ancestry, exact snapshot imports

**Status:** Proposed for M1 acceptance

Each import retains complete source ancestry without squashing. The approved
source commit and imported tree are recorded independently of the monorepo merge
commit. Ignored, untracked, unreadable, generated, and machine-local data are not
introduced by the history import.

## ACL-D008 — Execution disabled across identity migration

**Status:** Proposed for M1 acceptance

Standalone repository identity is part of the existing Worker Lab/framework
security contract. Component import does not grant authority to replace it.
Read-only and workspace-write execution stay disabled until component-scoped
monorepo identity is designed, tested, reviewed, and explicitly authorized.

## ACL-D009 — Component-local environments first

**Status:** Proposed for M1 acceptance

Worker Lab, the framework, and Local Model Bench retain their own runtimes and
validation commands through their import milestones. Dependency or packaging
unification is post-parity work.
