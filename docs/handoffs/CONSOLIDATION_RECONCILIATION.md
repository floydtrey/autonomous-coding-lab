# M1 Consolidation Reconciliation

**Prepared:** 2026-08-30
**Status:** ACCEPTED — D-01 through D-06 approved by the user 2026-08-30
**Import authority:** BLOCKED
**Execution authority:** Disabled

This document reconciles the verified repository state, H01, H03, the existing
Autonomous Coding Lab governance, and the bounded Ultra architecture review. The
user accepted its six decisions on 2026-08-30. Acceptance transfers no component
authority and authorizes no source import or execution.

## 1. Authority and evidence rules

Evidence is classified as `VERIFIED`, `RECORDED`, `CHAT-ONLY`, `PROPOSED`,
`UNKNOWN`, or `CONFLICTING`. Handoffs are witness reports. Current user
instructions and verified Git/filesystem evidence outrank handoff conclusions.

No source repository was modified during this reconciliation. No tests, workers,
models, imports, dependency installations, cleanup, commits, pushes, or
publication actions were performed.

## 2. Repository and component map

| Component | Recorded identity | Purpose and owned responsibility | Forbidden responsibility | Entry/interface | Destination | Import blocker |
|---|---|---|---|---|---|---|
| Autonomous Coding Lab | Pre-draft HEAD `7e6086954b2bfd66dd1e11a2ab467d70f85056c1`; tree `7272f715e05737e6bd1eeb67d1038ac1f4d244b2`; accepted checkpoint is the commit containing this document | Private merger governance, integration identity, milestone/rollback authority | Worker execution, benchmark scoring, silent component-authority transfer | Root governance under `docs/` | Repository root | M2 recovery/reverification prerequisites remain; M2 not authorized |
| Worker Lab | HEAD `ca55e30ccbcbf2318d73b3ef8a65f66bb9e1e684`; tree `cf7fb964aa25aabb076292865f2367f0cecb4c04`; `main` 9 ahead | Curricula, roles, policy, task authorization, attempts, test catalog, evidence, lifecycle, evaluation and graduation | Authentication, sandbox/process execution, provider security, publication or merge | Python package/CLI and canonical-JSON framework invocation | `components/worker-lab/` | 17 tracked deletions, local-only history selection, no license, monorepo identity design |
| Autonomous Worker Framework | HEAD `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`; tree `35ecad05e60c664324a4f30d42a4f6b198181074`; final-message tag; clean | Authentication, credential stripping, sandbox/process custody, containment, bounded output, strict transport/result validation | Task acceptance, curricula, graduation, model selection, publication or merge | Root-relative tools and `worker_lab_adapter.py` subprocess protocol | `components/autonomous-worker-framework/` | No remote/license; recovery bundle and prefix/identity design required |
| Local Model Bench | HEAD `4a023c8230365c3098a6dff71fa9623cac059cdd`; tree `1b20a0e6a9e273532ed047ff3cb9f8c990f6fa01`; clean `main` | Deterministic model/prompt evaluation, provider abstraction, resumable runs, experimental evidence | Worker attempts, execution security, graduation, routing authority, publication or merge | `local-model-bench` CLI; config/suite/result/evaluation schemas | `components/local-model-bench/` | MIT preservation and selected compact-evidence decision before M4 |

Dependency and authority direction is:

`benchmark recommendation -> trusted Worker Lab decision -> authorized task -> framework execution -> strict result -> Worker Lab verification/lifecycle`

The arrows are directional. A downstream component cannot assume an upstream
component's authority.

## 3. Evidence register

