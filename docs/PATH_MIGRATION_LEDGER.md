# Path Migration Ledger

No paths have moved yet. Destination roots are M1 candidates and stay unchanged
through M6 once accepted.

| ID | Source | Destination | Known references or behavior | Validation | Milestone | Status |
|---|---|---|---|---|---|---|
| P-001 | Worker Lab repository root | `components/worker-lab/` | Package/test relative paths survive; Git HEAD/status and source-root identity do not | Complete Worker Lab suite | M3 | Proposed |
| P-002 | Framework repository root | `components/autonomous-worker-framework/` | Adapter Git root/blob lookup and quick validator path discovery require design/repair | Framework full suite, then focused prefix tests | M2 | Proposed |
| P-003 | Local Model Bench repository root | `components/local-model-bench/` | `PSScriptRoot`, config-relative suites/results, editable install, and `.venv` stay component-local | Unit suite and config validation | M4 | Proposed |
| P-004 | Worker Lab framework pin `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework` | Monorepo component locator | Must not become a loose relative path; bind canonical monorepo root plus exact component prefix | Identity/substitution regression suite | M3 | Design required |
| P-005 | Framework blob `tools/worker_lab_adapter.py` at standalone commit | `components/autonomous-worker-framework/tools/worker_lab_adapter.py` at monorepo commit plus imported-source identity | Preserve exact byte digest and protocol identity | Adapter preflight and stale-provenance tests | M2/M3 | Design required |
| P-006 | Worker Lab standalone Git HEAD/status | Monorepo commit plus Worker Lab component tree/status identity | Must detect dirty Worker Lab bytes and relevant dependency drift without treating unrelated evidence output as source | Dirty-sibling, component-drift, and prefix-confusion tests | M3 | Design required |
| P-007 | Framework standalone full Git cleanliness | Component-scoped framework cleanliness plus invocation dependency set | Scope must remain fail-closed and include all files that affect execution | Security boundary review | M2/M3 | Design required |
| P-008 | Framework quick validation root-relative Git paths | Prefix-normalized paths under framework component | Do not alter full-suite behavior during import | Synthetic changed-file selection tests | M2 | Repair after parity |
| P-009 | Benchmark `C:\MineTrackerAI\...` paths in two tracked configs | Local configuration mechanism, exact destination undecided | Preserve tracked originals on import; no model binary enters Git | Config parser/unit tests and secret/path review | M4 or later | Deferred configuration change |

## Entry completion requirements

Before an entry becomes accepted, record:

- exact old and new path;
- source commit and monorepo commit;
- every active code, configuration, test, and documentation reference changed;
- focused and full validation evidence;
- security review for identity or authority paths; and
- rollback identity.

Historical documentation paths are normally retained verbatim as provenance and
marked historical by routing documents. They are not mechanically rewritten.
