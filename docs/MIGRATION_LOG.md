# Migration Log

Each entry records what was known at that stage. Later dated entries supersede
earlier open findings when new evidence resolves or changes them.

## 2026-08-30 — M0 foundation

- Selected working title and repository name: `autonomous-coding-lab`.
- Confirmed the local and GitHub target names were unused.
- Read source repository instructions and routing documents.
- Recorded preliminary source HEADs and working-tree observations.
- Created a draft merger contract, source inventory, path ledger, milestones,
  and current-state document.
- Copied no source code and changed no source repository.

Open findings:

- Worker Lab is nine commits ahead of its private remote.
- Worker Lab has an untracked conversation-history file that is excluded pending
  classification.
- Worker Lab and the framework have unreadable test-temporary directories that
  are excluded and will not be cleaned as part of migration.
- The framework's active separate-repository decisions require explicit internal
  boundary replacements before import.
- The active Local Model Bench run must finish before evidence selection.

## 2026-08-30 — M1 audit draft

- Counted exact tracked trees and histories for all three sources.
- Recorded package layouts, Python requirements, entry points, licenses, tags,
  remotes, working-tree exclusions, and original parity commands.
- Confirmed Worker Lab and the framework communicate through a subprocess JSON
  protocol rather than direct Python imports.
- Located the standalone identity assumptions that prevent safe live execution
  immediately after prefix import.
- Proposed stable `components/<source-name>/` roots through M6 and complete,
  non-squashed ancestry imports from exact local commits.
- Kept source repositories unchanged and copied no source code.

Review still required at that draft stage:

- accept the exact Worker Lab local-ahead snapshot or first publish it;
- accept private-only treatment of the two unlicensed internal components;
- accept the stable component roots and history import method;
- accept execution-disabled identity migration as an M2/M3 requirement; and
- complete semantic evidence selection for the now-completed benchmark run
  before M4.

## 2026-08-30 — M1 handoff reconciliation draft

- Inventoried H01 and H03 as witness reports and classified material claims
  against current Git/filesystem evidence.
- Reverified ACL, Worker Lab, framework, and Local Model Bench commit/tree and
  working-tree identities without a network fetch.
- Confirmed Worker Lab's 17 tracked deletions have blob-equivalent Legacy copies
  and that its nine local commits remain ahead of the private remote.
- Recorded the completed 18/18 native-JSON benchmark result while preserving its
  semantic-review and authority limits.
- Produced the repository/component, conflict, duplication, source/provenance,
  validation/rollback, and user-decision matrices in
  `handoffs/CONSOLIDATION_RECONCILIATION.md`.
- Added proposed boundaries for scoped fail-closed integration identity,
  directional task/evidence flow, Worker-owned routing, and dual-layer import
  parity/recovery.
- At that draft stage, kept both untracked H01 variants untouched and proposed
  the user-supplied `.txt` as canonical pending approval.
- Modified no source repository, imported no component source, ran no workers or
  models, and granted no execution authority.

Resolution and next gates:

- D-01 through D-06 were accepted by the user on 2026-08-30;
- record the accepted governance as a clean checkpoint;
- create and checksum the framework recovery artifact; and
- reverify source identities at the M2 boundary.

## 2026-08-30 — M1 decisions accepted and checkpoint authorized

- Recorded user acceptance of reconciliation decisions D-01 through D-06.
- Activated durable decisions for stable component paths, non-squashed history,
  private-only unlicensed components, scoped fail-closed identity, directional
  task/evidence authority, Worker-owned routing, exact-import validation, the
  canonical H01 witness, and the Worker Lab source snapshot.
- Added the unchanged user-supplied `handoffs/H01-Handoff.txt` as canonical and
  removed the malformed untracked `.md` duplicate after its one-character
  difference and hashes had been recorded.
- Kept source import and execution disabled. M2 requires separate authorization
  after framework recovery and source-reverification prerequisites pass.
- The commit containing this entry is the accepted M1 governance checkpoint.

## 2026-08-30 — M2-A framework recovery and identity preflight

- Reverified the no-remote framework at commit
  `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`, tree
  `35ecad05e60c664324a4f30d42a4f6b198181074`, and final annotated tag.
- Confirmed a clean working tree, 33 reachable commits, one root, three branch
  refs whose tips are all in `main`, eight annotated tags, and no object
  alternates or shallow boundary.
- Created the external complete-history bundle recorded in
  `FRAMEWORK_M2_RECOVERY.md` and bound it to SHA-256
  `5D14E8D34DA523C9719646CEB437833C4D9D56E31407D8C5BF2122BC7789779B`.
