# Worker Lab M3 Recovery and Exact-Import Preflight

**Status:** VERIFIED — recovery complete; exact import not performed
**Observed:** 2026-08-31
**Execution authority:** Disabled
**Component import performed:** No

This record binds the accepted Worker Lab source identity to an independently
verified offline recovery artifact and defines the exact, non-squashed M3-B
import procedure. It does not authorize that procedure. No Worker Lab file was
modified, imported, executed, or tested during M3-A.

## 1. ACL checkpoint basis

- Repository: `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`
- Accepted M2 checkpoint:
  `fe5182fceb4eef2a94df15977903421feee00c82`
- M2 tree: `e70978a5bcb5b879b5fa485c326295efb3812aea`
- Branch: `main`
- Object format: SHA-1, matching Worker Lab
- Working tree at M3-A start: clean
- Network fetch/push: not performed

The commit containing this record is the M3-A checkpoint. M3-B must receive
separate user authorization naming that exact commit before any import command
runs.

## 2. Reverified Worker Lab identity

- Source: `C:\Users\MineTrackerWorker\repos\worker-lab`
- Branch/upstream: `main` / `origin/main`
- HEAD: `fddf0726b975a8192d5e126f109e6fc756f11b36`
- Tree: `5fe9e3f153b48543a57f3b9d1e339b3cd875930a`
- Remote relation: 10 commits ahead, 0 behind
- Working tree and index: clean, including ordinary untracked reporting
- Shallow repository: no
- Object format: SHA-1
- Tracked HEAD tree: 68 files / 634,920 bytes
- Reachable commits in `HEAD` and across all refs: 44
- Reachable object-list lines: 392
- Root commit: `9ea3e68dfae00bd15e2672b80a007f13cb8339f3`
- Alternate object database: none

The ignored `.phase3c-test-temp*` test-residue paths remain excluded and were
not inspected or cleaned. Strict object verification passed. It reported two
unreachable dangling blobs, `58b14be8b1903ca14978ff68ef24b09954906d39`
and `60b2131b965234b5c6e4818aa845ccda473b40f9`; neither belongs to the complete
reachable history selected for import.

The accepted tip includes ten local-only commits after `origin/main`. Their
oldest-to-newest identities are:

1. `ec53b1eab80b7f9e1963e7d132897ce7b708ba27`
2. `64a258567d3fc13fd073da7a50fb5c0f39a02b88`
3. `32b215b215f1b587a921aa15078d4d0a3e9bd859`
4. `ecce2f3e2523ad10748046f002d10a7565081e3c`
5. `259330b0f091c5d5879b5cb44ba8d280c2f7e200`
6. `678ece902f14da90f57245e7b751ac1b0f73b6fe`
7. `b114977735967535efa4be037df6068222f0fc2e`
8. `6d63a18396203846cb3a97c1b7fb2a25c8039e1d`
9. `ca55e30ccbcbf2318d73b3ef8a65f66bb9e1e684`
10. `fddf0726b975a8192d5e126f109e6fc756f11b36`

## 3. Reachable source refs

Every local branch tip and annotated tag target is an ancestor of accepted
`main`; no branch adds history outside its 44 commits.

| Source ref | Object | Classification |
|---|---|---|
| `refs/heads/main` | `fddf0726b975a8192d5e126f109e6fc756f11b36` | Accepted import tip |
| `refs/heads/docs/phase3b-integrated-checkpoint` | `2c7d99af4343c15f670073896cc62319d322f107` | Ancestor of `main` |
| `refs/heads/experiment/terra-batch3-verification` | `ee574fd0483afa2fcb926462f21ebcc0245555f8` | Ancestor of `main` |
| `refs/heads/fix/phase1-audit-corrections` | `d0e17d9a87a7d308260a35cd31d2ecbaf4f4d01c` | Ancestor of `main` |
| `refs/heads/phase2/batch4-acceptance-v1` | `48bc3fd315658201ca3d0f9be71e9d2c0f063ac5` | Ancestor of `main` |
| `refs/heads/phase2/workspace-preparation-v1` | `757260efc32cc06b1b850458623dbfcba6635b8d` | Ancestor of `main` |
| `refs/heads/phase2/workspace-verification-disposal-v1` | `c5cc1a49e0dd620f4813cf867d076611f8b4cca1` | Ancestor of `main` |
| `refs/heads/phase3/framework-contracts-v1` | `07f106ef23c8e69e1388f234773d6a1e321f2634` | Ancestor of `main` |
| `refs/heads/phase3/framework-interface-spec-v1` | `eee9c7f2a4ab210dd6f22c774a7969e40a2a5a3d` | Ancestor of `main` |
| `refs/tags/v0.1.0-phase1` | `6da2642d2f8199db683caab62e2bcf791929b578` | Annotated; peels to `b7f5bac69d33ebd2c8521897c2a895a8e6e5f126` |
| `refs/tags/v0.1.1-phase1` | `5bc4e600cb53723cc25aa8a9d42b762e9724302e` | Annotated; peels to `d0e17d9a87a7d308260a35cd31d2ecbaf4f4d01c` |
| `refs/tags/v0.1.2-phase1` | `95d259ecec20c941d04e777ea2ca54d132d0f913` | Annotated; peels to `0b6869f889201eeac9091845c9e71bb573d10bbd` |
| `refs/tags/v0.2.0-phase2` | `6ca238ae5b5477cff108e33a75bcf39f09650116` | Annotated; peels to `bcfb1562c3f274c0256ed4105d5f443ab0749ace` |

The bundle also records seven `refs/remotes/origin/*` refs. They are recovery
evidence, including the pre-local-commit remote state, and are not permanent
monorepo import refs.

