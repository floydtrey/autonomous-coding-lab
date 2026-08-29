# Terra Phase 3C Framework Report

The framework candidate began clean on `main` at
`135373d24837f5d5b0da0650c9c00fc086fcb991`; Worker Lab began at trusted handoff checkpoint
`3c5a7e343c7c23046b1ec3bb369d8e03ec9bc4f8`. The framework routing/current-state documents were
stale for this handoff; the tracked Worker Lab handoff explicitly superseded that statement for this
non-executing implementation only.

Added `tools/worker_lab_adapter.py` and `tests/test_worker_lab_adapter.py`. The adapter accepts a
bounded canonical JSON read-only request, rejects workspace-write mode, requires an injected fake
executor, verifies prompt identity, bounds stdout/stderr, and rejects sensitive/absolute-path output.
Its command-line entry point leaves preflight and execution disabled, so it does not call Codex,
check authentication, or run a live worker. Focused adapter/runtime validation passed: `25 passed`.

The Worker Lab companion now supplies the reviewed-candidate process runner, custody recovery, and
identity client. No framework milestone or live Worker Lab invocation is claimed; both repository
candidates remain uncommitted and await trusted review.

## VS Code Correction Handoff

The correction handoff treated this inherited dirty framework candidate as untrusted and preserved
it in place. It reread the framework adapter/runtime surfaces and confirmed that all framework
execution remains fake-only: the CLI leaves preflight and `execute-read-only` disabled, and tests
use injected checkers/executors. Final correction validation compiled
`tools/worker_lab_adapter.py` and `tools/codex_runtime.py`, then ran
`tests/test_worker_lab_adapter.py tests/test_codex_runtime.py`: `37 passed in 0.21s`.

No framework full suite, Codex command, launcher/authentication probe, real adapter request,
milestone, commit, tag, push, PR, remote, or product action ran. The framework candidate remains
uncommitted and is ready for Sol review only.

## Codex continuation after VS Code Terra limit

VS Code Terra reached its usage limit while beginning the bounded-runtime reader-failure correction.
With explicit user direction, Codex completed that same fake-only correction: `execute_codex_bounded`
now makes stdout/stderr reader exceptions authoritative, terminates the fake process, and rejects
partial output. It adds a bounded reader-join timeout solely for deterministic fake-process tests.

The adapter now rejects duplicate-key, noncanonical, and non-finite JSON requests, and its injected
launcher-version reader is covered without calling a real launcher. Framework focused tests compiled
changed Python and ran `tests/test_worker_lab_adapter.py tests/test_codex_runtime.py`: `44 passed`.
Pytest emitted only its cache-directory permission warning; `git diff --check` was clean. No live
Codex/authentication/adapter operation occurred. The framework candidate remains non-executing and
uncommitted pending the final Sol diff review.

## Sol high-review correction completion

The framework request validator now independently enforces the missing identifier, positive-version,
catalog-version, and exact sorted test-ID scalar/list types instead of validating only the outer
field set. New fake-only cases reject booleans, zero or textual versions, malformed identifiers,
malformed test IDs, and duplicate test IDs. The final framework adapter/runtime slice passed
`53 passed`; changed Python compiled and `git diff --check` remained clean. Execution and live
authentication remained disabled and were not invoked.

## Trusted framework milestone

The complete framework suite passed `158 tests`. The reviewed adapter/runtime candidate was committed
at `2d8c93312103015125f0eef9e2afdc697a45d244` and annotated as
`v0.2.0-worker-lab-adapter`. The framework working tree was clean after the commit and tag, no remote
is configured, and `v0.1.0-foundation` remains unchanged. Worker Lab pins the exact adapter blob
digest `sha256:4014b58bb47689ad0dbb9e13b01a61a60012793c611d371765a2a87975f8d117`.
