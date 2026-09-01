# Current State

**Last updated:** 2026-09-01

**Repository:** `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`

**Branch:** `main`

**Last accepted Phase 3 implementation checkpoint:** `00b1769`

**Isolated GUI prototype checkpoint:** `a72f026d57b9d938c4ebba1987379482af4e39b3`

**Phase 2 proof record checkpoint:** `01620a817e13ee4032aeee6c2997a1487496d872`

**Remote relationship at acceptance:** local `main` and `origin/main` matched with zero divergence

**Execution authority:** disabled

## Plain-language status

Phase 1 is complete. The consolidated repository now has a clean, remotely recoverable checkpoint with strict installed-component identity, current active documentation, preserved legacy records, and passing root/component validation. No worker or model was run.

Phase 2 is complete. Exactly one authorized synthetic read-only Codex proposal ran through Worker Lab and the framework, reached `CANDIDATE`, retained exact evidence, left the disposable workspace unchanged, and ended with verified process absence. The installation was restored to disabled immediately afterward.

Phase 3 is complete at `00b1769`. Its shared service provides strict read-only queries; complete attempt timelines and candidate review; attempt/workspace lifecycle commands; durable invocation preparation, controller-bound authorization, terminal rejection, pre-dispatch cancellation, read-only dispatch, and fail-closed recovery after verified process absence; and backup, verification, and restore operations for CLI and future GUI clients. Execution remains disabled.

The accepted Phase 3 working tree completes the read-only dispatch packet. `dispatch-invocation` reloads exact authorization, controller, attempt, workspace, prompt, runtime, custody, and result identities; invokes the framework client, adapter, Windows Job, and sealed read-only-evidence primitives only after the execution gate; and leaves failed outcomes recoverable.

## Accepted Phase 4 implementation bridge checkpoint

Commit `8862880` establishes the workspace-write bridge; it is not a Phase 4 proof or completion claim.

- The read-only `worker-lab-framework-adapter:v2` protocol remains unchanged and rejects workspace-write operations. The separate `worker-lab-framework-adapter:v3` operation accepts only the versioned workspace-write task contract.
- The framework reconstructs and validates its consumer profile/context packet, existing `code_task`, candidate-content, and repository-handoff primitives. It returns only canonical, bounded candidate identity evidence.
- `WorkerLabApplicationService.dispatch_invocation` routes an authorized workspace-write invocation through the same gate-first lifecycle and Windows Job custody boundary as read-only dispatch, then accepts a candidate only after exact path, HEAD, diff, sealed-test, custody, and retained candidate-manifest checks.
- Production execution remains disabled. The implementation was exercised only through deterministic injected adapters against test repositories; no worker, Codex, model, adapter execution mode, or external/product repository ran.

Validation: framework bridge tests **63 passed**; framework compile/full validation **213 passed**; Worker Lab application-service/framework-client/integration tests **70 passed**; Worker Lab full suite **369 passed** with seven expected Windows symlink-capability skips. The manifest identifies framework runtime closure `sha256:b9c1061422b0cb28e94086f070ddf8fe4bf4c7a744b7e8589af2dca2b87de1f8` and Worker Lab production tree `sha256:7ec7255a1853b21ed4888846b0063565d2898505ab6535e07f174d4809a4fd99`; execution remains disabled. This implementation checkpoint is accepted, but it does not prove or complete Phase 4.

### Active Phase 4 disposable task packet

The user-authorized local disposable repository is `C:\Users\MineTrackerWorker\Documents\ChatGPT\Autonomous Coding Lab\phase4-proof-20260901-01`. It has no remotes, is clean at starting commit `a36049c5e4d97a2518d13578d6090fdd50738c02`, and supplies the sealed read-only `tests/test_models.py` file with SHA-256 `3a2f0faa16488f02fbfccdc0bf78ac43d7cd1e5446969627c2e19cc0817dcbd3`.

