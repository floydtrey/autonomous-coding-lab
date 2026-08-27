# Autonomous Worker Framework

Local-first infrastructure for giving a ChatGPT-managed Codex worker a bounded software task, validating the exact result, and presenting a candidate for controlled integration.

The framework is separate from every repository it operates on. Mine Tracker is the first consumer and integration reference; it is not framework source.

## Start here

Read these documents in order when starting or resuming development:

1. [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — exact checkpoint, proven capabilities, open boundary, and next step.
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system map, trust boundaries, and data flow.
3. [`docs/WORKING_AGREEMENTS.md`](docs/WORKING_AGREEMENTS.md) — roles, development loop, review rules, and maintenance expectations.
4. [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisions that must not be silently revisited.
5. [`docs/PROVING_PROGRAM.md`](docs/PROVING_PROGRAM.md) — disposable-app curriculum and Mine Tracker graduation gates.

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

The current framework suite contains 117 tests. See `docs/CURRENT_STATE.md` for the last certified checkpoint rather than assuming the working tree is current.
