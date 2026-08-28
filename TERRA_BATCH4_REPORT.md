# Terra Batch 4A Report

## Trial metadata

- Model: GitHub Copilot (handoff target: GPT-5.6 Terra).
- Reasoning effort: medium.
- Starting branch: `phase2/batch4-acceptance-v1`.
- Starting HEAD: `462e29cc1ffb70615af84c172ad2ba0588ac36c6`.

## Context consulted

- `docs/START_HERE.md`
- Phase 2 status and next-boundary section of `docs/CURRENT_STATE.md`
- Backup, operator-interface, test-selection, delivery-batch, and exclusion sections of `docs/PHASE2_SPEC.md`
- P2-C11 and P2-C12 in `docs/PHASE2_READINESS_REVIEW.md`
- T010/T012/T020/T021 and milestone profile details in `docs/TEST_CATALOG.md`
- `README.md`
- `worker_lab/backup.py`
- `tests/test_backup.py`
- `tests/test_cli.py`
- `tests/test_workspace_receipt.py`

No unchanged consulted file was reread. The ZIP and chat export were not opened or modified.

## Starting state

The required branch and tracked `TERRA_BATCH4.md` handoff were present. The only pre-existing untracked files were `Worker-Lab_8_28_26.zip` and `docs/8_27_26_ChatGPT_History`.

## Changed files

- `tests/test_cli.py`
- `tests/test_backup.py`
- `README.md`
- `docs/CURRENT_STATE.md`
- `TERRA_BATCH4_REPORT.md`

No production Python, schema, catalog, policy, lifecycle, workspace, or backup implementation file changed.

## Added acceptance behavior

- A complete synthetic public CLI flow creates a `DRAFT` attempt, prepares it to `READY`, verifies it
	without writing the attempt or receipt, confirms the prepared Git workspace has no remote or alternate
	object store, discards it to `ABORTED`, and confirms repeat discard is idempotent with no receipt,
	workspace, or quarantine directory.
- A backup taken while an attempt is `READY` retains durable attempt and curriculum data while excluding
	the receipt and disposable workspace. Restore only publishes into an empty destination; the restored
	attempt remains `READY` but cannot verify or resume, and the existing guarded terminal transition
	records the exact `workspace not restored` cleanup outcome.

## Status

Batch 4A acceptance and documentation work completed. This is a validation candidate only; it does not
claim the external backup/rollback drill, selected review, merge, tag, or final bundle.

## Commands and outcomes

- `Get-Location; git branch --show-current; git rev-parse HEAD; git status --short; git ls-files --error-unmatch TERRA_BATCH4.md` - passed required starting checks.
- `python -m pytest tests/test_cli.py -k complete_phase2_workspace_cli_workflow tests/test_backup.py -k ready_workspace_backup_excludes_receipt_and_requires_terminal_recovery -q` - selection mistake: `1 passed, 25 deselected in 4.83s`; the two `-k` filters intersected, so only the backup test ran.
- `python -m pytest -q tests/test_cli.py::test_complete_phase2_workspace_cli_workflow tests/test_backup.py::test_ready_workspace_backup_excludes_receipt_and_requires_terminal_recovery` - `2 passed in 11.49s`.
- The same exact focused command after a test-only import cleanup - `2 passed in 7.17s`.
- `python -m py_compile tests/test_cli.py tests/test_backup.py` - passed with no output.
- `python -m pytest -q` - `257 passed, 6 skipped in 157.03s`. All six skips were Windows environments where directory symlink creation is unavailable.
- `git log --oneline -6` - confirmed Batch 3 was integrated by `0e01168`, `Merge pull request #3 from floydtrey/phase2/workspace-verification-disposal-v1`.

## Assumptions and limitations

- The existing Phase 2 same-path replacement limitation remains accepted; Batch 4A adds no persistence
	or identity mechanism to change it.
- The restored `READY` record is terminally resolved through the existing guarded `transition-attempt`
	path because the excluded receipt is absent; retry requires a new linked attempt.
- No production defect was exposed by the added acceptance tests or the full suite.

## Final repository checks

- `git diff --check` passed with no output.
- `git status --short` showed only the four allowed modified tracked files, this required untracked
	report, and the untouched pre-existing `Worker-Lab_8_28_26.zip` and
	`docs/8_27_26_ChatGPT_History` files.
- `git diff --stat` reported `README.md` (8 lines), `docs/CURRENT_STATE.md` (16 lines),
	`tests/test_backup.py` (50 insertions), and `tests/test_cli.py` (53 insertions): 117 insertions and
	10 deletions across four tracked files. The report is untracked and therefore not included in that
	diff stat.

## Prohibited actions

No production-code modification, remote or external-repository access, commit, push, tag, external backup mutation, worker/framework invocation, ZIP access, or chat-export access occurred.

## Batch 4B handoff

Perform trusted review and select the proposed commit/PR. Run the external durable-data backup and
independent rollback-clone drill, capture rollback-suite evidence, finalize documentation, merge the
selected change, create the approved tag, and produce the final evidence bundle. Do not treat this
Batch 4A candidate as evidence that any Batch 4B action has occurred.