The active protected Worker Lab definitions admit only `phase4-record-normalizer-v1`: curriculum `phase4-record-normalizer` (`sha256:f0be43ca9c0b83785fe3cc5e00c62e5bc1e57d7f2ba2554ae90613f6641fe1ed`); workspace-write exercise version 1 (`sha256:d81836446a8dfaa8eca2fc0025567c969e97e5b30de97a35a39ce504bfac67fa`); context manifest version 1 (`sha256:e677c8ec088857e89c916a5cb7eb7c5f7447a6097eb571cc48cc81dc2fd29416`); and `phase4-record-normalizer-v1` catalog (`sha256:8c5ee8dd7913e14556582ed3b6e9f989721c97c81e9573845dda1f10c8cf9f76`). The `PHASE4_RECORD_NORMALIZER:v1` profile selects exactly `T023`, `git diff --check`, then `T024`, `python -B -m unittest discover -s tests -p test_models.py -v`. It permits only `record_ledger/models.py` to be changed, protects the sealed test, requires the existing `core-worker-policy`/`coding-worker` identities, and prohibits dependencies, network or external/product-repository access, commit, push, publication, PRs, merges, and Git-configuration changes. A future dispatch must be separately authorized by `ACL-primary-controller`.

Definition loading, exact selection, repository/commit binding, and substituted writable path, command, or commit rejection passed in the focused protected-definition suite (**6 passed**). The Worker Lab component suite passed **373** tests with seven expected Windows symlink-capability skips. Neither check ran a worker, model, adapter execution operation, or disposable-target test command.

The first isolated-clone preparation exposed Windows line-ending conversion of the sealed context bytes and failed closed. The `751d98f` change added `core.autocrlf=false` only to the no-checkout clone command; it did not preserve the source working-tree bytes during the later checkout.

On 2026-09-01, the exact non-executing retry created durable state at `C:\Users\MineTrackerWorker\Documents\ChatGPT\Autonomous Coding Lab\phase4-proof-20260901-01-worker-lab-state` and DRAFT attempt `ATTEMPT-882FD09624784C8D80D9020914EE8CF0`. Before writing, the authorized source was verified clean, detached at `a36049c5e4d97a2518d13578d6090fdd50738c02`, with no remotes and sealed `tests/test_models.py` SHA-256 `3a2f0faa16488f02fbfccdc0bf78ac43d7cd1e5446969627c2e19cc0817dcbd3`. Both preparation attempts failed closed with `CONTEXT_DIGEST_MISMATCH`; the second process-level Git-config override was correctly stripped by the helper's Git-environment sanitization. Compensation was verified: the attempt remains DRAFT, no workspace receipt or invocation exists, and `C:\Users\MineTrackerWorker\Documents\ChatGPT\Autonomous Coding Lab\phase4-proof-20260901-01-worker-lab-workspaces` is empty.

The verified cause is that the source working-tree sealed file has CRLF bytes (the required digest), while its Git blob has LF bytes (`caad10830de40bed7df3f8b6c465276e65bab88fb92dab957eb13e12514232f2`). The helper's sanitized checkout therefore materializes the LF blob after its no-checkout clone. Do not retry or authorize dispatch until a separately scoped and validated correction preserves the sealed working-tree bytes without weakening the exact context check. No worker, Codex, local model, framework execution adapter, target test command, commit, push, network access, or external/product-repository operation occurred.

## Accepted Phase 1 checkpoint

The accepted checkpoint consists of these bounded commits:

- `4678c87` — strict installation identity v2 and bilateral protocol update;
- `591ae42` — Local Model Bench CRLF Markdown-heading compatibility repair;
- `5f6c41d` — active-documentation consolidation and byte-preserved legacy archive.

At acceptance, the working tree was clean; local `main` and `origin/main` both resolved to `5f6c41da132daa12f0bb8c4be054112d77ef7e54`; remote divergence was `0 0`; and execution remained disabled.

## Phase 1 validation evidence

No worker or model was run. With temporary output placed outside every Git repository:

