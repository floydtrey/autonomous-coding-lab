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
