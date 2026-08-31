# Source Inventory

**Status:** M1 inventory accepted; component imports require separate milestone authorization
**Observed:** 2026-08-30

Git-tracked snapshots are the only automatic import inputs. Working-tree,
ignored, unreadable, generated, runtime, and machine-local material is excluded
unless this document explicitly selects it later.

## Summary

| Component | Exact observed HEAD | Tracked scope | Distribution | Principal review gate |
|---|---|---:|---|---|
| Worker Lab | `ca55e30ccbcbf2318d73b3ef8a65f66bb9e1e684` | 85 files / 768,850 bytes / 43 commits | No license file; private internal use only | Preserve nine local-only commits; resolve 17-deletion disposition; migrate standalone identities |
| Execution framework | `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd` | 38 files / 288,791 bytes / 33 commits | No license file; private internal use only | Exact import verified; untouched standalone parity requires separate authorization |
| Local Model Bench | `4a023c8230365c3098a6dff71fa9623cac059cdd` | 59 files / 252,116 bytes / 7 commits | MIT; preserve component license | Classify selected compact evidence; native run is complete but semantically unreviewed |

File and byte counts are the exact `HEAD` trees, not filesystem counts.

## Worker Lab

### Identity

- Source: `C:\Users\MineTrackerWorker\repos\worker-lab`
- Branch: `main`
- Remote: private `https://github.com/floydtrey/worker-lab.git`
- Remote relation: `main` is nine commits ahead of `origin/main`
- Observed HEAD: `ca55e30ccbcbf2318d73b3ef8a65f66bb9e1e684`
- Observed tree: `cf7fb964aa25aabb076292865f2367f0cecb4c04`
- Tags: `v0.1.0-phase1`, `v0.1.1-phase1`, `v0.1.2-phase1`,
  `v0.2.0-phase2`
- Package: `worker-lab` (`worker_lab` import), Python 3.12+, CLI
  `worker-lab = worker_lab.cli:main`
- Layout: 23 root files, 8 curriculum files, 12 active docs, 20 test
  files, and 22 package files

### Authority and interface

Worker Lab owns curricula, attempt lifecycle, policy, evidence, evaluation,
workspace receipts, process custody, failure records, and operator commands. It
does not own Codex authentication, sandbox enforcement, credential handling, or
worker-process execution.

The framework boundary is a fixed canonical-JSON subprocess protocol, not a
Python import. The active source pins:

- standalone framework path
  `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`;
- framework commit `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`;
- adapter path `tools/worker_lab_adapter.py` and its exact digest;
- CPython 3.12.10 executable path/digest; and
- Codex CLI 0.149.1 plus the `terra-medium:v1` runtime profile.

It also identifies Worker Lab by standalone Git HEAD and status. Both identity
models require a reviewed monorepo replacement before execution.

### Working-tree classification

- Exactly 17 tracked historical/task-report files are deleted in the working
  tree. Each name has a blob-equivalent copy under the separate
  `Legacy/worker-lab-history` location. These working-tree deletions are not part
  of the selected HEAD tree and must not be committed, imported as deletions, or
  restored automatically during M1.
- `Legacy/worker-lab-history` contains one additional
  `8_27_26_ChatGPT_History` file. It is historical conversation material and is
  excluded from import.
- `.phase3c-test-temp*` directories are unreadable test residue. They are not
  tracked and are excluded without cleaning or inspection.
- `.venv/`, caches, `state/`, `evidence/`, `workspace/`, and temporary files are
  ignored runtime/generated categories and are excluded.
- Numerous tracked `TERRA*.md` files are historical task and handoff evidence.
  Preserve them on full-history import, but do not treat their old absolute
  paths or stopped authority as current instructions.

### Validation candidate

Run from `components/worker-lab/` with the component's Python 3.12 environment:

```powershell
python -m pytest -q
```

The source records 257 passed with six expected Windows symlink-capability skips
at the Phase 2 milestone, followed by an 87-passed/two-skipped focused Phase 3C
checkpoint. A fresh complete suite on the imported snapshot is required; these
historical counts do not set the expected current total.

### Import gate

The exact local-ahead HEAD ancestry/tree and separate historical disposition of
the 17 moved/deleted working-tree files are accepted for a future, separately
authorized M3 import. Complete the monorepo identity implementation before that
import. The current deletion state cannot silently change import content: the
accepted exact HEAD tree includes those files. Legacy/chat history, ignored
residue, and unreadable directories remain excluded.

## Autonomous Worker Framework

### Identity

- Source: `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`
- Branch: local `main`, no upstream and no remote
- Observed HEAD: `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`
- Observed tree: `35ecad05e60c664324a4f30d42a4f6b198181074`
- Latest tag: `v0.2.6-worker-lab-final-message`
- Other relevant tags: `v0.1.0-foundation` and
  `v0.2.0-worker-lab-adapter` through `v0.2.5-worker-lab-verified-launcher`
- Package: none; root-relative Python tools and tests
- Layout: 4 root files, 9 docs, 13 test files, and 12 tool files

### Authority and interface

The framework owns Codex authentication, API-key rejection, credential
sanitization, sandbox selection, subprocess execution, target-repository
separation, bounded output, validation, and handoff evidence.

