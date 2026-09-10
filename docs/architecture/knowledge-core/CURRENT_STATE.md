# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-2 retrieval:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**First curated real-corpus pilot:** `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`  
**RI-1 design:** `f7f12c04163ecbe3b6143191008cf393726b8def`  
**RI-2 governed importer:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**RI-3 validated checkpoint:** `9a167e67200c6bee2b7f4ed7b1dc91224d553390` — CI `34418080815`  
**RI-4 host harness:** `934850d5830d4a5d89ec32b04630435a027e816f` — CI rehearsal `34418809968`  
**RI-4 intended-host evidence:** `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md` — success  
**Original SR-1 design commit:** `1d1313844aa4d224bd42c0888970a11e959d9501`  
**Pre-audit SR-2 candidate:** `2c48a0e73c560fad62028776f375c94162e138be` — **not accepted**  
**Controlling SR-1 contract:** `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — **audit-amended 2026-09-10**  
**Current phase:** **SR-2 paused for alignment to the amended SR-1 contract**

This is the controlling branch-specific state.

## Current status

Kernel V1, RF-2, RI-2, RI-3, and RI-4 remain accepted. The exact whole `ResourceVersion` remains canonical evidence. No broad or production corpus has been imported.

SR-2 was authorized and a first candidate implementation was committed as `2c48a0e73c560fad62028776f375c94162e138be`. A bounded independent audit then identified six design defects/ambiguities in the original SR-1 contract. The corrected systems semantics were reviewed and accepted before further implementation work.

The SR-1 contract is now amended. **The code, migration, tests, API schemas, and SR-2 real-pilot manifest from `2c48a0e...` have intentionally not yet been repaired.** They must not be treated as accepted SR-2 behavior merely because many pre-amendment tests passed.

The first CI run for `2c48a0e...` was GitHub Actions run `34439043763`:

```text
migrations: passed
fast semantic suite: 50 passed, 1 historical-pilot skip, 22 deselected
PostgreSQL suite: 19 passed, 2 historical-pilot skips, 1 SR-2 G22 failure
RI-4 rehearsal: skipped because the PostgreSQL step failed
workflow conclusion: failure
```

The observed G22 failure was a real-pilot query-fixture mismatch (`rename heuristics` did not produce the expected PostgreSQL hit). That test has **not** been changed yet because the audit amendment paused implementation work first.

More importantly, the pre-audit candidate encodes some superseded SR-1 lifecycle/parser/rebuild assumptions. It therefore requires a bounded contract-alignment pass before any CI result can qualify SR-2.

## Accepted foundation

Stable governed repository document identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Exact `ResourceVersion` identity remains content-addressed within one logical Resource. A previously unseen exact representation creates a new version; re-observing a prior representation reuses that existing exact version. Thus A → B → A reuses the original A `ResourceVersion` while a new governed observation/receipt/generation records the later observation.

RF-2 remains the accepted whole-`ResourceVersion` PostgreSQL lexical baseline with explicit lifecycle/authority metadata, deterministic ranking, one-current-generation serving, exact parent provenance, and mandatory serving-time restriction/deletion fences.

RI-2 remains the accepted governed repository importer: exact manifest-listed SHA-1 Git source verification, explicit Manifest V2 allowlists, manifest chaining, omission safety, stable logical identity, content-addressed exact-version reuse, explicit classification/retirement, stale-state rejection, publication fencing, exact replay, and service-only repository access.

RI-3/RI-4 persistence/recovery evidence remains historical qualification evidence and is not invalidated by the SR-1 section-retrieval correction.

## SR-1 audit-amended section-retrieval contract

The controlling contract is:

`docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`

The material corrections are summarized below. If any older document conflicts, the amended SR-1 contract and `KC-D025` in `DECISIONS.md` control.

### 1. Structural segmentation is separate from governed lifecycle projection

Structural segmentation depends only on:

- exact canonical `ResourceVersion` artifact/media;
- exact structural segmentation profile.

That pair determines structural segment boundaries, coordinates, source-slice digests, heading paths, kinds, and structural segment keys.

Complete retrieval projection additionally depends on:

- the exact governed observation/classification snapshot;
- retrieval lifecycle/control/lexical/ranking projection rules.

A serving generation must preserve enough lineage to identify those exact governed projection inputs. `ResourceVersion + segmentation profile` alone is no longer claimed to reproduce lifecycle/source-ranking state.

### 2. Declared lifecycle is preserved; effective lifecycle is monotone

Lifecycle restrictiveness remains:

```text
current < unknown < superseded
```

For a section:

```text
effective lifecycle = most restrictive of
    governed document lifecycle
    applicable ancestor-section declarations
    own section declaration
