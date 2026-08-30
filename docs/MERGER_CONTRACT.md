# Merger Contract

**Version:** Draft 0.1
**Status:** M0 bootstrap; requires M1 audit update before code import

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
M0; the accepted M1 contract must record their exact replacement before import.

## 5. Import strategy

The provisional low-risk strategy is:

1. Import each source with history into a dedicated prefixed directory.
2. Preserve that source's internal relative layout during its first parity run.
3. Do not restructure and import in the same milestone.
4. After parity, propose any final directory move in the path ledger and repair
   references as a separately reviewed change.

Provisional landing paths:

| Source | Initial landing path | Possible later product path |
|---|---|---|
| Worker Lab | `components/worker-lab/` | `apps/worker_lab/` |
| Execution framework | `components/autonomous-worker-framework/` | `packages/execution_framework/` |
| Local Model Bench | `components/local-model-bench/` | `tools/model_bench/` |

The M1 review may retain the initial paths permanently if moving them provides
insufficient benefit.

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

## 10. Validation

Each component import requires:

1. source identity and clean/importable-content decision;
2. provenance record;
3. focused tests;
4. original milestone suite or justified equivalent;
5. `git diff --check`;
6. path-reference audit;
7. independent review before the next component begins.

The final integration milestone also requires cross-component contract tests and
a recovery drill from the pre-migration source identities.

## 11. Stop conditions

Stop before import or progression on:

- dirty or unreadable source material that affects the intended snapshot;
- unexplained documentation/Git identity conflict;
- missing license or provenance decision;
- test regression;
- security-boundary weakening;
- unrecorded path changes;
- accidental public or credential-bearing content.

## 12. Rollback

Every milestone is a separate commit and review gate. Rollback means returning
the new repository to the preceding milestone; it never rewrites or deletes a
source repository. The originals remain the recovery basis until final transfer.
