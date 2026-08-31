# Path Migration Ledger

No component paths have moved yet. Destination roots were accepted at M1 and
stay unchanged through M6.

| ID | Source | Destination | Known references or behavior | Validation | Milestone | Status |
|---|---|---|---|---|---|---|
| P-001 | Worker Lab repository root | `components/worker-lab/` | Package/test relative paths survive; Git HEAD/status and source-root identity do not | Complete Worker Lab suite | M3 | Accepted path; move pending |
| P-002 | Framework repository root | `components/autonomous-worker-framework/` | Adapter Git root/blob lookup and quick validator path discovery require design/repair | Framework full suite, then focused prefix tests | M2 | Accepted path; move pending |
| P-003 | Local Model Bench repository root | `components/local-model-bench/` | `PSScriptRoot`, config-relative suites/results, editable install, and `.venv` stay component-local | Unit suite and config validation | M4 | Accepted path; move pending |
| P-004 | Worker Lab framework pin `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework` | Versioned monorepo identity manifest plus canonical framework prefix | Bind monorepo root/commit/tree, source provenance, exact prefix/subtree and closed invocation dependency set; never use a loose relative path | Identity/substitution/prefix/escape regression suite | M2/M3 | Accepted boundary; implementation pending |
| P-005 | Framework blob `tools/worker_lab_adapter.py` at standalone commit | `components/autonomous-worker-framework/tools/worker_lab_adapter.py` at monorepo commit plus imported-source identity | Preserve source and integration identities separately; committed blob and worktree digest must match | Adapter preflight and stale-provenance tests | M2/M3 | Accepted boundary; implementation pending |
| P-006 | Worker Lab standalone Git HEAD/status | Monorepo commit/tree plus Worker Lab prefix/subtree/status and dependency-closure identity | Detect dirty Worker Lab bytes and relevant dependency drift without treating unrelated docs/benchmark output as executable source | Dirty-sibling, component-drift, dependency-drift and prefix-confusion tests | M3 | Accepted boundary; implementation pending |
| P-007 | Framework standalone full Git cleanliness | Both participating components plus closed root/shared invocation dependency set | Tracked/untracked, unreadable, undeclared executable/config, path escape, substitution and stale identity fail closed | Security boundary review and negative regression suite | M2/M3 | Accepted boundary; implementation pending |
| P-008 | Framework quick validation root-relative Git paths | Prefix-normalized paths under framework component | Do not alter full-suite behavior during import | Synthetic changed-file selection tests | M2 | Repair after parity |
| P-009 | Benchmark `C:\MineTrackerAI\...` paths in two tracked configs | Local configuration mechanism, exact destination undecided | Preserve tracked originals on import; no model binary enters Git | Config parser/unit tests and secret/path review | M4 or later | Deferred configuration change |
| P-010 | Pre-checkpoint untracked `docs/handoffs/H01-Handoff.txt` and one-character-different `.md` duplicate | Indexed canonical `docs/handoffs/H01-Handoff.txt` | The user-supplied `.txt` is canonical; the malformed `.md` duplicate is excluded after hash/no-index comparison; witness content is unchanged | Hash/no-index comparison and handoff-index audit | M1 | Accepted and resolved |

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
