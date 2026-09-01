# PROJECT CONSOLIDATION HANDOFF — H03

## Handoff Metadata

- **Handoff ID:** H03
- **Source label:** Local Model Benchmark and merger foundation
- **Prepared:** 2026-08-30 04:48 CDT (`America/Chicago`)
- **Coverage:** One implementation repository plus the governance-only
  consolidation repository created from this conversation
- **Authority:** Witness report only; verify against Git and active files

| Repository | Local path | Branch / relation | HEAD | HEAD tree | Remote/status |
|---|---|---|---|---|---|
| Local Model Bench | `C:\Users\MineTrackerWorker\repos\awf-live-consumer-smoke\2026-08-29\referenced-chatgpt-conversation-this-is-an\outputs\local-model-bench` | `main...origin/main` | `4a023c8230365c3098a6dff71fa9623cac059cdd` | `1b20a0e6a9e273532ed047ff3cb9f8c990f6fa01` | Public `floydtrey/local-model-bench`; tracked tree clean; active result run is ignored |
| Autonomous Coding Lab | `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab` | `main...origin/main` | `f038d5d` when handoff preparation began | Verify again before use | Private `floydtrey/autonomous-coding-lab`; clean before this handoff was added |

Repository identity was verified with Git status, HEAD/tree inspection, tracked
file inventory, and current result manifests. The new handoff files themselves
necessarily make the consolidation repository newer than `f038d5d`; use their
eventual commit as the actual handoff identity.

## 1. Purpose and Scope

`VERIFIED` Local Model Bench is a quiet, resumable Windows harness for running
the same JSON or Markdown prompt suites against deterministic model order. It
owns provider calls, isolated or explicitly preserved context, results,
checkpoints, timing/token metadata, deterministic prompt-contract evaluation,
and disposable real-task validation packets.

`VERIFIED` It supports Ollama, generic OpenAI-compatible endpoints, and a managed
loopback llama.cpp/GGUF provider through the `Provider` abstraction in
`src/localbench/providers.py`.

`VERIFIED` It does not own Worker Lab authority, worker execution security,
publication, merge authority, product behavior, or model installation files.

`VERIFIED` This conversation also bootstrapped the private
`autonomous-coding-lab` repository and created merger governance. It did not
import any source component.

## 2. Current State

### Completed and verified

- `VERIFIED` Harness version 0.3.1 provides deterministic model/suite/case
  ordering, result metadata, retries, resumability, error capture, context
  isolation/preservation, unattended launch, progress watching, and evaluation.
- `VERIFIED` Twelve unit tests passed in 5.862 seconds on 2026-08-30 during this
  handoff using `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v`.
- `RECORDED` The original 24-call smoke run completed without provider transport
  errors. Its tracked manual review rejects StarCoder2 7B for tested roles,
  identifies Qwen2.5-Coder 7B as a provisional verifier-gated planner candidate,
  and gives DeepSeek-Coder 6.7B limited narrow-repair promise.
- `VERIFIED` The 90-call planning run
  `background-20260829T201719-f1197139` completed all 90 cases after one resume.
- `VERIFIED` The private consolidation repository exists with M0 complete and an
  M1 audit draft at commit `f038d5d`. Its current contract, inventory, path
  ledger, decisions, milestones, and migration log are under `docs/`.

### Implemented but requiring interpretation or further validation

- `VERIFIED` The 90-call deterministic evaluation scored:

  | Model | Score | Hard failures |
  |---|---:|---:|
  | Qwen2.5-Coder 7B | 91.11% | 2/18 |
  | DeepSeek-Coder 6.7B Instruct | 71.67% | 11/18 |
  | Vera/Qwen2.5 3B Instruct Q4_K_M | 57.78% | 17/18 |
  | Phi-4 14B | 33.89% | 18/18 |
  | Qwen2.5-Coder 14B | 32.22% | 18/18 |

