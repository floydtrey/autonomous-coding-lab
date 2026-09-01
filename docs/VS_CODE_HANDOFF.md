# VS Code Handoff

Resume `main` from the accepted Phase 3 checkpoint `00b1769` in `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`.

Read `AGENTS.md`, `docs/START_HERE.md`, `docs/CURRENT_STATE.md`, and `docs/WORKPLAN.md`; treat the work plan as the trusted sequence. Inspect the dirty tree before editing and preserve unrelated changes.

Phase 3 is complete. `dispatch-invocation` gates every durable transition, custody record, adapter path, and evaluator on `require_execution_enabled`; it binds exact authorization, controller, attempt, workspace, prompt, runtime, custody, result, and candidate evidence.

The current **unaccepted** working tree implements Phase 4’s workspace-write bridge without executing it. `worker-lab-framework-adapter:v2` remains read-only; v3 is a separately versioned workspace-write contract. The framework rebuilds the consumer profile/context packet and reuses `code_task`, candidate-content, and repository-handoff validation. Worker Lab routes write dispatch through the existing gate-first lifecycle/Windows Job custody boundary and accepts only exact changed paths, unchanged HEAD, clean diff, sealed tests, absence proof, and a retained candidate manifest.

Current-tree validation: framework protocol/code-task tests **63 passed** and framework compile/full validation **213 passed**; Worker Lab service/client/integration tests **70 passed** and the Worker Lab full suite **369 passed** with seven expected Windows symlink-capability skips. Manifest identities: framework `sha256:b9c1061422b0cb28e94086f070ddf8fe4bf4c7a744b7e8589af2dca2b87de1f8`, Worker Lab `sha256:7ec7255a1853b21ed4888846b0063565d2898505ab6535e07f174d4809a4fd99`; execution is still disabled. No adapter, worker, Codex/local model, or external/product repository ran. This does **not** prove or complete Phase 4.

Before any real workspace-write run, obtain explicit authorization for one disposable non-product repository, exact starting commit and readable/writable scope, one named task/test plan, controller, temporary policy activation, post-run absence/candidate review, and immediate return to disabled. It must separately prohibit commit, push, PR, merge, and external/product-repository access.

Start with:

```powershell
git status --short --branch
git log -3 --oneline
```
