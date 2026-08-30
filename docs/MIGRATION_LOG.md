# Migration Log

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

Review still required:

- accept the exact Worker Lab local-ahead snapshot or first publish it;
- accept private-only treatment of the two unlicensed internal components;
- accept the stable component roots and history import method;
- accept execution-disabled identity migration as an M2/M3 requirement; and
- complete the benchmark run/evidence selection before M4.
