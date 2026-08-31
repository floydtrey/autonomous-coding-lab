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