| ID | Class | Material conclusion | Evidence |
|---|---|---|---|
| ACL-01 | VERIFIED | No component source is imported. ACL tracked state was clean at the recorded pre-draft identity; the governance changes became the accepted M1 checkpoint. | Git identity and file inventory |
| ACL-02 | VERIFIED | The user-supplied `H01-Handoff.txt` was accepted unchanged as canonical. The excluded `.md` copy differed only by a missing first-line heading marker. | Git status, hashes, no-index diff, user approval |
| ACL-03 | RECORDED | Execution is disabled throughout M1 and identity migration. | Active ACL routing/current-state/decision documents |
| WL-01 | VERIFIED | Worker Lab is 0 behind/9 ahead and has exactly 17 unstaged tracked deletions. | Git refs/status/log |
| WL-02 | VERIFIED | All 17 deleted names have blob-equivalent Legacy copies; the extra Legacy file is `8_27_26_ChatGPT_History`. | HEAD-to-Legacy blob comparison |
| WL-03 | VERIFIED | Worker Lab pins standalone framework/adapter/Python/Codex identities and current local identities match. | `framework_client.py` and local hashes |
| WL-04 | VERIFIED | Current deletions fail Worker Lab's clean identity check. | Current status and identity code |
| WL-05 | CONFLICTING | Synthetic execution capability exists, but H01's claim that disabled-execution authority is superseded conflicts with active ACL authority. | H01 versus active ACL governance |
| WL-06 | RECORDED | Retained docs record 87 passed/2 skipped; H01's 39/37/58 counts are chat-only. | Retained docs and repository search |
| WL-07 | UNKNOWN | No current retained post-final-message end-to-end success establishes readiness. | No accepted fresh result |
| FW-01 | VERIFIED | Framework source is clean and the final-message tag resolves to its exact HEAD. | Git identity/tag/status |
| FW-02 | VERIFIED | Final proposal content is separated from diagnostics; security/process responsibilities are implemented at the adapter boundary. | Adapter/runtime source inspection |
| FW-03 | RECORDED | Historical 158-test evidence predates current final-message HEAD. | Retained framework documents |
| LMB-01 | VERIFIED | Version 0.3.1, MIT license, providers, schemas, deterministic ordering, resumability, redaction and retry mechanisms exist. | Tracked package/source/schema files |
| LMB-02 | VERIFIED | Planning run completed 90/90; Qwen 14B and Phi-4 fenced all prior structured responses. | Local retained run artifacts |
| LMB-03 | VERIFIED | Native-JSON Qwen 14B run completed 18/18 at 93.33% with zero hard failures and bare parseable JSON. | Current ignored run manifest/checkpoint/results |
| LMB-04 | UNKNOWN | Semantic role fitness and final model choice remain unreviewed. | No accepted manual/real-task review |
| LMB-05 | RECORDED | H03 reports 12 passing unit tests; twelve test methods exist but no retained run log was found. | H03 and test inventory |
| X-01 | RECORDED | Worker Lab owns lifecycle/evaluation authority, framework owns execution security, and benchmark produces evidence only. | Active ACL and source authority documents |
| X-02 | CHAT-ONLY | Luna performed chat/design; Terra and Sol authored code in separate streams. Exact file attribution is unknown. | User attestation |

## 4. Handoff comparison and conflicts

| Topic | H01 | H03 | Reconciled state |
|---|---|---|---|
| Source state | Worker/framework identities and 17 deletions | Benchmark and historical ACL identities | Current local identities are verified; older ACL observations remain historical |
| Execution | Capability exists; disabled docs called superseded | Execution disabled through identity migration | Capability does not grant authority; execution remains disabled |
| Test evidence | Chat-only focused counts and retained older counts | Historical unit/run evidence | Historical results do not replace fresh post-import validation |
| Benchmark state | Not applicable | Native run pending at 13/18 | Pending observation is historical; run is now 18/18, semantic review pending |
| IDs and lifecycle | Worker attempts/invocations/tests are authority-bearing | Benchmark runs/suites/cases are experimental | Preserve separate namespaces and lifecycle systems |
| Planner and Task Creator | Worker role/policy authority | Benchmark templates evaluate candidate behavior | Benchmark tests accepted contracts and cannot authorize work |
| Evidence | Attempt/catalog/workspace-bound evidence | Provider/result/score/resume evidence | Preserve native formats and directional adapters |
| Model routing | Owner unresolved | Benchmark may inform routing | Worker Lab controller owns routing policy through M6; benchmark recommends only |
| Import readiness | Blocked | Blocked | M1 is accepted; M2 prerequisites and separate authorization remain required |

## 5. Duplicate and reinvention map