- `VERIFIED` Qwen 14B and Phi-4 14B frequently returned otherwise parseable
  JSON inside Markdown fences. Their hard-failure totals therefore measure a
  structured-output mismatch as well as semantic quality. They must not be
  rejected solely from those aggregate percentages.
- `PENDING` Native-JSON retesting is intended to isolate that format variable.
- `PROPOSED` Deterministic scores select candidates for deeper review; they do
  not prove safe planning or implementation.

### Prepared but not executed as end-to-end worker proof

- `IMPLEMENTED` `validation-packets/real-tasks-v1/` contains five disposable
  real-task assessments. RT-001, RT-002, and RT-004 have executable assessor
  tests; RT-003 and RT-005 have report/refusal rubrics.
- `IMPLEMENTED` `suites/scope-withdrawal.json` compares forward removal of a
  deeply integrated unreleased capability while preserving shared machinery and
  approval-gating destructive data cleanup. It has not been used to justify
  uninstalling any model.
- `IMPLEMENTED` `experiments/gui-prompt-learning/` is a deliberately disconnected
  throwaway teaching experiment with a static reference GUI and direct/planner
  prompt templates. It is not an application backend or Worker Lab UI.

## 3. Repository and Preservation State

### Local Model Bench

- `VERIFIED` The tracked tree is clean and synchronized at
  `4a023c8230365c3098a6dff71fa9623cac059cdd`.
- `VERIFIED` Complete planning runs, logs, PID records, `.venv`, caches, and
  validation workspaces are local ignored/runtime data. Do not import them
  wholesale.
- `VERIFIED` The completed 90-call run contains valuable untracked evaluation
  evidence. Select compact reviewed reports deliberately; do not commit raw
  model output merely because it exists.
- `VERIFIED` Active process PID 30316 and Ollama llama-server PID 26936 were
  observed during handoff preparation. PIDs are ephemeral observation evidence,
  not durable identity.

### Autonomous Coding Lab

- `VERIFIED` No component source has been imported.
- `VERIFIED` Worker Lab, the framework, and Local Model Bench remain authoritative
  in their original repositories.
- `VERIFIED` This handoff and the reusable request are new merger-governance
  documents and should be committed to the private repository after review.

## 4. Architecture and Durable Decisions

| Decision | Implementation state | Evidence label | Evidence | Consolidation effect |
|---|---|---|---|---|
| Provider abstraction for Ollama/OpenAI-compatible/llama.cpp | IMPLEMENTED | VERIFIED | `src/localbench/providers.py`, config schema, unit tests | Preserve as benchmark-owned adapter boundary |
| Deterministic model-by-model ordering | IMPLEMENTED | VERIFIED | runner, manifests, unit tests | Preserve ordering and resume identity |
| Context isolated by default, preserved only by explicit group | IMPLEMENTED | VERIFIED | runner/suite tests and README | Preserve; never leak context across model or suite |
| Prompt evaluation is evidence, not worker authority | IMPLEMENTED | VERIFIED | README and merger contract | Benchmark cannot authorize execution or merging |
| Real-task packets use disposable archived baselines | IMPLEMENTED | VERIFIED | `validation-packets/README.md` | Compatible with external disposable-target rule |
| One private repository with three internal trust boundaries | PARTIALLY IMPLEMENTED | VERIFIED | ACL M0/M1 docs | Governance exists; component code not imported |
| Stable `components/<source-name>/` roots through M6 | NOT IMPLEMENTED | PROPOSED | merger contract draft 0.2 | Requires M1 acceptance |
| Complete non-squashed source-history imports | NOT IMPLEMENTED | PROPOSED | ACL-D007 | Requires M1 acceptance |
| Live execution disabled through identity migration | PARTIALLY IMPLEMENTED | VERIFIED | current source authority and ACL-D008 proposal | Must remain disabled during M2/M3 |

## 5. Directory, Path, and Environment Assumptions

- Benchmark root is the long absolute path in the metadata table.
- Python environment is component-local at `.venv\Scripts\python.exe`.
- PowerShell scripts derive the component root from `PSScriptRoot` and run from
  that component root.