- root inventory tools: 9 passed;
- framework compile gate: passed;
- framework full suite: 208 passed;
- Worker Lab full suite: 330 passed and seven expected Windows symlink-capability skips;
- Local Model Bench: 13 passed, including the CRLF regression, and the baseline configuration validated;
- framework documentation contract: 5 passed after the active-document update;
- 43 archived documentation files matched their accepted source blobs and were committed as 100% renames;
- both manifest consumers agreed on framework digest `sha256:81cc5608ec465133a8eb0bfe8a14ab744913ec4c35010b8cdf64f8cc9d61a6a3`, Worker Lab digest `sha256:a7d4d4eef3657bdd73f302a9fd11d150aa740bb052f16d083b04868725b9b6b2`, and disabled execution;
- `git diff --check` passed.

This evidence is accepted at checkpoint `5f6c41d`.

## Accepted Phase 2 readiness checkpoint

Commit `06a7d21` adds the operator boundary without enabling execution:

- `worker-lab doctor` verifies the complete manifest, installed component closures, and pinned Python/Codex identities without launching a subprocess;
- the synthetic command requires a new absolute directory outside every Git repository, a validated controller identity, and the exact one-time confirmation phrase;
- disabled policy is checked before the run directory or any subprocess can be created;
- admitted runs persist activation and authorization evidence bound to the controller, run-directory digest, invocation, installed components, and runtimes before adapter preflight;
- recovery grants no new execution authority and accepts only exact durable evidence, an unchanged workspace, and—after dispatch—verified process absence.

Validation for this checkpoint did not run a worker or model:

- Worker Lab full suite: 337 passed and seven expected Windows symlink-capability skips;
- focused operator/CLI/synthetic suite after final hardening: 21 passed;
- framework bilateral adapter suite: 36 passed;
- root inventory plus active-document checks: 14 passed;
- non-executing doctor reported manifest digest `sha256:2ffd73d1a6edf49ea906393de7dd89411a9d94c62d1cddb574f246aa3382a826`;
- doctor reported Worker Lab digest `sha256:a98085ec33a89616e388a490382c25043088c79196c5a3a671d46e07ca5670cf` and `execution_ready: false`;
- local `main` and `origin/main` matched after the readiness commit was pushed.

## Accepted Phase 2 proof

The bounded proof used controller `codex-primary-controller` and external run directory `C:\Users\MineTrackerWorker\Documents\ChatGPT\Autonomous Coding Lab\phase2-proof-20260831-01`. The retained run contains exactly one attempt, invocation, result, proposal, and process-custody record.

- attempt: `SYNTHETIC-545B69F603DB4806AAB5107A1D8EDCAB`, state `CANDIDATE`;
- invocation: `INVOCATION-3F76D29A63C74917BE8387CCA81EE995`, state `COMPLETED`;
- authorization: `AUTHORIZATION-B2BA9B0F7F364E648C23F48EFF69CB37`, bound to the controller, run-directory digest, activation evidence, and invocation;
- result/candidate digest: `sha256:ae7c1ef757d61bdb89b84b60ea2326d3871113184b3481d7b0298135131d4e2a`;
- proposal digest: `sha256:2b8e11c4a51e5f316132841be9d4aaa116b224078fc7774339ad54cc2d8ee1cc`, matching the retained proposal bytes;
- activation manifest digest: `sha256:3e67ea4937c46deefa90070632c560242fdda1c98ae69033507887a1b58ffbfd`, with only Worker Lab and the framework active and Local Model Bench advisory;
- workspace: detached at synthetic commit `9c97b63df9569848c7f56c5e8df56bfa6b1abd2a`, unchanged, zero changed paths, and no remotes;
- sealed validation: `T001` passed;
- custody: `ABSENCE_VERIFIED`, zero active processes at `2026-09-01T02:31:24Z`;
- external product repositories accessed: none;
- verified durable backup: 14 files under the retained run directory, manifest SHA-256 `3cb8c9a55806d8b858ff1ab6fd3b2220f42563d20214ba5b062868d64eda6a87`;
- post-proof doctor: manifest digest `sha256:2ffd73d1a6edf49ea906393de7dd89411a9d94c62d1cddb574f246aa3382a826`, `execution_ready: false`, Worker Lab deferred, framework available.

Interruption and recovery behavior remains covered by the accepted deterministic tests; recovery was not applied to the successful retained candidate.

## Accepted Phase 3 read-only service checkpoint