| Concern | Overlap | ACCEPTED disposition |
|---|---|---|
| Attempt lifecycle | Worker attempts versus benchmark run/checkpoint | Worker remains canonical for workers; benchmark state remains experiment-local |
| Task contracts | Worker authorization, framework transport, benchmark task prompts | Directional adapter; no universal task schema |
| Test identifiers | Worker permanent catalog, framework stages, benchmark cases | Preserve distinct namespaces and meanings |
| Evidence/results | Worker evidence, framework result, benchmark evaluation | Preserve native schemas; adapters cannot upgrade authority |
| Resume/recovery | Worker lifecycle and benchmark hash-bound resume | Preserve independently; no cross-state transitions |
| Workspace handling | Worker receipts, framework containment, benchmark fixtures | Framework owns process containment; Worker accepts receipts; benchmark owns evaluation fixtures only |
| Provider abstraction | Framework Codex security and benchmark multi-provider clients | Preserve both behind separate authority boundaries |
| Planner/worker prompts | Worker curricula, framework execution prompt, benchmark templates | Worker defines roles; framework renders authorized work; benchmark evaluates candidates |
| GUI concepts | Disconnected benchmark experiment and historical framework concepts | Preserve experiment; defer product GUI boundary |
| Model routing | Benchmark comparison data and Worker policy | Benchmark recommends; Worker controller decides; framework executes exact profile |

## 6. ACCEPTED canonical boundaries from the Ultra review

The user accepted these five bounded design recommendations on 2026-08-30. They
remain non-executable until their milestone implementations and tests pass.

### U-01 — Fail-closed monorepo identity

Record source provenance separately from integration identity. The integration
identity binds monorepo commit/tree, canonical component prefix and subtree,
adapter blob path/digest, runtime identities, and a closed invocation-dependency
set. Tracked or untracked dirtiness inside either participating component or any
root/shared dependency capable of affecting invocation blocks execution.
Unreadable, undeclared, substituted, escaped, or stale state fails closed.
Unrelated documentation or benchmark-output dirtiness outside that declared set
does not block.

### U-02 — Planner/Task Creator/Worker direction

Planner output is untrusted. Worker Lab validates and selects the plan, assigns
permanent IDs, and authorizes bounded tasks. Task Creator converts only accepted
plans into independently actionable tasks without widening them. A fail-closed
adapter serializes the authorized record into the framework transport contract.
The framework executes without selecting or expanding the task. Worker Lab
independently verifies results and controls progression.

### U-03 — Evidence integration

Keep native schemas and directional adapters through M4. Do not introduce a
universal evidence-content schema. At M5, add only a controller-owned typed
evidence reference if integration tests demonstrate a need. It may identify
producer/schema, namespaced subject, digest/location, source and integration
identities, observation time, verification class, and bounded authority, but it
does not copy payloads or upgrade evidence.

### U-04 — Model-routing ownership

Worker Lab's trusted controller owns role-to-model/profile routing through M6.
Local Model Bench supplies reviewed recommendations. The framework validates and
executes only the exact authorized profile; it cannot choose, fall back, or
escalate automatically. Benchmark provider configuration remains local to the
benchmark. A separate orchestration component is deferred until post-M6 evidence
shows a shared need.

### U-05 — Import, provenance and rollback gates

Keep the order framework, Worker Lab, benchmark. Before M2, accept and commit M1,
resolve the H01 duplicate, create a clean ACL checkpoint, verify source refs or
record an explicit offline observation, create a checksummed recovery bundle for
the framework, preserve complete reachable ancestry, namespace imported tags,
and record private-only license treatment.

Prove an exact import in two layers: imported subtree/tree equality, then the
untouched suite from a disposable standalone reconstruction of the imported
tree. Run the in-monorepo suite separately to expose prefix-dependent failures
for the later adaptation commit. M2 adaptation may add prefix-aware validation
and identity primitives, but Worker dependency binding remains disabled and
incomplete until M3.

## 7. Exact source selection and exclusions

| Component | ACCEPTED source snapshot | Full-history method | Exclusions | Ready? |
|---|---|---|---|---|
| Framework | Commit/tree in section 2 | Permanent merge-parent or equivalent reachable non-squashed ancestry; namespaced tags; recovery bundle | `.git`, hooks/config, caches, temp/test residue | Source selectable; recovery/reverification gates and separate authorization block M2 |
| Worker Lab | Commit/tree in section 2 including all 9 local commits | Complete reachable ancestry; exact HEAD tree under stable prefix | Current deletions, Legacy/chat history, runtime/state/evidence/workspaces/caches | Source accepted; identity implementation and separate authorization block M3 |
| Local Model Bench | Commit/tree in section 2 | Complete reachable ancestry; exact tracked tree and MIT license | Raw ignored runs/logs/PIDs/`.venv`, models/installations, disposable workspaces | Source selectable; M4 evidence-selection decision remains |

The accepted component roots remain stable through M6:

