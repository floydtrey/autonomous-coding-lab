# Framework M2 Recovery and Exact-Import Preflight

**Status:** VERIFIED — exact import, standalone parity, and prefix exposure complete
**Observed:** 2026-08-30
**Execution authority:** Disabled
**Component import performed:** Yes — exact tracked source tree only

This record binds the accepted framework source identity to an independently
verified offline recovery artifact and records the executed exact-import
procedure. No framework test, path adaptation, or execution occurred.

## 1. ACL checkpoint basis

- Repository: `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`
- Accepted M1 checkpoint:
  `e853cb3b2fe1a7c84399a590b46faa2f1bd12a1d`
- M1 tree: `a87a46ddc40468f3b38b59d2df035dd96a33fd25`
- Branch: `main`
- Object format: SHA-1, matching the framework source
- Working tree at M2-A start: clean
- Remote relation at M2-A start: one local commit ahead of `origin/main`
- Network fetch/push: not performed

The commit containing this record is the M2-A checkpoint. A future M2-B
authorization must name that exact commit before any import command runs.

## 2. Reverified framework identity

- Source: `C:\Users\MineTrackerWorker\repos\autonomous-worker-framework`
- Branch: `main`
- HEAD: `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`
- Tree: `35ecad05e60c664324a4f30d42a4f6b198181074`
- Parent: `0f6423f848f50d0b5e9f3de6f79bbf4a94c74b49`
- Final tag: `v0.2.6-worker-lab-final-message`
- Final tag object: `d6e246290c4331494e2e9ad4304c0eb24183e91b`
- Final tag peeled commit/tree: the HEAD and tree above
- Working tree: clean, including ordinary untracked-file reporting
- Remote/upstream: none
- Shallow repository: no
- Object format: SHA-1
- Tracked HEAD tree: 38 files / 288,791 bytes
- Reachable commits across all refs: 33
- Reachable object-list lines: 230
- Root commit: `1592194f66d88e017a1be921a0ba2bbb436eb89b`
- Alternate object database: none

`git fsck --full --strict --no-reflogs` completed successfully. It reported two
dangling commits (`82e50ec6e0738ec0d1c5965c9335dadd8d19581f` and
`e8e940022909c26bc2628d23a926fe7a908bcf0c`) and one dangling blob
(`3ef1fe1f369333d16ed6cd8fd68bbb765eb2a517`). They are not reachable from any
source ref and are intentionally outside the accepted complete-reachable-history
scope.

## 3. Source refs preserved by the bundle

All three branch tips are within the 33-commit `main` ancestry. The two `chore/`
tips therefore add no otherwise-unreachable commits.

| Source ref | Object | Classification |
|---|---|---|
| `refs/heads/main` | `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd` | Accepted import tip |
| `refs/heads/chore/framework-local-validation` | `6bef5302839cff0c7a9384225a1cd2619c8b79ad` | Ancestor of `main` |
| `refs/heads/chore/local-worker-harness-v1` | `d83854f8eb1b365a93b431c007286a12ed9d6366` | Ancestor of `main` |
| `refs/tags/v0.1.0-foundation` | `ccdb161fe4798054344baf1bbb038d8f5733ba2a` | Annotated tag |
| `refs/tags/v0.2.0-worker-lab-adapter` | `1362fa2e0c4d13e479fd4cddffd523da82f1decb` | Annotated tag |
| `refs/tags/v0.2.1-worker-lab-readonly` | `cf2ee18c55d3cc73087b048704d846f42c146d37` | Annotated tag |
| `refs/tags/v0.2.2-worker-lab-sandbox-identity` | `7ac330e30d002cff3189e5ce26523eabd289f33a` | Annotated tag |
| `refs/tags/v0.2.3-worker-lab-isolated-adapter` | `e377f3f63978d30b31ee0ee16a60c121a4355a5d` | Annotated tag |
| `refs/tags/v0.2.4-worker-lab-preflight-codes` | `2f9889c8a731030ce63bd0bf50d81a376e4958bc` | Annotated tag |
| `refs/tags/v0.2.5-worker-lab-verified-launcher` | `83b3ceba8399c77a597e840506723df88e43b3f0` | Annotated tag |
| `refs/tags/v0.2.6-worker-lab-final-message` | `d6e246290c4331494e2e9ad4304c0eb24183e91b` | Annotated tag; peels to accepted tip |

## 4. Accepted recovery artifact

- Path:
  `C:\Users\MineTrackerWorker\backups\autonomous-worker-framework\autonomous-worker-framework-20260830-3b03802-full.bundle`
- Size: 116,218 bytes
- SHA-256:
  `5D14E8D34DA523C9719646CEB437833C4D9D56E31407D8C5BF2122BC7789779B`
- Bundle creation input: `--all` from the clean source repository
- Advertised refs: three heads, eight annotated tags, and `HEAD`
- Bundle classification: complete history, SHA-1 object format

The older bundle named `autonomous-worker-framework-20260827-d83854f.bundle`
is historical, not the M2 recovery artifact. It advertises an earlier `HEAD` at
`d83854f8eb1b365a93b431c007286a12ed9d6366`, an earlier `main` at
`6bef5302839cff0c7a9384225a1cd2619c8b79ad`, and no current milestone tags.