- Results default below `results/`; unattended launcher logs and PID files live
  under `logs/`.
- The Vera llama.cpp profile references
  `C:\MineTrackerAI\llama.cpp\llama-server.exe` and
  `C:\MineTrackerAI\models\qwen2.5-3b-instruct-q4_k_m.gguf`.
- These executable/model paths are machine-local configuration. The binaries are
  outside Git and must not be imported.
- The proposed monorepo destination is
  `components/local-model-bench/`, stable through M6.
- Historical result manifests contain the original absolute repository path.
  Preserve it as evidence; do not mechanically rewrite historical records.

## 6. Interfaces, Schemas, and Dependencies

- CLI entry point: `local-model-bench = localbench.cli:main`.
- Provider types: `ollama`, `openai_compatible`, `llama_cpp`.
- Input suites: JSON or Markdown; JSON supports explicit messages and
  `context.mode` with optional group.
- Schemas: `schemas/config.schema.json`, `evaluation.schema.json`,
  `result.schema.json`, and `suite.schema.json`.
- Durable run files: manifest, checkpoint, per-case result files, summaries, and
  evaluation reports.
- Resumption rejects changed config hash, suite hash, or ordering. Failed cases
  may be retried explicitly.
- Worker Lab and the framework do not import `localbench`; there is currently no
  runtime dependency between them.
- Real-task packets are candidate-visible scope plus separately protected
  assessor material. Candidate workspaces are disposable external repositories.

## 7. Roles, Authority, and Workflow

- Planner models may propose plans and task sets; they do not authorize work.
- Task creation consumes an accepted plan and produces independently actionable
  briefs; deterministic schema success is not semantic acceptance.
- Candidate workers operate only on disposable validation snapshots when a
  separate controller invokes them.
- Assessors run protected tests after candidate completion.
- The trusted controller selects plans, contracts, evidence, and progression.
- Local Model Bench has no commit, push, merge, cleanup, or production authority.
- Cloud escalation and final technical review remain controller decisions; they
  are not implemented as autonomous benchmark routing.

## 8. Tests and Validation Evidence

| Test/suite/run | Exact command or run ID | Last result | Evidence label | What it proves | What it does not prove |
|---|---|---|---|---|---|
| Harness unit suite | `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v` | 12 passed, 2026-08-30 | VERIFIED | Core parsing, ordering, resume, errors, providers, evaluation, native JSON placement, atomic-write retry | Model answer quality or Worker Lab integration |
| Smoke benchmark | `background-20260829T182425-cf7a65c7` | 24/24 provider calls completed; tracked manual review available | RECORDED | Basic provider/harness operation and initial behavioral comparison | Autonomous role fitness |
| Planning round 2 | `background-20260829T201719-f1197139` | 90/90 completed after one resume | VERIFIED | Five-model deterministic plan/task comparison | Final model selection or implementation safety |
| Qwen 14B native JSON | `background-20260830T033057-9d425311` | PENDING: 13/18 at 2026-08-30 04:42:45 CDT; current case `structured-provider-tasks` | VERIFIED | When complete, isolates Ollama native JSON format for Qwen 14B | No outcome may be inferred while pending |
| Real tasks v1 | RT-001 through RT-005 | Prepared, not run through a selected planner/worker pipeline | VERIFIED | Reproducible deeper test design | Actual worker competence |
| Scope withdrawal | `scope-withdrawal` suite | Prepared, not reviewed as a model-selection run | VERIFIED | Capability-removal planning test exists | Whether any installed model should be removed |

Pending run path:
`C:\Users\MineTrackerWorker\repos\awf-live-consumer-smoke\2026-08-29\referenced-chatgpt-conversation-this-is-an\outputs\local-model-bench\results\background-20260830T033057-9d425311`.

## 9. Known Problems and Technical Debt

- The 90-call run encountered a Windows checkpoint `os.replace` permission
  failure, then completed safely after resume. Retry support was added in commit
  `21d0c73`; the completed manifest intentionally still retains `fatal_error`,
  which may confuse consumers unless interpreted with final status/resume count.