- `components/autonomous-worker-framework/`
- `components/worker-lab/`
- `components/local-model-bench/`

## 8. License and distribution

- The combined repository remains private.
- Preserve Local Model Bench's MIT license and notices with the component.
- Worker Lab and the framework have no root license files. Their consolidation is
  private internal use only and grants no public redistribution authority.
- Any visibility or distribution change requires a separate ownership/license
  review.

## 9. Import, validation and rollback gates

| Milestone | Focused validation | Full validation | Security evidence | Rollback | Stop conditions |
|---|---|---|---|---|---|
| M2 exact framework import | Source/subtree and adapter digest equality | Untouched suite from disposable standalone reconstruction | Execution disabled; source/integration identities recorded | Accepted M1 checkpoint and framework source/bundle | Dirty ACL, identity/tree/history mismatch, missing recovery artifact, regression |
| M2 adaptation | Prefix/root/blob and quick-validator tests | In-monorepo framework suite | Substitution, prefix confusion, dirty dependency and stale provenance | M2 exact-import commit | Any weakened credential, sandbox, containment, custody or cleanliness boundary |
| M3 exact Worker import | Source/subtree equality; lifecycle/evidence import checks | Worker suite under Python 3.12 | Framework invocation remains disabled | Accepted M2 adaptation and Worker source identity | Ambiguous source state, history loss or regression |
| M3 identity adaptation | Component identity and adapter-binding tests | Worker plus framework contract suites | Dirty sibling, component drift, substitution and stale provenance | M3 exact-import commit | Authority expansion or identity/security regression |
| M4 benchmark import | Schema/config and selected-report digest checks | Unit discovery and config validation | Redaction and assessor separation; no execution authority | Accepted M3 checkpoint and benchmark identity | Raw runtime import, license loss, schema/resume regression |
| M5 documentation/contracts | Link/path/authority checks | `git diff --check` and documentation audit | One current authority definition per concern | M4 checkpoint | Contradictory active docs or rewritten history |
| M6 integration | Directional adapter tests | Synthetic read-only proof and recovery drill | External target, exact profile, unchanged authority | M5 and all source identities | Mutation, ambiguity, missing evidence or recovery failure |

Exact import and adaptation are always separate commits. Historical test counts
are evidence, not parity acceptance.

## 10. User decisions — accepted 2026-08-30

The user accepted D-01 through D-06 without revision and authorized the M1
checkpoint containing this reconciliation.

| ID | Question | Accepted choice | Alternatives | Consequence | Blocks M2? |
|---|---|---|---|---|---|
| D-01 | Accept stable component roots and complete reachable ancestry? | Accept the three `components/` roots through M6 and non-squashed history | Different roots or squashed history | Changing roots adds migration work; squashing weakens provenance/recovery | Yes |
| D-02 | Accept private-only treatment of unlicensed components? | Accept private internal consolidation; no public redistribution | Delay merger for licensing work | Delay blocks framework import | Yes |
| D-03 | Accept scoped fail-closed dependency cleanliness? | Bind both components plus a closed root/shared dependency set | Whole-monorepo clean or component-only clean | Whole-repo is overbroad; component-only can miss executable dependencies | Yes |
| D-04 | Accept directional contract and routing ownership through M6? | Worker owns acceptance/routing; framework executes; benchmark recommends | New orchestration layer or authority in framework/benchmark | Alternatives create premature or unsafe authority duplication | No for exact M2 import; required before adaptation/integration |
| D-05 | Which H01 copy becomes canonical? | Preserve and index the user-supplied `.txt`; do not track the malformed duplicate `.md` | Normalize a reviewed Markdown copy or retain both | Resolved in the M1 checkpoint | Yes |
| D-06 | How should Worker Lab's 9 local commits and 17 moved/deleted files be preserved? | Preserve full HEAD ancestry and exact HEAD tree; treat current deletions/Legacy copies as separately reviewed historical disposition | Publish first, commit deletions, or select another snapshot | Determines M3 source identity and recovery evidence | No for M2; yes for M3 |

## 11. M1 status

`ACCEPTED`. The commit containing this document is the clean M1 governance
checkpoint. M2 remains blocked until framework recovery evidence is created,
source identities are reverified at the M2 boundary, and the user separately
authorizes the bounded M2 operation.

Benchmark semantic review, Phi-4 retesting, production GUI design, exact
Terra/Sol attribution, and historical synthetic roots do not block M2.
