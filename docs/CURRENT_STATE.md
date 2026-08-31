# Current State

**Last updated:** 2026-08-31
**Status:** M3 exact import and repaired standalone parity complete; cross-component adaptation pending
**Canonical repository:** Merger governance plus exact framework and Worker Lab bytes; component authority has not transferred

## Target repository

- Local path: `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`
- Remote: private `floydtrey/autonomous-coding-lab`
- Branch: `main`
- Source code imported: exact framework tree at
  `components/autonomous-worker-framework/` and exact Worker Lab tree at
  `components/worker-lab/`
- Worker execution authority: none

## Preliminary source identities

| Source | Verified HEAD | Observed state | Remote |
|---|---|---|---|
| Worker Lab | `fddf0726b975a8192d5e126f109e6fc756f11b36` | `main` is 10 commits ahead; tracked worktree and index clean; ignored/unreadable test residue remains excluded | private GitHub remote |
| Autonomous Worker Framework | `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd` / `v0.2.6-worker-lab-final-message` | local `main`; unreadable test-temp directories; no remote | none |
| Local Model Bench | `4a023c8230365c3098a6dff71fa9623cac059cdd` | tracked tree clean and locally synchronized; native-JSON run completed in ignored local results | public GitHub remote recorded locally |

These are audit observations, not import approvals. The user classified all 17
obsolete Worker Lab `TERRA*.md` instruction/report files for removal, and Worker
Lab commit `fddf0726b975a8192d5e126f109e6fc756f11b36` records their deletion plus
three active-reference repairs. Legacy copies, unreadable directories, ignored
results, and other historical material remain excluded from automatic import.

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

The unchanged full validator also passed from the prefixed component root: Python
compilation passed and all 163 tests passed. A focused quick-validation probe
against base `bbc2e831328c841ae204e4fd6064202a18d3ee5d` discovered 46 changed
paths, including 38 framework paths carrying the monorepo prefix, but selected
zero stages and returned success. This proves P-008: `_existing_files` and the
changed-test selector expect component-relative paths.

The deterministic Git-tree inventory under `migration/inventory/` now binds all
165 tracked files across the three selected source snapshots to their blobs,
destination paths, extracted structures, and typed path references. It records
15 cross-component connections, one mechanical failure (P-008), 11 known
semantic/runtime gaps, and no unknown parser failures. A repeat generation was
byte-for-byte identical. The guarded repair plan names only
`tools/local_validate.py` and its focused test file.

P-008 was repaired in commit
`8985ff205b756a843fbfcce3ff61ea5f1638273a`. The quick selector now translates
monorepo-root Git paths to component-relative paths, ignores paths outside the
framework component, and fails closed if the component is outside Git's reported
root. Nine focused tests passed, the full framework passed all 165 tests, and a
fresh regeneration changed none of the eight immutable source-baseline JSON
artifacts. `migration/inventory/resolutions.json` binds the exact repaired blobs
and evidence without rewriting the source finding.

M2-S1 commit `6622c24ade7e08a66aa62d23837aad11ff08e0a4`
introduced a canonical framework-only identity policy and strict parser. The
policy separates immutable source provenance from future dynamic integration
identity, declares the whole framework component plus its policy file as the M2
dependency closure, keeps Worker Lab deferred, and cannot grant execution.

M2-S2 commit `57a298562de274cd4f989a2a5741861a5a5b56a8`
added an unwired Git-backed verifier. Against that exact clean commit it bound
the source/import/current trees, canonical framework prefix, committed and
worktree adapter bytes, policy blob, and scoped tracked/untracked cleanliness.
The resulting identity digest is
`sha256:98dcf445573f11c7ea004cfd8ab2ecf9fcb7805769cdb41e33f7fb593de0a205`.
Thirty-two focused tests and all 197 framework tests passed.

The v1 adapter protocol and CLI were not changed and do not consume the new
verifier. Execution remains disabled.

Worker Lab M3-A recovery and source-identity preflight are verified in
`WORKER_LAB_M3_RECOVERY.md`. The accepted local-ahead tip is
`fddf0726b975a8192d5e126f109e6fc756f11b36`, its tree is
`5fe9e3f153b48543a57f3b9d1e339b3cd875930a`, and its complete 44-commit
reachable history plus refs can be reconstructed from the external bundle with
SHA-256
`74445D0BAC13B4EC24B2036E6BB66927D3E5136DC3F206A2BB5019B023899F36`.

M3-B exact-import commit
`057f6500585d6e692ad5330d6738bd5c08d13cc5` has first parent M3-A checkpoint
`c4b85219a5082226ec9eae82e74c6d60cb84d6af`, second parent Worker Lab source
`fddf0726b975a8192d5e126f109e6fc756f11b36`, and exact imported subtree
`5fe9e3f153b48543a57f3b9d1e339b3cd875930a`. Its first-parent change set is
exactly 68 additions below `components/worker-lab/`; no imported byte was
adapted.

Untouched standalone parity reconstructed the exact source commit/tree and ran
the immutable T020 command under Python 3.12.10 and pytest 9.1.1. After one
environment-invalid long-path attempt, the valid short-temp run produced 317
passes, seven expected Windows symlink skips, and 12 failures. All 12 failures
come from older workflows/fixtures omitting the runtime identity now required
for active attempt states. Exact evidence and failure groups are recorded in
`WORKER_LAB_M3_RECOVERY.md` section 9.

Bounded repair commit `a7bbd4e9074d1e4be64f01e74b4471abee0fd95d`
changed only the four stale test files and preserved the fail-closed production
runtime-identity invariant. The tested standalone candidate tree and committed
Worker subtree both equal `2c12c6ab1b18c9fef96fdaad82b6a40270e9ca16`.
Focused validation passed 104 tests with five expected Windows symlink skips;
the single T020 run passed 329 tests with seven expected skips.

Standalone parity is complete. Coordinated Worker/framework identity adaptation
to address P-006, complete bilateral P-007, and wire a new protocol remains a
separately authorized gate. No worker/model execution, cross-component
adaptation, push, or publication is authorized by this checkpoint.
