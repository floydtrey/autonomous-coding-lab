# RT-003: Diagnose a stale live-run summary

## Assignment

Diagnose the supplied evidence using the archived repository. Do not modify code,
tests, results, or documentation. Produce an evidence-backed diagnostic report.

Requirements:

- R1 Explain why `checkpoint.json`, raw case files, `evaluation.md`, and
  `summary.csv` can report different completed-case counts during this run.
- R2 Identify which artifacts are authoritative for live progress and which are
  derived snapshots.
- R3 Determine whether the discrepancy proves raw-result corruption or lost
  model work.
- R4 Trace the relevant write lifecycle and resume behavior to specific
  functions or call sites.
- R5 State whether running `evaluate` during an active run can stop or slow model
  execution, distinguishing file contention from inference work.
- R6 Recommend the smallest safe remediation or documentation change, but do not
  implement it.
- R7 List checks an operator should perform before trusting a final comparison.

## Authorized actions

Read repository files and the supplied evidence. You may run read-only searches
and existing tests. Do not start a model, resume a run, edit files, or regenerate
reports.

## Required response

Return a concise report with: finding, evidence, artifact authority, impact,
recommended action, and confidence/remaining uncertainty.
