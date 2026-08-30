# Merger Contract

**Version:** Draft 0.2
**Status:** M1 audit candidate; requires human acceptance before code import

## 1. Objective

Create one private Autonomous Coding Lab repository and program from three
proven components without losing source history, test evidence, rollback
identity, security boundaries, or the ability to explain every path change.

## 2. Sources in scope

1. `worker-lab`
2. `autonomous-worker-framework`
3. `local-model-bench`

No product repository, MineTracker source, runtime workspace, backup, generated
model file, credential, conversation export, or unrelated project is in scope.

## 3. Authority transfer

- Source repositories remain authoritative during M0 and M1.
- Importing bytes does not transfer authority.
- Each component transfers only after its import commit records provenance and
  its original focused and milestone tests pass from the new repository.
- The old repositories remain recoverable and unchanged throughout migration.
- They may be frozen only after the final monorepo integration milestone.

## 4. Decision supersession

Framework decisions D001 and D016 currently require separate repositories. The
user has directed consolidation into one private program. Their security and
responsibility separation will be preserved as internal package and process
boundaries. The old decisions are not rewritten in source repositories during
M0 or M1; M5 will mark them historically superseded only after the replacement
boundaries have passed parity and security review.

## 5. Import strategy

The M1 candidate strategy is:

1. Fetch the exact approved local source commit and import its complete Git
   ancestry without squashing into a dedicated prefixed directory.
2. Preserve that source's internal relative layout during its first parity run.
3. Record source repository, branch, commit, tags, remote state, imported tree
   digest, merger commit, and validation evidence in the migration log.
4. Do not restructure and import in the same milestone.
5. Keep the component roots stable through M6. A later product-layout change is
   a separate post-integration proposal, not part of this merger.

Candidate landing paths:

| Source | Landing path | Stability rule |
|---|---|---|
| Worker Lab | `components/worker-lab/` | Stable through M6 |
| Execution framework | `components/autonomous-worker-framework/` | Stable through M6 |
| Local Model Bench | `components/local-model-bench/` | Stable through M6 |

Component-local `AGENTS.md`, docs, tests, and relative layouts remain intact on
first import. Root governance applies program-wide; nested guidance applies
inside its component.

## 6. Exclusions

Never import automatically:

- nested `.git` directories;
- virtual environments, caches, logs, PID files, temporary test directories, or
  prepared worker workspaces;
- ignored or untracked files until individually classified;
- full benchmark result runs unless a selected evidence packet is approved;
- local model binaries, GGUF files, installers, credentials, tokens, backups, or
  conversation exports;
- source remotes, local Git configuration, alternate object stores, or hooks.

A complete-history import carries tracked files only. A tracked historical
report remains provenance even when it contains an obsolete local path; it does
not become current authority.

## 7. Path-change rule

Every moved path must appear in `PATH_MIGRATION_LEDGER.md` with:

- old repository and path;
- new path;
- references that require repair;
- validation command;
- milestone and commit;
- rollback identity.

No broad search-and-replace is accepted without review of every affected path.

## 8. Behavioral-change rule

Migration commits move or adapt code only as required to preserve behavior.
Refactoring, prompt changes, schema changes, new features, dependency upgrades,
and authority expansion require later independent milestones.

## 9. Security boundaries

- Worker Lab remains the authority and lifecycle owner.
- The execution framework remains the only worker-process and sandbox owner.
- Model Bench remains evidence-producing and receives no production authority.
- Workers target separate disposable repositories, never this monorepo.
- Read-only and workspace-write remain explicit distinct modes.
- Credential stripping, process custody, path containment, bounded output, and
  fail-closed behavior must survive migration unchanged.

### 9.1 Standalone-to-monorepo identity migration

The current Worker Lab/framework bridge cannot execute unchanged in a monorepo:

- Worker Lab pins `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`,
  framework commit `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`, and
  `tools/worker_lab_adapter.py` at that standalone commit.
- Worker Lab also treats its own standalone repository HEAD/status as runtime
  identity.
- The framework adapter derives a standalone root from its file path, checks the
  whole Git status, and reads `tools/worker_lab_adapter.py` from repository root.

Imports may preserve these values temporarily for parity tests, but all real
adapter modes remain disabled. Re-enabling even a read-only proposal requires a
separately reviewed contract that:

1. distinguishes monorepo commit identity from imported source identity;
2. binds exact component-relative roots and adapter blob paths;
3. proves component-scoped tracked and untracked cleanliness without ignoring
   changes elsewhere that affect the invocation;
4. preserves adapter, Python, Codex launcher, protocol, prompt, and runtime
   digests;
5. keeps the target as a separate external Git repository; and
6. adds substitution, dirty-sibling, prefix-confusion, and stale-provenance
   regression tests before execution authority changes.

Path repair is not authority to redesign or weaken these checks.

## 10. Environments and dependency boundary

- No root virtual environment or combined dependency lock is introduced during
  component import.
- Worker Lab retains Python 3.12 and its package/CLI contract.
- Local Model Bench retains Python 3.10+ and its package/CLI contract.
- The framework remains a tools-style component until a separate packaging
  proposal is reviewed.
- Commands run from the applicable component root. Root orchestration may be
  added only after all original parity commands pass.

## 11. Validation

Each component import requires:

1. source identity and clean/importable-content decision;
2. provenance record;
3. focused tests;
4. original milestone suite or justified equivalent;
5. `git diff --check`;
6. path-reference audit;
7. independent review before the next component begins.

The final integration milestone also requires cross-component contract tests and
a recovery drill from the pre-migration source identities. Candidate parity
commands are recorded in `SOURCE_INVENTORY.md`. Historical pass counts are
evidence, not a substitute for fresh import validation.

## 12. Stop conditions

Stop before import or progression on:

- dirty or unreadable source material that affects the intended snapshot;
- unexplained documentation/Git identity conflict;
- missing license or provenance decision;
- test regression;
- security-boundary weakening;
- unrecorded path changes;
- accidental public or credential-bearing content.

## 13. License and distribution

- Preserve `components/local-model-bench/LICENSE` and its MIT notices.
- Worker Lab and the framework have no license files. The user's explicit merger
  direction authorizes private internal consolidation, not public relicensing or
  redistribution.
- Keep the combined repository private. Any visibility change or third-party
  distribution requires an explicit ownership/license review.

## 14. Rollback

Every milestone is a separate commit and review gate. Rollback means returning
the new repository to the preceding milestone; it never rewrites or deletes a
source repository. The originals remain the recovery basis until final transfer.
