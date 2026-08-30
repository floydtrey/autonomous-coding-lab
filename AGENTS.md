# Autonomous Coding Lab instructions

Read `docs/START_HERE.md` before acting.

During migration:

- Treat every source repository as read-only unless the user explicitly
  authorizes a source-side change.
- Never copy untracked, ignored, temporary, credential, runtime, backup, or
  generated-result material without an explicit inventory decision.
- Record every source commit and every old-to-new path in the migration records.
- Import one component at a time and prove test parity before restructuring it.
- Do not combine migration, refactoring, and behavior changes in one milestone.
- Preserve Worker Lab authority rules and execution-framework security boundaries
  even when they live in one Git repository.
- A worker target must remain a separate disposable Git repository; workers may
  not target this controlling repository.
- Stop on dirty source state, stale documentation, identity conflict, or an
  unexplained test difference.
