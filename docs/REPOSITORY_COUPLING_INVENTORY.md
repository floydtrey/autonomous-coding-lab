# Repository Coupling Inventory

**Baseline audited:** `d992a74ab2c84cf96b5736547e93a4a196c25839`

**Scope:** active runtime/domain code in Autonomous Worker Framework, Worker Lab, and
Knowledge Core; active Worker Lab curricula; and root runtime configuration. Tests,
prototypes, `docs/legacy/`, `migration/inventory/`, and Local Model Bench were excluded
because they are not the current execution/domain pipeline.

**Invariant:** ACL is the logical system. A repository can supply a Git-backed coding
workspace or governed knowledge source, but its name, URL, remote, branch, checkout
path, or `.git` location is not ACL system/project/target identity and grants no
authority.

## Classification 1 — justified Git-backed mechanics or evidence

These occurrences may remain when the selected capability explicitly requires a
Git-backed coding workspace or Git-backed knowledge source.

| Occurrence | Why it is justified | Boundary |
|---|---|---|
| `components/autonomous-worker-framework/tools/repository_state.py`: `repository_head()`, `changed_paths()`, `require_clean_workspace()`, `require_repository_root()`, `candidate_content_digest()` | Exact base state, changed-path boundary, cleanliness, and candidate bytes are deterministic coding-workspace evidence. | The module is a Git workspace adapter, not a target/system abstraction. |
| `consumer_profile.py` and `code_task.py`: `repo_root` parameters and `repository_head` in context/task/result records | The current code-task seam verifies one exact Git source state before and after a bounded edit. | The root is supplied operationally; the SHA is capability-specific evidence. Neither identifies ACL or the logical target. |
| `worker_result.py`, `repository_handoff.py`, and `local_git_publisher.py`: `base_sha`, `candidate_sha`, `changed_paths`, and candidate-content digests | These bind a coding candidate to exact Git state. Local publication is an explicitly separate Git backend. | Publication remains separate from execution and does not create universal target identity. |
| `worker_lab/workspace.py`: local clone, detached checkout, clean-state checks, remote removal, `.git` isolation, no alternates/submodules/nested repositories, and exact HEAD checks | These prepare and verify a disposable Git-backed coding workspace. | The mechanics are valid; the durable `template_repository` field used around them is classified separately below. |
| `worker_lab/framework_adapter.py`, `windows_job.py`, `read_only_evidence.py`, and `evidence.py`: starting/observed HEAD, changed paths, diff checks, `.git` isolation, and base-commit evidence | These are independently observed coding-workspace facts and containment checks. | V3 must make them conditional on the Git-backed coding capability rather than universal runtime identity. |
| `pydantic_ollama_worker.py`: rejection of `.git` paths | Preventing model access to Git control data is a valid bounded-file security rule. | The adjacent `target_repo` path is only a backend locator, classified below. |
| `worker_lab/operator_control.py` and `backup.py`: rejection/exclusion of enclosing `.git` data | These prevent operator-state or backup paths from overlapping source-control internals. | Safety mechanic only; no target identity meaning. |
| Worker Lab catalog commands `repository-identity` and `diff-integrity`, and their `head`, clean-state, and changed-path evidence | These tests are valid for a Git-backed coding-workspace profile. | Later catalog/schema work must not apply them to every future target capability. Branch or repository labels must not become target identity. |
| Knowledge Core repository-import code in `knowledge_core/application/repository_source.py`, `repository_import.py`, `governed_source_selection.py`, `projection_lineage.py`, `section_generation.py`, and corresponding domain/storage/API records: source commit, `git_blob_sha`, `source_repository_key`, manifest digest, and source paths | These are immutable source/provenance evidence for the governed Git import backend. `source_repository_key` is a Knowledge Core source key, not ACL target identity. | Git object verification is retained. Locator fields are classified separately below. |

The exact Git SHA is therefore not itself obsolete. The coupling problem is using
that SHA, a repository label, or its checkout locator without a separate logical
target/workspace identity.

## Classification 2 — backend-only locators

These values can be needed to reach a checkout, component, or governed source on one
host, but must not become durable system identity or authorization.

| Occurrence | Locator role | Required later treatment |
|---|---|---|
| `worker_runtime.py` `WorkerRequest.target_repo` and `framework_repo`; matching fields/arguments in `code_task.py`, `pydantic_ollama_worker.py`, `codex_runtime.py`, `context_probe.py`, `local_worker_harness.py`, `task_contract.py`, `worker_lab_adapter.py`, and `workspace_write_adapter.py` | Host-local working-directory and framework-code locations. | Task 4 dispatch reconstruction should carry them inside the selected workspace/framework backend, not universal task identity. Obsolete Codex/commissioning owners are deleted in Task 7. |
| `worker_lab/application_service.py` and `cli.py` `target_repository` / `template_repository` `Path` arguments; `workspace.py` template/workspace paths | Operator/backend inputs used to locate a local Git checkout and disposable workspace. | Keep path validation in the coding-workspace backend. Replace repository-only generic commands/interfaces during Tasks 3–5. |
| `WorkspaceReceipt.workspace_root_digest`, `workspace_path_digest`, and `workspace_relative_path`; matching Invocation/Result V2 fields | Host-local custody locators represented as digests/relative paths. | Custody V2 and Invocation/Result V3 must keep host paths out of logical target identity while retaining containment evidence. |
| `worker_lab/provider_qualification.py` `repository_root` | Local ACL installation root used to read the disabled portable manifest. | Treat as an installation lookup path; portable identity V2 must remain host-independent. |
| Knowledge Core `RepositorySourceReader.repository_root` | Server-configured path to the selected Git source backend. | Keep in host/backend configuration only. |
| Knowledge Core `repository_locator` and retrieval/projection field `repository` in repository-import manifests, observations, segment evidence, API schemas, and Controller Task Packet knowledge evidence | Locator/provenance for an imported knowledge source; it is not the task target. | Preserve provenance as needed, but never equate it with ACL target/system identity or authority. A future backend-neutral source contract may version the locator representation. |
| Component `root` / `production_root` paths in `config/portable-installation-manifest.json` | Installation-relative component locators. | Portable identity V2 may retain relative component locations while separating all host/platform/provider facts. |