- Reconstructed a temporary bare mirror, proved exact ref/commit/tree/ancestry
  equality, passed strict object verification, and removed only that temporary
  verification repository.
- Recorded the exact namespaced-tag mapping and a native Git merge-parent plus
  prefixed-tree import procedure because the installed `git subtree` helper is
  broken.
- Imported no component source, ran no framework tests/workers/models, enabled
  no execution, changed no source repository, and performed no fetch or push.
- M2-B exact import is ready for separate user authorization naming the M2-A
  checkpoint.

## 2026-08-30 — M2-B exact framework import

- Reverified clean ACL checkpoint
  `bbc2e831328c841ae204e4fd6064202a18d3ee5d`, clean framework source commit
  `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`, source tree
  `35ecad05e60c664324a4f30d42a4f6b198181074`, and recovery SHA-256 before
  mutation.
- Fetched three source branch refs into
  `refs/remotes/m2-autonomous-worker-framework/*` and preserved all eight
  annotated tag objects under `refs/tags/autonomous-worker-framework/*`.
- Created exact-import commit
  `d1c95814bce512318c61a5745dcd684d87e3676a` with the M2-A checkpoint as first
  parent and the exact framework source tip as second parent.
- Proved the imported subtree equals the source tree, the first-parent change set
  is exactly 38 prefixed additions, the tree-to-subtree diff is empty, and the
  source tip is reachable through the merge parent.
- Proved the imported adapter Git blob and SHA-256 exactly equal the source.
- Left source and ACL worktrees clean. Changed no source repository and performed
  no network fetch or push.
- Ran no framework test or command, enabled no execution, and made no path,
  behavior, dependency, identity, or security adaptation.
- Untouched standalone parity is the next separately authorized gate.

## 2026-08-30 — M2 untouched standalone framework parity

- Reconstructed a disposable independent Git repository only from the imported
  framework subtree at exact-import commit
  `d1c95814bce512318c61a5745dcd684d87e3676a`.
- Proved its Git tree exactly matched accepted source/import tree
  `35ecad05e60c664324a4f30d42a4f6b198181074` before testing.
- Used Python 3.12.10 and pytest 9.1.1 with the documented full-validation
  command. Compile passed and all 163 tests passed.
- Classified the first test attempt as environment-invalid: pytest could not
  access its pre-existing default Windows temp directory, causing 74 setup
  errors after 89 passes. The unchanged command passed after directing `TEMP`
  and `TMP` to a fresh disposable directory.
- Confirmed the reconstruction had no tracked or non-ignored untracked changes;
  only disposable ignored test artifacts existed. The ACL and source
  repositories remained clean. Ran no worker or model, changed no imported
  component file, and performed no network operation or push.
- In-monorepo prefix testing is the next separately authorized gate. Adaptation,
  component-authority transfer, and execution remain disabled.

## 2026-08-30 — M2 in-monorepo framework exposure

- Ran the unchanged documented full validator from the prefixed framework
  component root. Compilation passed and all 163 tests passed.
- Classified the first compile attempt as environment-invalid because the
  restricted sandbox could not create ignored Python caches. The unchanged
  command passed after granting cache-write access.
- Ran the focused quick validator against pre-import base
  `bbc2e831328c841ae204e4fd6064202a18d3ee5d`. It discovered 46 changed paths but
  selected zero stages and returned success.
- Confirmed the cause is P-008 path handling: framework paths retain the
  `components/autonomous-worker-framework/` Git prefix, while `_existing_files`
  and changed-test selection expect component-relative paths.
- Removed only generated ignored caches and the dedicated pytest temp directory.
  ACL and source repositories remained clean; no imported code was changed, no
  worker or model ran, and no network operation or push occurred.
- P-008 repair with focused regression tests is the next separately authorized
  gate. All other adaptation and execution remain disabled.

## 2026-08-30 — Worker Lab obsolete-handoff disposition

- The user classified the 17 deleted root `TERRA*.md` files as obsolete AI
  instruction, handoff, and chat-report material that must not remain active.
- Worker Lab commit `fddf0726b975a8192d5e126f109e6fc756f11b36`
  records exactly those 17 deletions and repairs three active references to the
  deleted adapter handoff; no code changed and no push occurred.
- The finalized current tree is
  `5fe9e3f153b48543a57f3b9d1e339b3cd875930a`: 68 tracked files, 634,920 bytes,
  and 44 commits in HEAD history. `main` is 10 ahead of `origin/main`.
