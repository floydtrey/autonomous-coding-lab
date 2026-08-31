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

**Status:** Active — accepted 2026-08-30

The three sources land under `components/<source-name>/` and remain there through
M6. Import, prefix repair, restructuring, refactoring, and feature development
are separate changes. A later move to `apps/`, `packages/`, or `tools/` must show
an actual benefit and repeat affected parity checks.

## ACL-D007 — Full ancestry, exact snapshot imports

**Status:** Active — accepted 2026-08-30

Each import retains complete source ancestry without squashing. The approved
source commit and imported tree are recorded independently of the monorepo merge
commit. Ignored, untracked, unreadable, generated, and machine-local data are not
introduced by the history import.

## ACL-D008 — Execution disabled across identity migration

**Status:** Active — accepted 2026-08-30

Standalone repository identity is part of the existing Worker Lab/framework
security contract. Component import does not grant authority to replace it.
Read-only and workspace-write execution stay disabled until component-scoped
monorepo identity is designed, tested, reviewed, and explicitly authorized.

The accepted identity distinguishes source provenance from integration identity
and binds both participating components plus a closed root/shared invocation
dependency set. Its acceptance does not enable execution.

## ACL-D009 — Component-local environments first

**Status:** Active — accepted 2026-08-30

Worker Lab, the framework, and Local Model Bench retain their own runtimes and
validation commands through their import milestones. Dependency or packaging
unification is post-parity work.

## ACL-D010 — Scoped fail-closed integration identity

**Status:** Active — accepted 2026-08-30

Record source provenance separately from monorepo integration identity. Bind the
monorepo commit/tree, component prefix/subtree, adapter blob, runtime identities,
and a closed invocation dependency set. Tracked/untracked dirtiness, unreadable
or undeclared executable/configuration state, path escape, substitution, digest
mismatch, or stale provenance inside that scope fails closed. Unrelated material
outside the scope does not block.

## ACL-D011 — Directional task authority

**Status:** Active — accepted 2026-08-30

Planner output is untrusted. Worker Lab accepts plans, assigns permanent IDs and
authorizes bounded tasks. Task Creator may only transform accepted plans without
widening them. The framework transports and executes exact authorized tasks;
Worker Lab independently verifies results and controls lifecycle progression.
Benchmark templates evaluate candidates but do not authorize work.

## ACL-D012 — Native evidence schemas through M4

**Status:** Active — accepted 2026-08-30

Preserve native Worker Lab, framework, and benchmark evidence schemas with
directional adapters. Adapters cannot upgrade evidence authority. Defer any
controller-owned typed evidence-reference envelope until M5 and add it only if
integration tests show a need.

## ACL-D013 — Worker Lab owns model-routing policy through M6

**Status:** Active — accepted 2026-08-30

The benchmark supplies reviewed recommendations. Worker Lab's trusted controller
owns accepted role-to-model/profile routing. The framework validates and executes
only an exact authorized profile and cannot select, fall back, or escalate
automatically. A separate orchestration component is deferred until post-M6.

## ACL-D014 — Dual-layer exact-import validation and recovery

**Status:** Active — accepted 2026-08-30

Before M2, create a clean accepted checkpoint, reverify source identity, and
create a checksummed framework recovery bundle or mirror. Preserve complete
reachable ancestry and namespace source tags. Prove imported subtree equality
and untouched parity from a disposable standalone reconstruction before a
separate in-monorepo prefix-adaptation commit.

## ACL-D015 — Private-only treatment for unlicensed components

**Status:** Active — accepted 2026-08-30

Worker Lab and the execution framework may be consolidated only inside the
private Autonomous Coding Lab repository. Their missing license files grant no
public redistribution or relicensing authority. Preserve Local Model Bench's
MIT license and notices with that component.

## ACL-D016 — Canonical H01 witness

**Status:** Active — accepted 2026-08-30

`docs/handoffs/H01-Handoff.txt`, exactly as supplied by the user, is the
canonical H01 witness. The malformed `.md` duplicate differs only by its missing
first-line heading marker and is excluded from the checkpoint rather than
tracked as a second handoff.

## ACL-D017 — Worker Lab source snapshot and historical disposition

**Status:** Active — accepted 2026-08-30

Preserve Worker Lab's complete reachable ancestry through
`ca55e30ccbcbf2318d73b3ef8a65f66bb9e1e684` and import that exact HEAD tree when
M3 is separately authorized. The 17 current working-tree deletions and their
Legacy copies are separately reviewed historical disposition; they do not alter
the selected source tree and must not be committed, restored, or imported from
the working tree automatically.
