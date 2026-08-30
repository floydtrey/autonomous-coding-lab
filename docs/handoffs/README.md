# Consolidation Handoffs

Handoffs are witness reports from source conversations. They preserve local
context efficiently, but they are never authority by themselves. The
consolidation task must verify important claims against Git, files, tests, and
the active merger contract.

## Rules

- Use `HANDOFF_REQUEST.md` unchanged except for the handoff ID and source label.
- One source conversation produces one uniquely numbered Markdown document.
- Do not let a source conversation merge, refactor, commit, push, clean, delete,
  or resolve cross-project conflicts while preparing its report.
- Preserve contradictions between reports. Reconciliation belongs to the
  consolidation task.
- Never include credentials, token values, unrestricted environment dumps,
  private operational data, model binaries, or large raw logs.
- A running test is recorded as running with an observation time. It is not
  represented as passed, failed, or blocking handoff preparation.

## Index

| ID | Area | Status | File |
|---|---|---|---|
| H03 | Local Model Benchmark and merger foundation | Prepared | `H03-LOCAL-MODEL-BENCHMARK-AND-MERGER-FOUNDATION.md` |

Add incoming reports to this index only after their content has been preserved
exactly. Normalization and conflict resolution happen in a separate document.