Commit `a288a15` establishes the first shared Worker Lab application-service boundary:

- versioned health, installation-status, record-list, and record-detail DTOs;
- non-mutating list/show coverage for all definition and durable attempt, invocation, result, failure, and evidence collections;
- deterministic identity ordering and record digests suitable for future GUI clients;
- strict rejection of invalid roots, substituted storage, corrupt records, duplicate identities, unsupported collections, unsafe identities, and missing records;
- CLI access through `health`, `installation-status`, `list-records`, and `show-record` without private storage calls;
- refreshed Worker Lab installed-tree identity while execution remains disabled.

Validation did not run a worker or model:

- focused service tests after final hardening: 7 passed;
- Worker Lab full suite before the final test-only hardening: 342 passed and seven expected Windows symlink-capability skips;
- framework bilateral adapter suite: 36 passed;
- framework compile gate and full suite: passed, 208 tests;
- root inventory tools: 9 passed;
- live absent-root health query left the root absent and reported `execution_ready: false`;
- installation status reported manifest digest `sha256:79edaae89f8f5b19d8bd12df1c31d8f7161b2b24999e0d8dee4d669e01cb8976` and Worker Lab digest `sha256:2705bb48173bcfff22d43a5014ae75d62513910684a155dba5ba87b8a7564884`;
- local `main` and `origin/main` matched at the code checkpoint with zero divergence.

## Accepted Phase 3 attempt/workspace service checkpoint

Commit `cf9d45f` moves the existing attempt and workspace lifecycle behind the shared service without adding an execution path:

- versioned `worker-lab-service-operation-result:v1` DTOs expose the affected record, identity, type, and digest to future clients;
- `create-attempt`, `prepare-workspace`, `verify-workspace`, `transition-attempt`, and `discard-workspace` route through the service while preserving established CLI JSON;
- malformed command values and unresolved authority fail before durable state is created;
- receipt-bound workspaces cannot be bypassed with a generic abort transition;
- the packet creates no invocation and grants no dispatch authority.

Validation did not run a worker or model:

- focused service/CLI/operator suite: 27 passed;
- Worker Lab full suite: 347 passed and seven expected Windows symlink-capability skips;
- framework compile gate and full suite: passed, 208 tests;
- final bilateral adapter check with a valid short temp path: 36 passed;
- root inventory tools: 9 passed;
- doctor reported manifest digest `sha256:ed71ac462cedba9f96bafd5ee01ab750809e3ec0753b9ed6a6ed021f62e41eae`, Worker Lab digest `sha256:9f51aeb953cc689cd160a9e03fd31575fec3825b0b2b5f14713a028632f34fa4`, and `execution_ready: false`.

Commit `a72f026` preserves the user's 15-file Tkinter design under `components/worker-lab/prototypes/gui-shell/`. It parses and imports as an isolated prototype, has no production entrypoint, does not connect to the application service, and is excluded from the protected production-tree identity.

## Accepted Phase 3 invocation-command checkpoint

Commit `e776743` adds invocation preparation and decision commands without adding execution:

- `prepare-invocation` strictly revalidates the READY attempt, protected definitions, verified workspace receipt, test plan, and installed identities;
- exact prompt bytes are bounded, content-addressed, and retained for restart-safe reconstruction;
- a single attempt cannot accumulate competing invocation envelopes;
- operation-result v2 adds the immutable invocation identity without silently changing the accepted v1 DTO;
- authorization requires that exact immutable digest and a validated controller identity;
- rejection requires the same digest and is terminal;
- CLI commands expose preparation, authorization, and rejection without calling an adapter or process runner.

Validation did not run a worker or model:

- final focused service suite: 12 passed;
- Worker Lab full suite: 349 passed and seven expected Windows symlink-capability skips;
- framework compile gate and full suite: passed, 208 tests;
- final bilateral adapter check: 36 passed;
- root inventory tools: 9 passed;
- doctor reported manifest digest `sha256:3409e5b447d74017b20c58d3259aa22b45c2428d0c412d4e0f3f671150ff4f8d`, Worker Lab digest `sha256:f39de294d5399149549a3e4dedaf1d395615ac97d800118ab9144f4a8dadfd94`, and `execution_ready: false`.