- Qwen 14B and Phi-4 fenced structured responses; the active Qwen native-JSON
  retest is unfinished.
- Deterministic semantic anchors are screening heuristics, not a substitute for
  human code/reasoning review.
- The two llama.cpp configs embed machine-local absolute paths.
- Selected compact reports for the completed 90-call run have not yet been
  chosen or committed.
- The validation packets have not yet been exercised end to end by accepted
  Planner and Worker roles.
- The GUI experiment remains manual and disconnected by design.

## 10. Cross-Project Conflicts and Possible Duplication

- Worker Lab already owns attempt lifecycle, evidence, testing authority, and
  graduation. Benchmark run/checkpoint records must not become a competing
  worker-attempt system.
- Framework test IDs and Worker Lab catalogs are permanent authority. Benchmark
  case IDs and scores are experimental evaluation identities, not substitutes.
- Worker Lab already defines Planner and Coding Worker responsibilities.
  Benchmark prompt templates should test those contracts after consolidation,
  not redefine them independently.
- The GUI teaching experiment is not the Worker Lab dashboard described in
  framework design documents.
- The benchmark provider abstraction may later inform model routing, but it must
  not absorb framework Codex authentication/sandbox responsibilities.

## 11. Dangerous Assumptions

- Do not treat `status: success` as a correct model answer.
- Do not select or reject Qwen 14B from the fenced-output run before reviewing
  the native-JSON retest.
- Do not copy ignored result trees, logs, PIDs, `.venv`, model files, or llama.cpp
  executables into the monorepo.
- Do not run candidates against Worker Lab, the framework, Mine Tracker, or the
  monorepo itself; use disposable external repositories.
- Do not turn benchmark scores into execution, graduation, publication, or
  merge authority.
- Do not rewrite historical absolute paths inside completed evidence records.
- Do not let the merger invalidate resume hashes for an active run.

## 12. Must Preserve

- Complete Git ancestry through `4a023c8230365c3098a6dff71fa9623cac059cdd`.
- MIT `LICENSE` and `pyproject.toml` package identity.
- Provider abstraction and its credential/error-redaction behavior.
- Deterministic ordering, context rules, resumability, checkpoint safety, result
  schemas, and complete error metadata.
- Prompt suites, real-task validation packets, assessor separation, scope
  withdrawal probe, and GUI prompt-learning experiment.
- Tracked smoke review and selected evaluation reports.
- The pending native-JSON run path until its final state is recorded and
  reviewed.
- Private ACL merger history through `f038d5d` plus this handoff commit.

## 13. May Replace, Archive, or Discard

- `PROPOSED` Machine-specific example configuration may later be separated into
  portable examples plus ignored local overrides after parity.
- Historical chat/task reports may be archived after active facts are routed to
  canonical documents; retain provenance.
- Generated logs, PIDs, caches, `.venv`, complete unselected output trees, and
  disposable validation workspaces are excluded from import.
- No model should be uninstalled based on this handoff. Model disposition remains
  an open evidence-based decision.

## 14. Recommended Canonical Direction

`PROPOSED` Import Local Model Bench last, after the framework and Worker Lab,
under `components/local-model-bench/`. Preserve it as a separate evidence tool
with its own environment and CLI. Later add an explicit adapter that converts an
accepted Worker Lab role/profile into benchmark suites and converts reviewed
benchmark evidence into a controller-readable candidate recommendation. Do not
give the adapter authority to graduate a worker or execute a task.

## 15. Open Decisions

- Final Planner/Task Creator model selection requires the completed native-JSON
  retest, manual semantic review, and real-task evidence.
- Whether Phi-4 needs an equivalent native-JSON retest remains undecided.
- Which compact artifacts from the 90-call and native-JSON runs belong in Git is
  undecided.
- Whether model routing belongs in Worker Lab or a separate orchestration layer
  requires Worker Lab/framework handoffs.
