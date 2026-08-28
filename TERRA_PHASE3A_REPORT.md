# Terra Phase 3A Report

## Trial metadata

- Work type: documentation-only Phase 3 interface specification.
- Reasoning level: medium.
- Worker Lab repository: `C:\Users\MineTrackerWorker\repos\worker-lab`.
- Branch: `phase3/framework-interface-spec-v1`.
- Starting HEAD containing the final handoff authority:
  `99836e09502e1b6df421891bfb39382f74636876`.
- Trusted base milestone `v0.2.0-phase2` was verified as ancestral.
- Framework read-only authority checkpoint:
  `135373d24837f5d5b0da0650c9c00fc086fcb991` on clean local `main`.
- Framework foundation tag `v0.1.0-foundation` was verified as ancestral.

At the specification start, the only untracked pre-existing user file was
`docs/8_27_26_ChatGPT_History`. The handoff also permitted `Worker-Lab_8_28_26.zip`, but it was no
longer present. Neither file was opened, modified, staged, moved, or deleted during this work.

## Context consulted

Worker Lab:

- `TERRA_PHASE3A.md`
- `docs/START_HERE.md`
- `docs/CURRENT_STATE.md`
- `docs/PHASE2_SPEC.md`
- `docs/POLICY_MODEL.md`
- `docs/TEST_CATALOG.md`
- relevant public records and transitions in `worker_lab/models.py`, `worker_lab/lifecycle.py`,
  `worker_lab/workspace.py`, and `worker_lab/test_catalog.py`
- machine-readable profiles in `curricula/catalogs/worker-lab-v2.json`

Framework, read-only:

- `AGENTS.md`
- `docs/START_HERE.md`
- `docs/CURRENT_STATE.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/WORKER_LAB_DESIGN.md`
- `docs/TESTING_AND_AUTHORITY.md`
- public contracts in `tools/codex_runtime.py`, `tools/consumer_profile.py`,
  `tools/context_probe.py`, `tools/code_task.py`, `tools/task_contract.py`, and
  `tools/worker_result.py`

Historical reports, ZIPs, chat exports, backups, product repositories, framework tests, and unrelated
implementation files were not read.

## Files changed

- Added `docs/PHASE3_SPEC.md`.
- Added `docs/PHASE3_READINESS_REVIEW.md`.
- Added this `TERRA_PHASE3A_REPORT.md`.
- Updated only the Phase 3 candidate status and next boundary in `docs/CURRENT_STATE.md`.

No production Python, test, schema, curriculum, policy, role, catalog, prior phase contract, README,
or START_HERE file changed.

## Principal design decisions

1. Selected one fixed framework-owned local process adapter using canonical JSON stdin/stdout.
2. Rejected direct cross-repository imports and network/general orchestration layers.
3. Kept Worker Lab as attempt/lifecycle/test/evidence authority and the framework as
   auth/credential/sandbox/runtime/subprocess authority.
4. Defined strict invocation and result identities instead of reusing consumer-specific or
   commissioning contracts unchanged.
5. Required deterministic non-executing preparation before authorization.
6. Chose `READY -> RUNNING` before process creation, with durable `DISPATCHING` custody and
   conservative uncertain-outcome handling.
7. Required read-only proposal proof before any workspace-write task.
8. Reserved `FAILED` for evaluation and used `ABORTED` for contained execution failures.
9. Required immutable `worker-lab-v3` profiles, including T016/T022, rather than a second YAML test
   matrix.
10. Kept shared test-helper cleanup, workspace modularization, and CLI cleanup outside the integration
    batches.

## Contract gaps found

- The current context probe defaults to a consumer-specific profile and its result cannot prove the
  complete Worker Lab non-mutation or invocation boundary.
- The general code-task result lacks strict failure/process evidence and candidate content identity.
- The commissioning task is intentionally fixture-specific.
- `worker-result:v1` is useful structure but lacks invocation/receipt identity and permits repair or
  repository-handoff semantics excluded from initial Phase 3.
- The current framework does not provide durable process identity sufficient for safe restart cleanup;
  Batch 3C must not begin until the trusted controller approves and tests that control.

## Reserved decisions

The readiness review reserves the exact adapter executable boundary, initial runtime profile,
Windows process containment/absence proof, prompt/output limits and redaction, runtime-identity
transition behavior, `worker-lab-v3` commands, and whether the framework adapter receives a new
milestone before execution. The candidate recommends approving only non-executing Batch 3B after
trusted review.

## Commands and validation

- Verified Worker Lab branch, HEAD, milestone ancestry, and status with non-mutating Git commands.
- Verified framework branch, HEAD, foundation ancestry, and clean status with non-mutating Git
  commands.
- Inspected only the routed documents and public source contracts listed above.
- Corrected the handoff's nonexistent `worker_lab/test_planner.py` path to the actual
  `worker_lab/test_catalog.py` before the clean specification checkpoint.
- Ran `git diff --check` once after the final documentation edit; it passed with no output.
- Verified the changed-path set is limited to the three required deliverables and the permitted
  `docs/CURRENT_STATE.md` update.

No pytest, compilation, runtime profile, Codex command, worker, framework adapter, attempt creation,
lifecycle transition, backup, bundle, branch creation, remote, GitHub, commit, push, merge, tag,
installation, credential access, or external product action occurred during specification drafting.

## Recommendation

Send `docs/PHASE3_SPEC.md` and `docs/PHASE3_READINESS_REVIEW.md` for trusted high-reasoning review.
If the reserved decisions are accepted or narrowed, authorize Batch 3B only. Continue to prohibit
worker execution until a separate Batch 3C approval.