## 5. Recovery verification

The following checks passed:

1. `git bundle verify` reported the artifact as complete and valid.
2. The SHA-256 was identical before and after the recovery drill.
3. A unique temporary bare mirror was cloned from the bundle without a source
   checkout.
4. Every recovered `refs/heads/*` and `refs/tags/*` object ID exactly matched the
   source.
5. Recovered `main`, final tag, commit, and tree matched the accepted identity.
6. The recovered mirror contained 33 reachable commits, 230 reachable
   object-list lines, and the same single root commit.
7. Strict object verification passed in the recovered mirror.
8. The temporary mirror was removed after its absolute path was verified to be
   the uniquely created task directory under the system temporary directory.

No framework file was checked out, executed, modified, imported, or tested.

## 6. Permanent tag namespace for M2-B

M2-B must fetch each source tag object directly into a namespaced tag ref. This
preserves the annotated tag objects byte-for-byte while preventing collisions.

| Source tag | Monorepo tag ref |
|---|---|
| `v0.1.0-foundation` | `autonomous-worker-framework/v0.1.0-foundation` |
| `v0.2.0-worker-lab-adapter` | `autonomous-worker-framework/v0.2.0-worker-lab-adapter` |
| `v0.2.1-worker-lab-readonly` | `autonomous-worker-framework/v0.2.1-worker-lab-readonly` |
| `v0.2.2-worker-lab-sandbox-identity` | `autonomous-worker-framework/v0.2.2-worker-lab-sandbox-identity` |
| `v0.2.3-worker-lab-isolated-adapter` | `autonomous-worker-framework/v0.2.3-worker-lab-isolated-adapter` |
| `v0.2.4-worker-lab-preflight-codes` | `autonomous-worker-framework/v0.2.4-worker-lab-preflight-codes` |
| `v0.2.5-worker-lab-verified-launcher` | `autonomous-worker-framework/v0.2.5-worker-lab-verified-launcher` |
| `v0.2.6-worker-lab-final-message` | `autonomous-worker-framework/v0.2.6-worker-lab-final-message` |

The source heads are fetched temporarily under
`refs/remotes/m2-autonomous-worker-framework/*`. Their exact identities remain
durable in this record and the recovery bundle. Complete ancestry remains
reachable from the exact-import commit's second parent.

## 7. Exact non-squashed M2-B procedure — executed

The installed `git subtree` helper exits 126 and reports itself broken even
though its script exists, so M2-B did not depend on it. The executed equivalent
used a native Git merge parent plus a prefixed `read-tree`. It created one exact
import commit whose first parent is the M2-A checkpoint and whose second parent
is the accepted framework source tip.

### 7.1 Preconditions

Before running any mutating command, the separately authorized M2-B task must:

1. receive the exact M2-A checkpoint hash from the user;
2. require `main` and an empty status;
3. recheck the bundle SHA-256 shown above;
4. re-run `git bundle verify`;
5. require the destination path and both import namespaces to be absent;
6. require both repositories to use SHA-1 object format;
7. require source HEAD/tree/tag identities to equal sections 2 and 3; and
8. keep execution disabled.

### 7.2 Ref fetch

The following ref fetch ran from the ACL repository using the exact bundle path:

```powershell
$aclRepo = 'C:\Users\MineTrackerWorker\repos\autonomous-coding-lab'
$bundle = 'C:\Users\MineTrackerWorker\backups\autonomous-worker-framework\autonomous-worker-framework-20260830-3b03802-full.bundle'

git -C $aclRepo fetch --no-tags $bundle `
  '+refs/heads/*:refs/remotes/m2-autonomous-worker-framework/*' `
  '+refs/tags/*:refs/tags/autonomous-worker-framework/*'
```

After the fetch, compare all fetched objects with sections 2 and 3. Any missing,
extra, or mismatched ref stops M2-B before tree changes.

### 7.3 Exact prefixed merge-parent import

The exact M2-A checkpoint was reverified immediately before the import:

```powershell
$expectedBase = 'bbc2e831328c841ae204e4fd6064202a18d3ee5d'
$sourceRef = 'refs/remotes/m2-autonomous-worker-framework/main'
$sourceCommit = '3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd'
$sourceTree = '35ecad05e60c664324a4f30d42a4f6b198181074'
$prefix = 'components/autonomous-worker-framework'

if ((git -C $aclRepo rev-parse HEAD) -ne $expectedBase) { throw 'M2-A checkpoint mismatch' }
if (git -C $aclRepo status --porcelain) { throw 'ACL working tree is not clean' }
if ((git -C $aclRepo rev-parse $sourceRef) -ne $sourceCommit) { throw 'Source commit mismatch' }
if ((git -C $aclRepo rev-parse "$sourceRef`^{tree}") -ne $sourceTree) { throw 'Source tree mismatch' }
if (Test-Path -LiteralPath (Join-Path $aclRepo $prefix)) { throw 'Destination already exists' }

