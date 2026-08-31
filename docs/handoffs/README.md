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
| H01 | Worker Lab and framework boundary | Accepted canonical witness | `H01-Handoff.txt` |
| H03 | Local Model Benchmark and merger foundation | Prepared | `H03-LOCAL-MODEL-BENCHMARK-AND-MERGER-FOUNDATION.md` |

The excluded `H01-Handoff.md` duplicate differed from the user-supplied `.txt`
only by a missing first-line Markdown heading marker. The user accepted the
unchanged `.txt` as canonical on 2026-08-30; the malformed duplicate was removed
instead of being indexed as a second handoff.

The current cross-handoff reconciliation is
`CONSOLIDATION_RECONCILIATION.md`. Its D-01 through D-06 decisions were accepted
by the user on 2026-08-30.

Add incoming reports to this index only after their content has been preserved
exactly. Normalization and conflict resolution happen in a separate document.