## 4. Accepted recovery artifact

- Path:
  `C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-20260831-fddf0726-full.bundle`
- Size: 257,743 bytes
- SHA-256:
  `74445D0BAC13B4EC24B2036E6BB66927D3E5136DC3F206A2BB5019B023899F36`
- Bundle creation input: `--all` from the clean source repository
- Advertised refs: nine heads, seven remote-tracking refs, four annotated tags,
  and `HEAD`
- Bundle classification: complete history, SHA-1 object format

The artifact is outside both the source repository and monorepo so either Git
repository can be reconstructed if its working directory is lost.

## 5. Recovery verification

The following checks passed:

1. `git bundle verify` reported the artifact as complete and valid.
2. The SHA-256 was identical before and after the recovery drill.
3. A unique temporary bare mirror was cloned only from the bundle.
4. All 21 recovered refs exactly matched the source refs.
5. Recovered `main`, HEAD, tree, history, roots, and annotated tags matched the
   identities in sections 2 and 3.
6. The mirror contained 44 reachable commits and 392 reachable object-list
   lines.
7. Strict object verification passed in the recovered mirror.
8. The temporary mirror was removed only after its exact containment under the
   uniquely created system-temporary directory was verified.

No Worker Lab code, worker, model, adapter, or test was run.

## 6. Permanent tag namespace for M3-B

M3-B must fetch each annotated tag object directly into the namespaced tag ref.
This preserves the tag objects exactly and prevents collisions.

| Source tag | Monorepo tag ref |
|---|---|
| `v0.1.0-phase1` | `worker-lab/v0.1.0-phase1` |
| `v0.1.1-phase1` | `worker-lab/v0.1.1-phase1` |
| `v0.1.2-phase1` | `worker-lab/v0.1.2-phase1` |
| `v0.2.0-phase2` | `worker-lab/v0.2.0-phase2` |

Source heads use `refs/remotes/m3-worker-lab/*`. Complete ancestry is durable
through the exact-import commit's second parent. Source remote-tracking refs stay
only in the recovery bundle and this record.

## 7. Exact non-squashed M3-B procedure — not authorized or executed

The procedure mirrors the proven native-Git M2 import: a merge parent preserves
ancestry and a prefixed `read-tree` preserves the exact selected tree. It must
produce one exact-import commit with no repair or adaptation.

### 7.1 Preconditions

Before any mutating command, M3-B must:

1. receive separate authorization naming the exact M3-A checkpoint commit;
2. require that exact `main` HEAD and an empty ACL status;
3. recheck the artifact SHA-256 and run `git bundle verify`;
4. require `components/worker-lab/`, the import-head namespace, and the
   namespaced tags to be absent;
5. require SHA-1 object format;
6. require the bundle's `main`, tree, heads, and annotated tags to match this
   record exactly;
7. require the source repository's accepted HEAD/tree and tracked status to
   remain unchanged; and
8. keep execution and component-authority transfer disabled.

Any mismatch stops M3-B before tree changes.

### 7.2 Ref fetch

```powershell
$aclRepo = 'C:\Users\MineTrackerWorker\repos\autonomous-coding-lab'
$bundle = 'C:\Users\MineTrackerWorker\backups\worker-lab\worker-lab-20260831-fddf0726-full.bundle'

git -C $aclRepo fetch --no-tags $bundle `
  '+refs/heads/*:refs/remotes/m3-worker-lab/*' `
  '+refs/tags/*:refs/tags/worker-lab/*'
```

After the fetch, all nine head refs and four annotated tag object IDs must match
sections 2, 3, and 6 exactly. Missing, extra, or mismatched imported refs stop
the operation.

### 7.3 Exact prefixed merge-parent import

The user-supplied M3-A hash must replace the placeholder below. It may not be
inferred from a moving branch name.

```powershell
$expectedBase = '<exact-M3-A-checkpoint-provided-by-user>'
$sourceRef = 'refs/remotes/m3-worker-lab/main'
$sourceCommit = 'fddf0726b975a8192d5e126f109e6fc756f11b36'
$sourceTree = '5fe9e3f153b48543a57f3b9d1e339b3cd875930a'
$prefix = 'components/worker-lab'

if ((git -C $aclRepo rev-parse HEAD) -ne $expectedBase) { throw 'M3-A checkpoint mismatch' }
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

git -C $aclRepo commit -m 'chore: import Worker Lab exact history'
```

### 7.4 Required post-commit proof

- `HEAD^1` equals the exact M3-A checkpoint named by the user.
- `HEAD^2` equals `fddf0726b975a8192d5e126f109e6fc756f11b36`.
- `HEAD:components/worker-lab` equals
  `5fe9e3f153b48543a57f3b9d1e339b3cd875930a`.
- A source-tree-to-imported-subtree diff is empty.
- The first-parent change set is exactly 68 additions, all under
  `components/worker-lab/`.
- The accepted source tip is an ancestor of the import commit.
- All nine source head refs and four namespaced annotated-tag object IDs match.
- Source and ACL tracked statuses are clean.

No Worker Lab test or imported command runs in the exact-import turn. Untouched
standalone reconstruction parity is a later, separately authorized step. Path,
identity, protocol, and bilateral-cleanliness adaptation follows only in a
separate commit after parity.

If a pre-commit failure occurs, abort the in-progress merge and stop. If a
post-commit assertion fails, preserve the evidence and return to the M3-A
checkpoint only through a separately reviewed rollback; do not amend the import
into passing state.

## 8. M3-B readiness

M3-A is complete and Worker Lab is not imported. M3-B is mechanically ready
only after the user names the exact commit containing this record and separately
authorizes the exact import. Sol High is sufficient for that bounded operation;
Ultra review is not required.