## Accepted Phase 3 cancellation and backup-service checkpoint

Commit `e505866` adds the next operator controls without adding execution:

- cancellation accepts only an `AUTHORIZED` invocation and requires its exact immutable digest plus the same validated controller that authorized it;
- successful pre-dispatch cancellation records terminal `ABORTED` while retaining authorization identity and creating no result or process-custody record;
- prepared invocations still use rejection, while dispatching and uncertain invocations remain unavailable to this cancellation path and require later recovery orchestration;
- backup creation, verification, and restore now route through the shared service instead of CLI calls to private backup functions;
- versioned backup-result v1 binds each operation to the canonical backup-manifest digest, file count, and exact manifest content;
- the CLI preserves its established verified-file-count output for backup commands.

Validation did not run a worker, model, adapter execution operation, or external repository:

- focused service/CLI/backup suite: 43 passed;
- Worker Lab full suite: 352 passed and seven expected Windows symlink-capability skips;
- framework full suite, including independent manifest and adapter-contract coverage: 208 passed;
- root inventory tools: 9 passed;
- doctor reported manifest digest `sha256:ca3cd65c1eada0bb21881245be3d7c3bf27fcf936aabb8b64ae018f958ed082a`, Worker Lab digest `sha256:e327735568d0999fcf9bc1916967c6000433c611924c958d7ea4a09256c86c05`, and `execution_ready: false`.

## Accepted Phase 3 recovery-service checkpoint

Commit `e938a18` adds restart-safe invocation recovery without adding dispatch:

- the recovery command requires the immutable invocation digest and the same validated controller that authorized it;
- exact attempt, invocation, workspace receipt, workspace root/path, starting commit, and pre-launch content identities are revalidated before state changes;
- a terminated dispatched process can gain absence proof only after the exact original controller is gone and its durable active-process count is zero;
- custody whose own state is `UNCERTAIN` remains fail-closed and cannot be promoted into absence proof;
- no result may exist, and any workspace change blocks recovery without transitioning durable state;
- `DISPATCHING` is durably classified `UNCERTAIN` before terminal `ABORTED`, the running attempt is aborted with an explicit retained-workspace outcome, and partial writes can be completed safely on retry;
- recovery-result v1 returns exact terminal attempt, invocation, custody, and unchanged-workspace evidence for CLI and future GUI clients.

Validation did not run a worker, model, adapter execution operation, or external repository:

- focused application-service suite: 20 passed;
- Worker Lab full suite: 357 passed and seven expected Windows symlink-capability skips;
- framework full suite, including independent manifest and adapter-contract coverage: 208 passed;
- root inventory tools: 9 passed;
- doctor reported manifest digest `sha256:d9409f9b28047a7f05ace3fd6d7cb414ca8b3b698eabaef7bad4406d3db66bc0`, Worker Lab digest `sha256:2d50c93226689a4ab08d7adf52dd7df928bf059a256d88ada76245efea35a201`, and `execution_ready: false`.

## Accepted Phase 3 timeline and candidate-review checkpoint

Commit `f69bfad` adds the remaining read-only operator queries before general dispatch:

- `show-attempt-timeline` returns the complete durable attempt view: attempt, workspace receipt, linked invocations, results, process custody, evidence, and failures;
- `review-candidate` requires one exact completed invocation/result/custody chain, verifies the retained candidate content and every linked evidence record, and returns changed paths, validation stages, evidence, and the failure boundary;
- both CLI commands use only `WorkerLabApplicationService`, never call private storage directly, and reject missing, corrupt, or conflicting durable records without mutation;
- the installed Worker Lab identity is `sha256:61f01988f8626dd0cf1ac449b7ddce6e849f3d2879aaed129e849b93d495d143`; doctor reported manifest digest `sha256:d44c1bab6b6e3a27fb714da7960908cbe909a6e1b9bf653ecce72495233d7c66` and `execution_ready: false`;
- focused application-service and CLI validation passed 36 tests; the Worker Lab component suite passed 359 tests with seven expected Windows symlink-capability skips.