## Classification 3 — obsolete repository-as-system coupling

These occurrences currently make a repository label or Git-only fact part of a
universal/durable target contract, or belong to obsolete repository-centered runtime
paths. Task 1 records but does not version or delete them.

| Occurrence | Coupling | Planned removal/versioning boundary |
|---|---|---|
| `worker_lab/models.py` `ExerciseRecord.template_repository`; `worker_lab/policy.py` `ContextManifest.repository`; equality checks in `validation.py` and `application_service.py`; matching active curricula/exercise/context JSON | A repository label is the durable exercise/context target identity. | Invocation/Result V3 and related authority-record versioning in Tasks 3 and 5 must introduce logical target/workspace identity and make Git source state capability-specific. |
| `WorkspaceReceipt.template_repository` and its comparisons in `workspace.py`, `framework_adapter.py`, and `application_service.py` | The receipt binds the workspace to the repository label rather than a logical target plus backend evidence. | Version with the workspace/Invocation V3 migration in Tasks 3–5. |
| Universal `starting_commit` / `template_commit` placement in `AttemptRecord`, `ContextManifest`, `InvocationRecord` V2, `ResultRecord` V2, Controller Task Packet V1, application/lifecycle/validation code, and current JSON definitions | The SHA is valid Git evidence, but the current schemas have no independent logical target/workspace identity, so it implicitly stands in for that identity and requires every target to be Git-backed. | Preserve the SHA only inside the Git-backed workspace evidence portion of V3/current records. Do not mechanically rename it to `target`. |
| `worker_lab/cli.py` generic `--target-repository` / `--template-repository` commands and `application_service.py` generic repository validation | The generic service interface assumes repository equals target. | Replace only with the V3/service migration in Tasks 3–5; keep Git validation inside the coding-workspace backend. |
| `components/autonomous-worker-framework/tools/monorepo_identity.py` and `config/monorepo-identity.json`: former `repository_id`, branch, tag, commit/tree, and `remote_state` identities | Pre-consolidation repository histories and remote state are treated as current component/system identity. | Remove with obsolete active-tree identity paths in Task 7; rebuild source/component identity in portable identity V2 during Task 8. |
| `worker_lab/installation_manifest.py`, `config/installation-manifest.json`, and old installation checks in `worker_lab_adapter.py`: per-component `repository_id` / source commit/tree | The legacy Codex installation contract identifies ACL components through former repositories and obsolete launcher state. | Delete after current dispatch replacements exist, in Task 7. |
| `codex_runtime.py`, `context_probe.py`, `local_worker_harness.py`, `task_contract.py`, `worker_fixture_validator.py`, and commissioning-only tests/fixtures | Obsolete Codex/Mine Tracker/`autonomy_smoke` paths assume an external Git repository is the product target. | Task 1 extracts the generic repository-state helpers only. Delete these paths and their tests in Task 7 after current replacement coverage exists. |
| `worker_lab_adapter.py`, `workspace_write_adapter.py`, `framework_client.py`, and Invocation/Result V2 integration shell | Old adapters combine host installation, repository workspace, provider/runtime, and dispatch identity. | Replace through Tasks 3–5; do not extend them with Provider Binding. |
| `worker_lab/synthetic_read_only.py` and its repository/template records | Historical synthetic Codex proof uses repository identity as the complete target. | Delete in Task 7 after replacement deterministic coverage exists. |
| `consumer_profile.py` `MINE_TRACKER_PROFILE` and explicit use in obsolete `context_probe.py` | Product-specific commissioning residue inside the old profile/probe surface. Task 1 removes it as an implicit generic default; it remains only when explicitly selected by legacy tests/probe. | Remove with obsolete Mine Tracker/commissioning paths in Task 7. Current protected task data supplies profiles explicitly. |
| Worker Lab catalog prose/commands that make repository identity tests unconditional for all operations | A Git capability test is expressed as if every ACL target were a repository. | Scope/version catalogs when V3 introduces capability-specific workspace evidence; retain the underlying Git checks for coding work. |

## Task 1 resolution

- Provider-neutral Git workspace inspection now lives in `repository_state.py`.
- `code_task.py`, `repository_handoff.py`, and `local_git_publisher.py` no longer
  import helpers from the commissioning harness.
- `local_worker_harness.py` consumes the extracted helpers only to keep its old tests
  intact until the documented Task 7 deletion gate.
- The disabled legacy installation manifest's file-set closure includes the new
  helper only so transitional fail-closed identity checks still describe exact
  current bytes; its repository/Codex schema semantics were not extended.
- Generic context creation, context verification, and code-task execution require an
  explicit `ConsumerProfile`; Mine Tracker is no longer an implicit generic default.
- No legitimate Git source-state verification, workspace containment, knowledge
  provenance, publication, or diff-integrity behavior was removed.

## Explicitly deferred

Task 1 does not change custody, Invocation/Result V2 records, Provider Binding,
dispatch, Worker Lab authority records, active curricula, legacy deletion, portable
identity V2, provider/model qualification, or execution. The classifications above
are the input to those later bounded tasks.