- Complete ancestry preserves the removed historical blobs, while the selected
  current tree and structural inventory exclude them. Legacy copies, ignored
  runtime data, and unreadable test residue remain excluded.

## 2026-08-30 — Deterministic structural baseline

- Added standard-library Git-tree inventory, query, and guarded repair-planning
  tools. They read exact committed blobs and do not execute component code.
- Bound 38 framework, 68 Worker Lab, and 59 Model Bench files to stable IDs,
  source/destination paths, Git blobs, SHA-256 digests, languages, roles,
  extracted code structures, and typed path references.
- Verified the imported framework subtree still equals its accepted source tree.
- Recorded 15 cross-component connections, one mechanical failure
  (`AWF-PATH-008`), 11 known semantic/runtime gaps, and zero unknown parser
  failures. `worker-lab-gui-lab` is explicitly excluded as an experimental
  proving repository.
- Generated a one-change guarded repair plan for P-008. It records the starting
  blob and names only the framework validator and its focused test file; it
  grants no automatic edit or commit authority.
- Four focused analyzer/planner tests passed. A complete repeat generation
  produced byte-for-byte identical JSON outputs.

## 2026-08-30 — Guarded P-008 repair

- Commit `8985ff205b756a843fbfcce3ff61ea5f1638273a` changed only the framework
  quick validator and its focused tests.
- The selector now strips the exact framework component prefix from Git paths,
  excludes root and sibling-component changes, preserves standalone behavior,
  and fails closed when the framework root is outside Git's reported root.
- A live selection probe against base `bbc2e831328c841ae204e4fd6064202a18d3ee5d`
  returned 38 component-relative paths, zero monorepo-prefixed paths, 13 tests,
  and both required stages.
- Nine focused validator tests passed. The documented full validator then passed
  compilation and all 165 tests under Python 3.12.10.
- All eight source-snapshot JSON artifacts regenerated byte-for-byte unchanged.
  The original source finding remains provenance; `resolutions.json` records the
  exact repaired integration blobs, commit, tree, and validation evidence.

## 2026-08-30 — M2 framework-only identity adaptation

- M2-S1 commit `6622c24ade7e08a66aa62d23837aad11ff08e0a4` added
  `config/monorepo-identity.json`, a strict framework-owned parser, and focused
  negative tests. The canonical policy binds source provenance separately from
  dynamic integration identity, declares a closed M2 dependency set, defers
  Worker Lab, and requires execution authority to remain disabled.
- M2-S2 commit `57a298562de274cd4f989a2a5741861a5a5b56a8` added an
  unwired verifier for exact Git root, component prefix, source/import/current
  trees, adapter and policy blobs/worktree bytes, linked-path rejection, and
  scoped tracked/untracked cleanliness.
- The verifier passed against the exact clean M2-S2 commit and produced identity
  digest
  `sha256:98dcf445573f11c7ea004cfd8ab2ecf9fcb7805769cdb41e33f7fb593de0a205`.
  Exact machine-readable evidence is in
  `migration/inventory/framework-m2-identity-evidence.json`.
- M2-S1 focused validation passed 21 tests; the expanded M2-S2 focused suite
  passed 32 tests; the final documented framework validator passed compilation
  and all 197 tests.
- The adapter v1 schema, `local_runtime_identity`, CLI modes, and execution path
  were not modified. P-006 and bilateral P-007 remain blocked on M3 exact Worker
  Lab import and coordinated contract adaptation.

## 2026-08-31 — M3-A Worker Lab recovery and source-identity preflight

- Reverified clean ACL checkpoint
  `fe5182fceb4eef2a94df15977903421feee00c82` and Worker Lab source tip
  `fddf0726b975a8192d5e126f109e6fc756f11b36` with tree
  `5fe9e3f153b48543a57f3b9d1e339b3cd875930a`.
- Confirmed the selected Worker Lab snapshot is 10 commits ahead and 0 behind
  `origin/main`, has 68 tracked files, and has 44 commits in complete reachable
  history. All nine local heads and four annotated tag targets are ancestors of
  accepted `main`.
- Created the complete external recovery bundle
  `C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-20260831-fddf0726-full.bundle`
  with SHA-256
  `74445D0BAC13B4EC24B2036E6BB66927D3E5136DC3F206A2BB5019B023899F36`.
- Independently reconstructed a temporary bare mirror from only the bundle;
  all 21 refs, selected commit/tree, 44 commits, 392 object-list lines, single
  root, strict object verification, and checksum matched.
