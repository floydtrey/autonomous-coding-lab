# VS Code Handoff

Resume `main` from accepted Phase 4 admission-fix checkpoint `751d98f702c9a5794691325bb569f2bd840d6b2a` in `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`.

Read `AGENTS.md`, `docs/START_HERE.md`, `docs/CURRENT_STATE.md`, and `docs/WORKPLAN.md`; treat the work plan as the trusted sequence. Inspect the dirty tree before editing and preserve unrelated changes.

Phase 3 is complete. `dispatch-invocation` gates every durable transition, custody record, adapter path, and evaluator on `require_execution_enabled`; it binds exact authorization, controller, attempt, workspace, prompt, runtime, custody, result, and candidate evidence. The accepted Phase 4 implementation bridge checkpoint is `8862880`.

The accepted working tree implements Phase 4’s workspace-write bridge without executing it. `worker-lab-framework-adapter:v2` remains read-only; v3 is a separately versioned workspace-write contract. The framework rebuilds the consumer profile/context packet and reuses `code_task`, candidate-content, and repository-handoff validation. Worker Lab routes write dispatch through the existing gate-first lifecycle/Windows Job custody boundary and accepts only exact changed paths, unchanged HEAD, clean diff, sealed tests, absence proof, and a retained candidate manifest.

Current-tree validation: framework protocol/code-task tests **63 passed** and framework compile/full validation **213 passed**; Worker Lab service/client/integration tests **70 passed** and the Worker Lab full suite **369 passed** with seven expected Windows symlink-capability skips. The `751d98f` clone-path correction refreshed Worker Lab identity to `sha256:cbafe9fb3022f7ed0d4da230d5c56800c622be750c358f00c8a272e35b090101`; execution is still disabled. No adapter, worker, Codex/local model, target test command, or external/product repository ran. This does **not** prove or complete Phase 4.

Before any real workspace-write run, obtain explicit authorization for one disposable non-product repository, exact starting commit and readable/writable scope, one named task/test plan, controller, temporary policy activation, post-run absence/candidate review, and immediate return to disabled. It must separately prohibit commit, push, PR, merge, and external/product-repository access.

The active protected packet now admits `phase4-record-normalizer-v1`: curriculum digest `sha256:f0be43ca9c0b83785fe3cc5e00c62e5bc1e57d7f2ba2554ae90613f6641fe1ed`, exercise `sha256:d81836446a8dfaa8eca2fc0025567c969e97e5b30de97a35a39ce504bfac67fa`, context `sha256:e677c8ec088857e89c916a5cb7eb7c5f7447a6097eb571cc48cc81dc2fd29416`, and catalog `sha256:8c5ee8dd7913e14556582ed3b6e9f989721c97c81e9573845dda1f10c8cf9f76`. It binds the exact disposable repository/commit above, writable `record_ledger/models.py`, sealed `tests/test_models.py` digest `sha256:3a2f0faa16488f02fbfccdc0bf78ac43d7cd1e5446969627c2e19cc0817dcbd3`, controller `ACL-primary-controller` for a future separate authorization, and exactly `git diff --check` followed by `python -B -m unittest discover -s tests -p test_models.py -v`. Protected-definition tests passed 6 and the Worker Lab suite passed 373 with seven expected symlink skips; no worker/model/adapter execution or target test command ran.

The 2026-09-01 non-executing retry verified the authorized source clean at the full required commit, with no remotes and exact sealed-test bytes; it created external durable state at `C:\Users\MineTrackerWorker\Documents\ChatGPT\Autonomous Coding Lab\phase4-proof-20260901-01-worker-lab-state` and DRAFT attempt `ATTEMPT-882FD09624784C8D80D9020914EE8CF0`. Preparation then failed closed twice with `CONTEXT_DIGEST_MISMATCH`, fully compensating each time: no receipt, workspace, invocation, authorization, adapter, worker, test command, or process custody exists.

The source working tree's sealed test is CRLF (`sha256:3a2f0faa16488f02fbfccdc0bf78ac43d7cd1e5446969627c2e19cc0817dcbd3`), but its Git blob is LF (`sha256:caad10830de40bed7df3f8b6c465276e65bab88fb92dab957eb13e12514232f2`). The `751d98f` no-checkout clone setting does not govern the later sanitized checkout, so the cloned file remains LF. A process-level config override was intentionally stripped by the security helper. Do not retry, change the source target, enable policy, authorize/dispatch the invocation, run a sealed test, or use a wrapper workaround. A separately authorized correction must preserve the sealed source working-tree bytes while retaining all exact identity checks; then revalidate and resume this DRAFT attempt. Execution remains disabled.

Start with:

```powershell
git status --short --branch
git log -3 --oneline
```
