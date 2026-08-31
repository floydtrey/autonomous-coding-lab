# Local Model Bench M4 Recovery and Import Preflight

**Status:** Verified M4 recovery checkpoint
**Date:** 2026-08-31

## Selected source identity

- Source repository:
  `C:\Users\MineTrackerWorker\repos\awf-live-consumer-smoke\2026-08-29\referenced-chatgpt-conversation-this-is-an\outputs\local-model-bench`
- Branch/upstream: `main` / `origin/main`
- Source commit: `4a023c8230365c3098a6dff71fa9623cac059cdd`
- Source tree: `1b20a0e6a9e273532ed047ff3cb9f8c990f6fa01`
- Root commit: `ef3bf6a2ce7159a1124516183b8ebc8f088bf05e`
- Reachable commits: 7
- Remote relation: 0 ahead / 0 behind
- Object format: SHA-1; repository is not shallow
- Tracked worktree and index: clean
- Source refs: `HEAD`, `refs/heads/main`, and `refs/remotes/origin/main` all
  select the accepted commit; the source has no tags

The source remains read-only. Ignored raw benchmark runs, logs, PIDs, virtual
environments, model binaries, and local installations are excluded. The 59-file
tracked tree already contains the MIT license and selected compact reports.

## External recovery artifact

- Bundle:
  `C:\Users\MineTrackerWorker\backups\local-model-bench\local-model-bench-20260831-4a023c8-full.bundle`
- Size: 87,683 bytes
- SHA-256:
  `2A4A927E036E5BDB33E92A01C030F5A6611285DA67EE76D439280BAA478B94FB`
- Creation input: all source refs
- Classification: complete history

`git bundle verify` accepted the bundle as complete. A disposable bare mirror
created only from the bundle reproduced the selected commit, tree, seven-commit
history, root commit, and strict object verification. The bundle checksum was
unchanged after the drill; the disposable mirror was then removed.

## Exact import procedure

1. Fetch bundle `refs/heads/main` to
   `refs/remotes/m4-local-model-bench/main`.
2. Create an unrelated-history merge with the recovery checkpoint as first
   parent and the exact source commit as second parent.
3. Read the source tree unchanged beneath `components/local-model-bench/`.
4. Require the imported subtree to equal
   `1b20a0e6a9e273532ed047ff3cb9f8c990f6fa01` and its diff from the source tree
   to be empty.
5. Commit no path, configuration, evidence, dependency, or behavior adaptation
   with the import.

The exact import grants no model-selection, execution, routing, publication, or
component authority. The seven recorded machine-local path findings remain for
a separate adaptation commit.
