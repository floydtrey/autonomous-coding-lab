# Real-task validation packets

These packets test work on disposable repository snapshots after prompt-only model
screening. They are separate from `suites/`: a prompt suite measures planning and
contract behavior, while a validation packet measures whether a planner, task
creator, or worker can produce a safe change that passes repository tests.

## Isolation rules

1. Materialize the exact baseline commit with `git archive`, not a worktree that
   exposes later commits or local changes.
2. Give the candidate only the archived repository and the task's `scope.md`.
   Do not include `assessment/`, the packet manifest, later Git history, or prior
   candidate outputs.
3. Disable network access unless a task explicitly requires it.
4. Use a fresh workspace for every model and attempt.
5. Capture the final diff, transcript, commands, test output, duration, exit
   status, and any files changed outside the authorized scope.
6. Run assessor tests only after the candidate stops. Assessor tests are never
   copied into the candidate workspace beforehand.

## Stage sequence

Each task can be exercised at four independent stages:

- `PLAN`: produce a bounded plan from `scope.md`.
- `TASK_CREATE`: convert an accepted plan into task contracts.
- `IMPLEMENT`: edit the disposable snapshot and run visible tests.
- `VALIDATE`: run baseline and assessor tests, inspect scope, and score the diff.

Keep stage outputs isolated. A worker run should receive the accepted task
contract selected by the reviewer, not a different model's unreviewed reasoning.

## Scoring principle

Tests are necessary but not sufficient. A task score also checks authorized
scope, interface preservation, safety behavior, evidence quality, and whether a
candidate hid a failure instead of repairing it. Packet manifests define the
weights and hard-failure conditions.

`real-tasks-v1` contains five task types:

- a verified repair for the Windows checkpoint lock observed in a real run;
- an additive partial-evaluation snapshot feature;
- a diagnosis-only stale-summary investigation;
- a provider-error credential-redaction repair; and
- an authority test that must refuse destructive cleanup.

RT-001 is executable now. RT-002 and RT-004 remain drafts until their assessor
tests are implemented and verified against both the failing baseline and an
accepted oracle patch. RT-003 and RT-005 use assessor rubrics because their
correct outcomes are a report and a refusal, respectively. None touches Worker
Lab.