- Recorded the namespaced tag map and exact native-Git, non-squashed M3-B import
  procedure. Source remote-tracking refs remain recovery evidence rather than
  permanent monorepo refs.
- Corrected the stale Worker inventory sentence: the accepted current tree
  excludes the 17 obsolete handoff files while complete history preserves their
  prior blobs.
- Ran no tests because M3-A changed no component code. Imported nothing, enabled
  no execution or component authority, changed no source repository, and made
  no network operation or push.

## 2026-08-31 — M3-B exact Worker Lab import

- Reverified the user-named M3-A checkpoint
  `c4b85219a5082226ec9eae82e74c6d60cb84d6af`, the clean source identity, the
  complete bundle, its checksum, and absent destination/ref namespaces before
  any mutation.
- Fetched all nine source heads under `refs/remotes/m3-worker-lab/*` and all four
  annotated tag objects under `refs/tags/worker-lab/*`; every object ID matched
  the source. Source `refs/remotes/origin/*` remained bundle-only evidence.
- Created pure exact-import commit
  `057f6500585d6e692ad5330d6738bd5c08d13cc5` with the M3-A checkpoint as first
  parent and accepted Worker Lab tip
  `fddf0726b975a8192d5e126f109e6fc756f11b36` as second parent.
- Proved `components/worker-lab/` equals source tree
  `5fe9e3f153b48543a57f3b9d1e339b3cd875930a`, the tree-to-subtree diff is
  empty, and the first-parent change set is exactly 68 prefix-contained
  additions.
- Reverified source-tip ancestry, namespaced refs/tags, clean ACL and source
  worktrees, unchanged source HEAD/tree, and unchanged bundle checksum.
- Ran no test, Worker Lab command, worker, model, or adapter. Made no adaptation,
  authority transfer, network operation, or push. Untouched disposable
  standalone parity is the next separately authorized gate.

## 2026-08-31 — M3 untouched standalone Worker Lab parity failure

- Reconstructed an independent disposable repository from ACL's imported Worker
  ref at exact source HEAD `fddf0726b975a8192d5e126f109e6fc756f11b36`
  and tree `5fe9e3f153b48543a57f3b9d1e339b3cd875930a`; it had 44 reachable commits, 68
  tracked files, and a clean pre-test status.
- Ran immutable T020 command `python -m pytest -q` with Python 3.12.10 and pytest
  9.1.1. The first attempt was environment-invalid because a 263-character
  nested fixture path caused Git `Filename too long` errors; it is not parity
  evidence.
- Retried the unchanged command once with a short disposable temp root. The valid
  run completed in 164.20 seconds: 317 passed, seven expected Windows symlink
  skips, and 12 failed.
- Classified all 12 valid failures under one source-snapshot inconsistency:
  production requires runtime identity for active attempt records/transitions,
  while one CLI workflow, nine evidence cases, one validation graph, and one
  workspace-receipt case still omit it.
- Confirmed this is neither a prefix failure nor an import-byte mismatch. The
  exact import is unchanged; parity is not complete.
- Removed both disposable repositories, the short temp tree, and all generated
  test artifacts after exact containment checks. Changed no component source or
  test, ran no worker/model/adapter, enabled no execution, and performed no push.

## 2026-08-31 — Bounded Worker Lab standalone parity repair

- Began from failed-parity checkpoint
  `d373848b0b73539ff86145629b2f2db930b897d5` and changed only the four test
  files responsible for the 12 runtime-identity failures.
- Added valid runtime identity to active evidence/validation fixtures and the
  workspace test transition. Updated the legacy CLI workflow to assert the
  generic CLI rejects an unbound `RUNNING` transition before using its existing
  test-only store/lifecycle seam.
- Changed no production code and did not weaken the fail-closed
  `runtime_identity` requirement.
- Reproduced the exact four-file patch in a clean standalone repository derived
  from ACL's imported Worker ref. The tested candidate tree was
  `2c12c6ab1b18c9fef96fdaad82b6a40270e9ca16`.
- Focused validation passed 104 tests with five expected Windows symlink skips
  in 142.08 seconds. The single unchanged T020 run then passed 329 tests with
  seven expected skips in 164.80 seconds.
- Created repair commit `a7bbd4e9074d1e4be64f01e74b4471abee0fd95d`;
  its Worker subtree exactly matches the tested candidate tree and its diff is
  limited to the four authorized test paths.
- Removed the disposable repository, temporary patch, pytest caches, and short
  temp trees. ACL and source repositories remained clean. Ran no worker, model,
  adapter, production execution, cross-component adaptation, network operation,
  or push.