```

A valid child declaration of `current` under an `unknown` or `superseded` parent is preserved as source evidence but cannot promote the effective state. A later parent downgrade therefore does not make unchanged canonical bytes fail segmentation; the same structural segment identities are reused and the new projection becomes more restrictive.

SR2-G12 now tests **effective non-promotion**, not parser rejection of less-restrictive declarations.

### 3. Lifecycle-control grammar is narrow

An exact eligible standalone lifecycle HTML comment is semantic control. Ordinary prose, inline code, block quotes/quoted explanations, and fenced examples containing `kc:retrieval-lifecycle` remain ordinary content.

A standalone, non-fenced, control-looking HTML-comment line beginning with the reserved control prefix is an attempted directive. If malformed, duplicated, or misplaced it fails lifecycle projection explicitly. This retains typo detection without poisoning documentation that discusses the token.

### 4. Large-block termination is explicit

The structural splitter:

- emits a remaining suffix whole when it fits `hard_max_bytes`;
- never splits inside a UTF-8 line or fenced block;
- deterministically fails when an indivisible fenced region **or ordinary UTF-8 source line** exceeds the hard maximum with no legal external boundary.

### 5. Content identity includes A → B → A reuse

A new byte representation not previously present under the logical Resource gets a new `ResourceVersion`. Re-observed bytes that match an earlier exact version reuse that version. Under the same structural profile, its original structural segment identities therefore return.

### 6. Privacy purge is not repository supersession

Repository/import supersession or retirement-retain is historical lifecycle metadata, not privacy deletion. Its segments may remain historical and are excluded by default retrieval.

Privacy `RESTRICT`/`ERASE` fences parent and children immediately. Derivative cleanup is deterministic/idempotent reconciliation and may occur eagerly. If a parent exact version is actually physically purged/erased, no segment derivative may remain. Serving-time parent eligibility remains mandatory defense in depth.

## Amended SR2-G boundary

`SECTION_RETRIEVAL_SR1.md` remains the source of truth for `SR2-G1` through `SR2-G22`. The materially changed gates are especially:

- G1 — canonical evidence plus exact governed observation separation;
- G4 — ordinary lifecycle-token discussion remains content;
- G5/G6 — explicit final suffix and oversized ordinary-line behavior;
- G7 — structural determinism distinguished from complete projection reproducibility;
- G8 — A → B → A exact-version/segment reuse;
- G9 — exact governed projection provenance;
- G11 — valid standalone controls vs ordinary mentions vs malformed standalone controls;
- G12 — effective lifecycle cannot be promoted; less-restrictive declarations do not fail;
- G17 — immediate serving fence plus idempotent derivative reconciliation, with supersession kept distinct from privacy purge;
- G21 — structural-profile change distinguished from retrieval-projection-only change;
- G22 — real-document pilot must exercise safe literal discussion of the lifecycle token and exact governed observation lineage.

No implementation may claim SR-2 acceptance until the amended gates are implemented and requalified.

## Document precedence and restart order

To prevent fallback to the pre-audit rules, a new SR-2 continuation must read in this order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially `KC-D025`
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — audit-amended controlling SR-1 contract
4. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
5. `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md` and `REPOSITORY_IMPORT_RI2.md` — with their post-acceptance A→B→A clarification
6. accepted RF-2/RI-2 runtime interfaces and tests needed for the bounded change
7. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
8. `components/knowledge-core/README.md`

`SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md` is historical planning context only. Its original design assumptions do not override the amended SR-1 contract.

RF-1/RF-2 and RI-3/RI-4 completion/evidence documents remain historical records of the behavior they actually qualified. They must not be used to override later section-retrieval amendments.

## Current limitations / unclaimed capability

Knowledge Core does not yet claim:

- **accepted** SR-2 section/segment retrieval under the amended contract;
- exact governed observation lineage in the current pre-audit SR-2 segment generation implementation;
- corrected declared-vs-effective lifecycle behavior in the current pre-audit SR-2 implementation;
- corrected narrow standalone control parsing in the current pre-audit SR-2 implementation;
- requalified A→B→A section identity behavior under SR-2;
- requalified derivative-reconciliation semantics under amended G17;
- a passing amended G1-G22 qualification run;
- machine-reboot persistence, backup/restore, or production deployment/security qualification;
- broad/production corpus import or automatic discovery/classification/document-key assignment;
- SHA-256-format Git repository support;
- PDF/DOCX/HTML extraction/OCR, embeddings/vector retrieval, semantic reranking, or RAG/context assembly;
- cross-version semantic section identity;
- model-based lifecycle inference;
- Authority integration or autonomous execution.

## Next bounded SR-2 action

SR-2 remains authorized, but implementation is paused at the documentation boundary requested after the audit.

The next implementation action, when resumed, is **not** general feature work. It is a bounded comparison of commit `2c48a0e73c560fad62028776f375c94162e138be` against the amended SR2-G1 through G22 contract, followed only by the minimum code/schema/test corrections needed to conform and a fresh synthetic-first qualification.

Do not change implementation as part of this documentation-only amendment. Do not add embeddings, RAG, broad import, Authority, execution, or unrelated deployment work.

## Stop boundary

**Documentation is being corrected before implementation. The pre-audit SR-2 candidate remains intentionally unaccepted and unchanged until a separately resumed implementation pass aligns it with the amended contract.**