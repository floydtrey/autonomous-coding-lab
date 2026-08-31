# Current State

**Last updated:** 2026-08-30
**Status:** M2 standalone parity complete; in-monorepo testing not authorized
**Canonical repository:** Merger governance plus exact framework bytes; component authority has not transferred

## Target repository

- Local path: `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`
- Remote: private `floydtrey/autonomous-coding-lab`
- Branch: `main`
- Source code imported: exact framework tree only at
  `components/autonomous-worker-framework/`
- Worker execution authority: none

## Preliminary source identities

| Source | Verified HEAD | Observed state | Remote |
|---|---|---|---|
| Worker Lab | `ca55e30ccbcbf2318d73b3ef8a65f66bb9e1e684` | `main` is 9 commits ahead; 17 unstaged tracked deletions; no ordinary untracked files; ignored/unreadable test residue | private GitHub remote |
| Autonomous Worker Framework | `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd` / `v0.2.6-worker-lab-final-message` | local `main`; unreadable test-temp directories; no remote | none |
| Local Model Bench | `4a023c8230365c3098a6dff71fa9623cac059cdd` | tracked tree clean and locally synchronized; native-JSON run completed in ignored local results | public GitHub remote recorded locally |

These are audit observations, not import approvals. All 17 Worker Lab deletions
have blob-equivalent copies under the separate Legacy history location. Their
working-tree disposition, unreadable directories, ignored results, and
historical material will not be cleaned, removed, or copied automatically.

## Existing boundary that must be preserved

The framework has proven bounded execution capabilities. Worker Lab owns
authority, lifecycle, curriculum, and evidence. Local Model Bench owns model and
prompt evaluation. Bringing them into one repository does not allow one
component to silently assume another component's authority.

## M1 findings

- The first integration layout is accepted as `components/worker-lab/`,
  `components/autonomous-worker-framework/`, and
  `components/local-model-bench/`. These paths remain stable through M6.
- Worker Lab and the framework have no detected Python imports between them.
  Their live interface is a versioned canonical-JSON subprocess protocol.
- Worker Lab pins the framework's standalone absolute path, standalone Git
  commit, and root-relative adapter blob path.
- The framework adapter independently assumes its component directory is the
  Git repository root and requires the entire repository to be clean.
- Those identity checks cannot be weakened or patched casually. Live execution
  remains disabled after import until a reviewed monorepo identity contract
  provides component-scoped paths, source provenance, blob identity, and scoped
  cleanliness evidence.
- Worker Lab requires Python 3.12. Local Model Bench requires Python 3.10 or
  newer. The framework has no package metadata and is validated as root-relative
  tools. Each component therefore keeps its own environment and commands during
  migration.
- Worker Lab and the framework have no license file. Their consolidation is
  authorized only inside this private repository; public redistribution remains
  undecided. Local Model Bench's MIT license must remain with that component.
- Benchmark profiles contain two machine-local llama.cpp/model paths. They are
  configuration, not portable defaults, and require later local-configuration
  treatment without importing the model binaries.
- Local Model Bench's native-JSON Qwen 14B run completed 18/18 with a mechanical
  score of 93.33% and zero hard failures. It remains ignored local evidence;
  semantic role fitness and model selection are still unknown.
- Worker Lab contains execution-capable synthetic read-only source, but active
  ACL authority still disables execution. Capability does not transfer
  authority.
- `docs/handoffs/H01-Handoff.txt` is the accepted canonical H01 witness. The
  malformed one-character-different `.md` duplicate was excluded from the
  checkpoint after its difference was recorded.
- The accepted fail-closed monorepo identity binds source provenance separately
  from monorepo integration identity and scopes cleanliness to both participating
  components plus a closed root/shared invocation dependency set.
- Planner and Task Creator outputs remain untrusted until Worker Lab accepts and
  authorizes them. Framework execution and benchmark evaluation remain
  directional downstream boundaries.

## Next boundary

The framework source identity, complete reachable ancestry, annotated tags, and
external recovery bundle are verified in `FRAMEWORK_M2_RECOVERY.md`. The bundle
SHA-256 is
`5D14E8D34DA523C9719646CEB437833C4D9D56E31407D8C5BF2122BC7789779B`.

M2-B exact import commit
`d1c95814bce512318c61a5745dcd684d87e3676a` has first parent M2-A checkpoint
`bbc2e831328c841ae204e4fd6064202a18d3ee5d`, second parent framework source
`3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`, and exact imported subtree
`35ecad05e60c664324a4f30d42a4f6b198181074`. No imported file was adapted.

Untouched standalone parity passed from a disposable reconstruction whose Git
tree exactly matched `35ecad05e60c664324a4f30d42a4f6b198181074`:
Python 3.12.10 compiled the framework and pytest 9.1.1 passed all 163 tests. The
first test attempt was environment-invalid because pytest could not access its
pre-existing default Windows temp directory; the unchanged documented command
passed after `TEMP` and `TMP` were directed to a fresh disposable directory.

No framework test has run from its prefixed monorepo location. That separately
authorized exposure run is the next gate. Path adaptation, component authority
transfer, and all worker/model execution remain disabled.
