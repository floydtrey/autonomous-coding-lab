# Autonomous Worker Framework

Local-first infrastructure for giving a ChatGPT-managed Codex worker a bounded software task, validating the exact result, and presenting a candidate for controlled integration.

The framework is separate from every repository it operates on. Mine Tracker is the first consumer and integration reference; it is not framework source.

## Start here

Start with the routing index. It will identify the minimum documents needed for the current task:

1. [`docs/START_HERE.md`](docs/START_HERE.md) — authority order and task-specific reading routes.
2. [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — exact checkpoint, proven capabilities, open boundary, and next step.

Do not read every design/history document by default. This reduces stale-context drift.

## Non-negotiable boundaries

- Codex uses ChatGPT-managed authentication only.
- `OPENAI_API_KEY` or `CODEX_API_KEY` causes worker execution to fail closed.
- GitHub credential-like environment variables are removed from Codex subprocesses.
- Worker sandboxes are explicitly `read-only` or `workspace-write`; danger/full-access modes are forbidden.
- A worker operates on a separate target repository and isolated worktree.
- Every task binds repository head, context, writable paths, acceptance criteria, and trusted validation into deterministic evidence.
- The first failed boundary stops the run.
- Workers do not commit, push, merge, alter Git configuration, or establish production authority.
- Publication and merge are separate trusted-controller actions against an exact verified commit.

## Local validation

Routine loop:

```powershell
python tools\local_validate.py quick
```

Milestone gate:

```powershell
python tools\local_validate.py full
```

The current framework suite contains 120 tests. See `docs/CURRENT_STATE.md` for the last certified checkpoint rather than assuming the working tree is current.