git -C $aclRepo merge --no-ff --no-commit --allow-unrelated-histories -s ours $sourceRef
if ($LASTEXITCODE -ne 0) { throw 'History-parent merge preparation failed' }

git -C $aclRepo read-tree --prefix="$prefix/" -u $sourceRef
if ($LASTEXITCODE -ne 0) {
  git -C $aclRepo merge --abort
  throw 'Prefixed source-tree read failed'
}

$candidateTree = git -C $aclRepo write-tree
$candidateSubtree = git -C $aclRepo rev-parse "${candidateTree}:${prefix}"
if ($candidateSubtree -ne $sourceTree) {
  git -C $aclRepo merge --abort
  throw 'Candidate subtree differs from accepted source tree'
}

git -C $aclRepo commit -m 'chore: import autonomous worker framework exact history'
```

The resulting exact-import commit contains no path repair, adaptation, refactor,
dependency change, test change, or execution authorization.

### 7.4 Post-commit proof

All required assertions passed:

- `HEAD^1` equals the exact M2-A checkpoint.
- `HEAD^2` equals the accepted framework commit.
- `HEAD:components/autonomous-worker-framework` equals the accepted source tree.
- A tree-to-subtree diff is empty.
- Every first-parent change is an addition under the accepted component prefix.
- The source tip is an ancestor of the exact-import commit.
- All eight namespaced tag refs retain their original annotated-tag object IDs.
- ACL status is clean.
- No test or framework command runs from the prefixed tree until the separate
  disposable standalone-reconstruction parity step is authorized.

If a pre-commit failure occurs, abort the in-progress merge and stop. If a
post-commit assertion fails, preserve the evidence and return to the M2-A
checkpoint through a separately reviewed rollback; do not amend the import into
passing state.

### 7.5 Verified import outcome

- Exact-import commit:
  `d1c95814bce512318c61a5745dcd684d87e3676a`
- Commit tree: `defab82164d4071bce1899a4b5da4044d0a7cb5f`
- First parent: M2-A checkpoint
  `bbc2e831328c841ae204e4fd6064202a18d3ee5d`
- Second parent: source commit
  `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd`
- Imported prefix: `components/autonomous-worker-framework/`
- Imported subtree: `35ecad05e60c664324a4f30d42a4f6b198181074`
- First-parent change set: exactly 38 additions, all below the imported prefix
- Tree-to-subtree diff: empty
- Source tip ancestor check: passed
- Three source branch refs: exact under the approved import namespace
- Eight annotated tag object IDs: exact under the permanent tag namespace
- Adapter blob: `d38b6a366dc2a69187e217b007af7638ee9cc419`
- Adapter SHA-256:
  `B9F53081D23B0C16F5B262DC900DF1AC08A09FEF12711C1F2B4FA98552EDA558`
- Source and ACL worktrees after the import commit: clean
- ACL strict object check: passed; it reported two dangling blobs and one
  dangling commit, all unreachable from current refs and outside import identity

No framework test or imported command ran. Component authority has not
transferred.

## 8. Untouched standalone parity gate

The user separately authorized the next step after M2-B. A disposable repository
was reconstructed only from
`d1c95814bce512318c61a5745dcd684d87e3676a:components/autonomous-worker-framework`.
Its independent Git tree exactly matched
`35ecad05e60c664324a4f30d42a4f6b198181074`, and it was clean before validation.

Validation environment and result:

- Python: 3.12.10
- pytest: 9.1.1
- Documented command: `python tools\local_validate.py full`
- Compile stage: passed
- Full suite: 163 passed in 45.46 seconds
- Repository status after validation: clean; only ignored test artifacts existed

The initial suite attempt was environment-invalid: 89 tests passed and 74 tests
could not enter setup because pytest lacked permission to its pre-existing
default Windows temp directory. No test reported a framework assertion failure.
The unchanged documented command passed after `TEMP` and `TMP` were directed to
a fresh directory inside the disposable parity area.

Untouched standalone parity was `VERIFIED COMPLETE` at this checkpoint.
In-monorepo testing then required separate authorization; its later result is
recorded in section 9. Prefix adaptation, identity implementation,
component-authority transfer, and execution remained disabled.

## 9. In-monorepo prefix exposure gate

The user separately authorized the next step after standalone parity. From
`components/autonomous-worker-framework/`, the unchanged documented full
validator passed compilation and all 163 tests under Python 3.12.10 and pytest
9.1.1. The first compile attempt was environment-invalid because the restricted
sandbox could not create ignored `__pycache__` directories; the unchanged command
passed when granted write access for generated caches.

The focused quick-validator probe used base
`bbc2e831328c841ae204e4fd6064202a18d3ee5d`. It discovered 46 paths: 38 imported
framework paths under `components/autonomous-worker-framework/` and eight root
governance paths. Because `quick_stages` expects component-relative paths, it
selected no compile or test stage and returned success with:

`No applicable local validation stages were required.`

This is a reproduced fail-open validation-selection defect, not a full-suite
regression. Generated caches and the dedicated pytest temp directory were
removed after validation; ACL and source worktrees remained clean. P-008 repair
and regression tests require separate authorization. Adapter identity repair,
component-authority transfer, and execution remain disabled.