Its adapter derives the framework root as the parent of `tools/`, requires that
root's full Git status to be clean, binds the repository HEAD to the Worker Lab
invocation, and reads `tools/worker_lab_adapter.py` from that commit. Prefixing
the tree changes the repository root and blob path even when adapter bytes remain
identical. This is a security-contract migration, not a routine path correction.

`tools/local_validate.py quick` also assumes Git reports paths relative to the
component root. In a monorepo Git reports prefixed paths, so its changed-file
selection needs a prefix-aware repair after the untouched full parity run.

### Working-tree classification

- `.phase3c-test-temp*`, `.pytest-terra-phase3c/`, caches, and bytecode are
  unreadable or ignored test residue. They are excluded without cleaning.
- No untracked source intended for import was identified.
- The repository has no current remote. Complete ancestry will be fetched from
  the exact local object database during M2.

### Validation candidate

Run from `components/autonomous-worker-framework/`:

```powershell
python tools\local_validate.py full
```

The source records 158 passing tests at the adapter milestone. Fresh import
validation must pass before any prefix-aware validator or identity change.

### Import gate

The current no-remote source, all refs, complete reachable ancestry, and external
recovery bundle passed M2-A. M2-B exact import commit
`d1c95814bce512318c61a5745dcd684d87e3676a` preserves the source tip as its
second parent and the accepted source tree unchanged under
`components/autonomous-worker-framework/`. Exact identities, checksum, recovery
drill, namespaced tags, import procedure, and proof are recorded in
`FRAMEWORK_M2_RECOVERY.md`.

Adapter execution remains disabled. Untouched parity from a disposable
standalone reconstruction requires separate authorization. Later in-monorepo
prefix testing and adaptation remain separate gates. M2 may not silently
authorize the new identity contract.

## Local Model Bench

### Identity

- Source:
  `C:\Users\MineTrackerWorker\repos\awf-live-consumer-smoke\2026-08-29\referenced-chatgpt-conversation-this-is-an\outputs\local-model-bench`
- Branch: `main`, synchronized with `origin/main`
- Public remote: `https://github.com/floydtrey/local-model-bench.git`
- Observed HEAD: `4a023c8230365c3098a6dff71fa9623cac059cdd`
- Observed tree: `1b20a0e6a9e273532ed047ff3cb9f8c990f6fa01`
- Tags: none
- Package: `local-model-bench` (`localbench` under `src/`), Python 3.10+,
  CLI `local-model-bench = localbench.cli:main`
- License: MIT at source root
- Layout: 4 root files, 5 configs, 4 experiment files, 4 selected result
  reports, 4 schemas, 7 scripts, 10 package files, 4 suites, 1 test file, and
  16 validation-packet files

### Authority and interface

Local Model Bench evaluates models, prompts, context handling, structured output,
timing, errors, resumability, and deterministic scoring. It produces evidence
but does not grant worker, planner, execution, publication, or merge authority.
No Python imports between it and the other two components were identified.

PowerShell entry scripts derive their project root from `PSScriptRoot`; they
should survive prefixing when run from the component root. Config and suite paths
are resolved relative to the selected config. Two tracked configs contain
machine-local llama.cpp and GGUF paths under `C:\MineTrackerAI`; preserve them for
provenance on import, then address portability as a separate configuration task.

### Working-tree classification

- `.venv/`, logs, PID files, caches, validation workspaces, and most complete
  benchmark result trees are ignored/excluded.
- Selected review reports from one completed smoke run are already tracked and
  belong to the import snapshot.
- `results/background-20260830T033057-9d425311/` is the completed ignored Qwen
  14B native-JSON retest: 18/18 transport successes, 93.33% mechanical score,
  zero hard failures, and bare parseable JSON. It remains local raw evidence and
  must not be copied merely because M4 begins. Select only reviewed durable
  reports; semantic role fitness remains unknown.
- Model files and Ollama/llama.cpp installations remain outside the repository.

### Validation candidate

Run from `components/local-model-bench/` after component bootstrap:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m localbench validate --config .\configs\ollama-16gb.json
```

The unit suite does not contact models. Configuration validation also remains
separate from the optional endpoint/model availability check.

### Import gate

Decide which derived reports are durable, complete semantic review separately,
and preserve the MIT license. The completed native run is not an M2 blocker and
does not authorize model selection. Do not import complete local run data, logs,
model binaries, or machine installations.

## Cross-component conclusions

- Keep three component roots and three validation contexts through M6.
- Import order is framework, Worker Lab, then benchmark because Worker Lab
  depends on the framework contract and the benchmark grants no authority.
- Original source commits remain provenance identities after import; monorepo
  commits become integration identities. Neither substitutes for the other.
- Existing standalone absolute paths in historical docs are evidence. Active
  code/config path assumptions are ledgered and repaired only in their assigned
  milestone.
- The old repositories remain unchanged recovery sources throughout the merger.
- Worker Lab owns accepted plans, permanent task/test identities, routing policy,
  lifecycle, and evidence acceptance. Framework contracts transport and execute
  exact authorized tasks. Benchmark schemas and IDs remain experimental.
- Preserve native evidence schemas through M4. Directional adapters may create
  candidate evidence or recommendations without upgrading authority. A minimal
  typed evidence reference is deferred to M5 unless integration tests establish
  an earlier need.
