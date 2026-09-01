# VS Code Handoff

Resume `main` from the accepted Phase 3 checkpoint `00b1769` in `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`.

Read `AGENTS.md`, `docs/START_HERE.md`, `docs/CURRENT_STATE.md`, and `docs/WORKPLAN.md`; treat the work plan as the trusted sequence. Inspect the dirty tree before editing and preserve unrelated changes.

Phase 3 is complete. `dispatch-invocation` gates every durable transition, custody record, adapter path, and evaluator on `require_execution_enabled`; it binds exact authorization, controller, attempt, workspace, prompt, runtime, custody, result, and candidate evidence. The accepted Phase 4 implementation bridge checkpoint is `8862880`.

The accepted working tree implements Phase 4’s workspace-write bridge without executing it. `worker-lab-framework-adapter:v2` remains read-only; v3 is a separately versioned workspace-write contract. The framework rebuilds the consumer profile/context packet and reuses `code_task`, candidate-content, and repository-handoff validation. Worker Lab routes write dispatch through the existing gate-first lifecycle/Windows Job custody boundary and accepts only exact changed paths, unchanged HEAD, clean diff, sealed tests, absence proof, and a retained candidate manifest.

Current-tree validation: framework protocol/code-task tests **63 passed** and framework compile/full validation **213 passed**; Worker Lab service/client/integration tests **70 passed** and the Worker Lab full suite **369 passed** with seven expected Windows symlink-capability skips. Manifest identities: framework `sha256:b9c1061422b0cb28e94086f070ddf8fe4bf4c7a744b7e8589af2dca2b87de1f8`, Worker Lab `sha256:7ec7255a1853b21ed4888846b0063565d2898505ab6535e07f174d4809a4fd99`; execution is still disabled. No adapter, worker, Codex/local model, or external/product repository ran. This does **not** prove or complete Phase 4.

Before any real workspace-write run, obtain explicit authorization for one disposable non-product repository, exact starting commit and readable/writable scope, one named task/test plan, controller, temporary policy activation, post-run absence/candidate review, and immediate return to disabled. It must separately prohibit commit, push, PR, merge, and external/product-repository access.

The active protected packet now admits `phase4-record-normalizer-v1`: curriculum digest `sha256:f0be43ca9c0b83785fe3cc5e00c62e5bc1e57d7f2ba2554ae90613f6641fe1ed`, exercise `sha256:d81836446a8dfaa8eca2fc0025567c969e97e5b30de97a35a39ce504bfac67fa`, context `sha256:e677c8ec088857e89c916a5cb7eb7c5f7447a6097eb571cc48cc81dc2fd29416`, and catalog `sha256:8c5ee8dd7913e14556582ed3b6e9f989721c97c81e9573845dda1f10c8cf9f76`. It binds the exact disposable repository/commit above, writable `record_ledger/models.py`, sealed `tests/test_models.py` digest `sha256:3a2f0faa16488f02fbfccdc0bf78ac43d7cd1e5446969627c2e19cc0817dcbd3`, controller `ACL-primary-controller` for a future separate authorization, and exactly `git diff --check` followed by `python -B -m unittest discover -s tests -p test_models.py -v`. Protected-definition tests passed 6 and the Worker Lab suite passed 373 with seven expected symlink skips; no worker/model/adapter execution or target test command ran.

Preparation was attempted with execution disabled. The exact target passed clean/commit/context admission, then isolated-workspace preparation failed closed with `CONTEXT_DIGEST_MISMATCH` for `tests/test_models.py`. Its transient draft was `ATTEMPT-2A566F345A774ADC892FDD1A39FA1A76` (`sha256:49bbb08a9a6b29b536c84a283bc9f73b88e9b2dfe0da1532cd40efd4cb97e1cc`); it had no workspace receipt, invocation, or authorization, and the external run/workspace roots were removed. Do not retry until a scoped correction resolves the clone context-byte mismatch without weakening identity checks. Execution remains disabled.

Start with:

```powershell
git status --short --branch
git log -3 --oneline
```