## Accepted Phase 3 general-dispatch completion checkpoint

The accepted Phase 3 working tree completes the application-service gate:

- `dispatch-invocation` is the CLI/service-owned read-only dispatch path; it revalidates authorization, controller, protected definitions, workspace, prompt, runtime, custody, result, and candidate identities;
- the committed disabled policy is enforced before any durable dispatch transition, adapter call, or evaluator; the production framework-client, Windows Job, and sealed-evidence path is therefore unreachable without separate execution authority;
- deterministic injected tests cover disabled non-mutation, legal candidate creation, malformed/mismatched responses, and recovery-compatible failures;
- focused application-service validation passed 26 tests; Worker Lab passed 363 tests with seven expected Windows symlink-capability skips; framework compile/full validation passed with 208 tests;
- doctor reported manifest digest `sha256:12a23a0c20fcbaeb9f06dd32d684f9a030d100235d6c0ec97bda07dead91dec4`, Worker Lab digest `sha256:3d3a58e3336e3a565fdcc977fcb199b2115f6232fc425d1368108c80dfe78a7b`, and `execution_ready: false`.

## Proven component capabilities

### Worker Lab

Worker Lab has strict, versioned records for curricula, policies, roles, exercises, attempts, evidence, failures, and test catalogs. It can validate authority, create attempts, prepare and verify isolated workspaces, manage lifecycle transitions, safely discard workspaces, verify evidence, and create/verify/restore durable backups.

It is the control plane. It decides whether a task is valid and whether evidence is sufficient.

### Autonomous Worker Framework

The framework has tested code for ChatGPT-managed Codex execution, API-key rejection, credential stripping, explicit sandbox modes, target-repository containment, timeouts, bounded output, trusted validation, candidate publication, and repository handoff.

It is the execution/security engine. Capability in the code does not grant current permission to invoke it.

### Local Model Bench

Local Model Bench can run deterministic JSON or Markdown suites model-by-model through Ollama, managed llama.cpp/GGUF, or OpenAI-compatible local endpoints. It captures complete responses and timing/token metadata where supplied, checkpoints each case, resumes interrupted runs, evaluates result contracts, and supports unattended Windows runs.

It is advisory infrastructure. It neither imports Worker Lab nor participates in the worker execution path.

## Benchmark evidence

The committed 24-request smoke run proved the harness and result-capture path. Its manual review found Qwen2.5-Coder 7B provisionally useful for further planner testing, DeepSeek-Coder 6.7B useful for additional narrow-repair tests, and StarCoder2 7B unsuitable for the tested roles.

A later 90-call planning/task-creation run and an 18-case Qwen 14B native-JSON retest were completed in the source benchmark workspace. The consolidation record reports 18/18 completion, 93.33% deterministic mechanical score, and zero hard failures for the Qwen 14B retest. Semantic role fitness remains unaccepted until human review is recorded.

## Not yet available

- A general workspace-write bridge from Worker Lab to the framework.
- A production-authorized or real-proof workspace-write dispatch bridge (Phase 4 implementation is unaccepted).
- A functional Worker Lab GUI.
- Unsupervised local-model planning, task authorization, code review, publishing, or merging.
- Production-project access or modification by workers.

## Immediate next gate

Phase 3 is complete at `00b1769`; the current accepted `751d98f` tree implements, but does not prove or complete, the Phase 4 bridge. The exact non-executing Phase 4 admission retry retained DRAFT attempt `ATTEMPT-882FD09624784C8D80D9020914EE8CF0`, but preparation remains blocked by the verified CRLF-working-tree/LF-Git-blob mismatch. Do not retry preparation, alter the source target, alter execution policy, or authorize dispatch until a separately scoped correction reconciles that mismatch without relaxing the exact repository, commit, context-digest, path, command, or candidate checks. Execution remains disabled; there is no Worker Lab invocation or authorization to dispatch.

The trusted dependency-ordered delivery plan for worker execution and the Worker Lab GUI is `docs/WORKPLAN.md`.

Do not restart source recovery, import, or structural inventory work unless the underlying imported history or component paths change.