- The final prompt/plan/task schemas must reconcile with existing Worker Lab
  invocation and test-catalog authority.
- M1 merger decisions remain proposed until the consolidation review accepts
  them.

## 16. Pre-Consolidation Actions

| Action | Owner | Reason | State | Verification |
|---|---|---|---|---|
| Preserve this handoff and reusable request in private ACL repo | Consolidation controller | Prevent loss of current context | PASS after handoff commit | Git commit and clean push |
| Let Qwen 14B native-JSON run finish or fail naturally | Benchmark operator | Preserve deterministic run and resume identity | PENDING, non-blocking for handoff | Final manifest/checkpoint |
| Create a compact reviewed native-JSON report | Benchmark reviewer | Avoid importing raw runs as conclusions | PENDING | Review file tied to run/config/suite hashes |
| Obtain other source handoffs | User/source chats | Reconcile overlapping architectures | PENDING | Numbered H01/H02/etc. reports |
| Accept M1 merger contract | User and consolidation controller | Required before source import | BLOCKED pending reconciliation | Accepted decision states and checkpoint commit |

## 17. First Actions for the Consolidation Task

1. Verify this report against both repositories and the current
   `docs/MERGER_CONTRACT.md`; do not assume the recorded ACL HEAD is still current.
2. Ingest the other numbered handoffs without normalizing away contradictions.
3. Build a claim/evidence/conflict matrix separating verified Git facts,
   recorded results, chat-only claims, proposals, and unknowns.
4. Reconcile component ownership, authority, paths, schemas, role definitions,
   and validation without importing code.
5. Update M1 inventory, decisions, path ledger, milestones, and contract.
6. Present the revised M1 contract for user approval and stop.

## Pre-Merge Readiness Checklist

| Check | State | Evidence/reason |
|---|---|---|
| Exact source identity known | PASS | Benchmark HEAD/tree verified; ACL handoff commit must be recorded after creation |
| Working-tree differences classified | PASS | Benchmark tracked tree clean; ignored active/generated data identified |
| Local-only commits protected | NOT APPLICABLE | Benchmark synchronized; ACL pushed through `f038d5d` before handoff |
| Generated/runtime data excluded | PASS | Contract and `.gitignore` classifications recorded |
| Credentials/private data excluded | PASS | No credentials selected; local paths are configuration evidence only |
| License/distribution status known | PASS | Benchmark MIT; ACL private |
| Authority boundary documented | PASS | Benchmark produces evidence only |
| Interfaces and schemas inventoried | PASS | Provider types, CLI, schemas, results, packets recorded |
| Path assumptions inventoried | PASS | Component, results, `.venv`, PSScriptRoot, and llama.cpp/GGUF paths recorded |
| Focused validation identified | PASS | Unit command and provider/evaluator tests recorded |
| Full validation identified | PASS | Unit suite plus deterministic run/review stages recorded |
| Pending runs recorded without assumed outcome | PASS | Native-JSON run recorded at 13/18 with timestamp and path |
| Rollback identity available | PASS | Source commit/tree and private ACL Git history available |
| Conflicts requiring other handoffs identified | PASS | Worker Lab/framework ownership and schema questions listed |
| Safe to begin source import | BLOCKED | M1 reconciliation and contract acceptance are not complete |

## Consolidation Warning Summary

1. `VERIFIED` The active Qwen 14B native-JSON run is pending; 13/18 is not a
   model-selection result.
2. `VERIFIED` Qwen 14B/Phi-4 hard failures in the completed run are heavily
   affected by Markdown-fenced JSON and require format-aware interpretation.
3. `VERIFIED` Benchmark records are evaluation evidence and must never become
   Worker Lab execution or graduation authority.
4. `VERIFIED` Complete ignored runs, logs, environments, and model binaries must
   not be imported wholesale.
5. `VERIFIED` The private merger repository contains governance only; no source
   component has transferred authority.
6. `PROPOSED` M1 must reconcile all numbered handoffs and receive approval before
   M2 imports the framework.

