# Knowledge Core — Retrieval / Import Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RF-2 and RI-2/RI-3/RI-4 remain accepted. SR-1 is audit-amended. SR-2 is authorized but paused with pre-audit candidate `2c48a0e73c560fad62028776f375c94162e138be` not accepted. No implementation fixes are part of the documentation amendment.**

## Accepted checkpoints

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`
- RF-2 retrieval: `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`
- First curated real-corpus pilot: `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`
- RI-1 design: `f7f12c04163ecbe3b6143191008cf393726b8def`
- RI-2 governed importer: `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`
- RI-3 validated checkpoint: `9a167e67200c6bee2b7f4ed7b1dc91224d553390` — CI `34418080815`
- RI-4 harness: `934850d5830d4a5d89ec32b04630435a027e816f` — CI rehearsal `34418809968`
- RI-4 intended-host evidence: `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md` — success
- Original SR-1 design commit: `1d1313844aa4d224bd42c0888970a11e959d9501`
- Pre-audit SR-2 candidate: `2c48a0e73c560fad62028776f375c94162e138be` — not accepted
- Controlling SR-1 contract: `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — audit-amended 2026-09-10

## Read-order / precedence rule

For any new retrieval/section-retrieval continuation, read:

1. `CURRENT_STATE.md`;
2. `DECISIONS.md`, especially `KC-D025`;
3. audit-amended `SECTION_RETRIEVAL_SR1.md`;
4. this handoff;
5. RI-1/RI-2 records with their post-acceptance content-identity clarification;
6. RF-2/RI-2 implementation interfaces relevant to the bounded task;
7. `EXECUTION_GOVERNANCE.md`;
8. `components/knowledge-core/README.md`.

Where older wording conflicts, the audit-amended SR-1 contract plus `KC-D025` control. Historical RF/RI qualification records continue to describe what was actually tested at their checkpoints and are not silently reinterpreted.

`SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md` is historical planning context only and cannot override the amended contract.

## Accepted foundation

Kernel V1 remains frozen. Stable repository document identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

`ResourceVersion` is exact content identity within one logical Resource. Previously unseen bytes create a new exact version; re-observed bytes matching an existing digest reuse that exact version. A → B → A therefore reuses A's original exact `ResourceVersion` while a new observation/receipt/generation records the later source observation.

RI-2 still requires exact manifest-listed Git objects, explicit lifecycle/authority/classification, manifest chaining, omission safety, exact replay, stale-state rejection, publication fencing, and service-only repository access.

RF-2 remains the implemented whole-`ResourceVersion` PostgreSQL lexical baseline with exact parent provenance, deterministic rank, current-generation-only serving, and mandatory serving-time privacy/restriction/deletion fencing.

RI-3/RI-4 remain accepted persistence/recovery evidence for their bounded historical workloads.

## Audit-amended SR-1 contract

The exact whole `ResourceVersion` and immutable artifact remain canonical evidence. Smaller retrieval units remain derived/disposable state.

### Structural segmentation boundary

Structural segmentation is determined solely by:

```text
exact ResourceVersion bytes/media
+ exact structural segmentation profile
```

It produces deterministic:

- segment boundaries and ordinals;
- structural kind/base block/part coordinates;
- byte and line coordinates;
- heading paths;
- source-slice SHA-256 values;
- structural segment keys.

Changing lifecycle classification alone must not change those structural identities.

### Governed lifecycle/source projection boundary

Complete retrieval projection is determined by:

```text
structural segments
+ exact governed observation/classification snapshot
+ retrieval-projection profile
```

The exact governed snapshot set must be identifiable from generation lineage. `ResourceVersion + segmentation profile` alone is insufficient to reproduce lifecycle, authority, source path/version, classification, or rationale because identical canonical bytes may be re-observed later under different governed metadata.

### Declared and effective lifecycle

Lifecycle restrictiveness remains:

```text
current < unknown < superseded
```

A section declaration is preserved exactly as source evidence. Effective lifecycle is the most restrictive of:

1. governed parent-document lifecycle;
2. every applicable ancestor-section declaration;
3. the section's own declaration.

A child declaration of `current` under an `unknown` or `superseded` parent is valid source content but cannot promote effective lifecycle. Likewise a descendant `current` cannot undo an ancestor `superseded` declaration.

A parent downgrade on unchanged bytes must produce a new governed projection, not a structural segmentation failure. Structural keys remain the same; effective lifecycle becomes more restrictive.

### Narrow lifecycle-control recognition

Valid declaration forms remain exact standalone Markdown HTML comments immediately after the heading:

`<!-- kc:retrieval-lifecycle=current -->`  
`<!-- kc:retrieval-lifecycle=unknown -->`  
`<!-- kc:retrieval-lifecycle=superseded -->`

Ordinary prose, inline-code examples, block quotes/quoted explanations, and fenced-code examples containing `kc:retrieval-lifecycle` remain ordinary content.

Outside a fence, a line whose first bytes after zero through three leading spaces are `<!-- kc:retrieval-lifecycle` is a control-looking attempted directive. Exact valid/eligible/unique form applies. Malformed, misplaced, or duplicate attempted controls fail lifecycle projection explicitly.

### Large-block completion

- remaining suffix ≤ hard max is emitted whole and terminates;
- no split occurs inside a UTF-8 line or fenced block;
- an indivisible fence or ordinary UTF-8 line that exceeds hard max without a legal external boundary fails deterministic structural segmentation.

### Privacy versus historical supersession

Repository supersession/retirement-retain is historical retrieval lifecycle, not privacy deletion. Historical segments may remain/rebuild and are excluded by default.

Privacy `RESTRICT`/`ERASE` fences parent and children immediately. Derivative cleanup is deterministic/idempotent reconciliation and may be eager. Actual physical purge/erasure of the parent exact version requires no segment derivative to remain. Serving-time parent eligibility is mandatory even if stale rows exist.

## Amended SR2-G highlights

The complete gates remain in `SECTION_RETRIEVAL_SR1.md`. Important changed expectations are:

- **G1/G9:** exact governed observation/classification lineage is part of retrieval-generation provenance;
- **G4/G11:** ordinary mentions of the lifecycle token are content; only standalone control-looking comments enter control validation;
- **G5/G6:** final suffix and oversized ordinary-line behavior are explicit;
- **G7:** structural determinism is separate from complete projection reproducibility;
- **G8:** A → B → A reuses A's exact ResourceVersion and structural keys;
- **G12:** less-restrictive declarations no longer fail; they cannot promote effective lifecycle;
- **G17:** immediate privacy serving fence plus idempotent derivative reconciliation; historical supersession remains distinct;
- **G21:** structural-profile changes are distinct from retrieval-projection-only changes;
- **G22:** real-doc pilot must prove ordinary literal discussion of the lifecycle token is safe and must bind exact governed observation inputs.

## Current SR-2 candidate state

SR-2 candidate commit:

`2c48a0e73c560fad62028776f375c94162e138be`

was written against the pre-audit SR-1 rules. It is **not an accepted SR-2 checkpoint**.

GitHub Actions run `34439043763` showed:

```text
migrations: success
fast suite: success
PostgreSQL: 19 passed, 2 historical skips, 1 G22 failure
RI-4 rehearsal: skipped after PostgreSQL failure
overall: failure
```

The G22 failure was a real-pilot query-fixture mismatch. No test fix has been applied because the audit required the contract to be corrected first.

In addition to that query mismatch, the candidate must be audited against the amended lifecycle/parser/reproducibility/identity/purge rules before it can be accepted.

## What must not happen next

Do not:

- treat pre-amendment G11/G12 expectations as controlling;
- reject a valid child declaration merely because its effective inherited state is more restrictive;
- treat arbitrary prose containing `kc:retrieval-lifecycle` as a control error;
- claim lifecycle projection is reproducible from `ResourceVersion + structural profile` without the governed observation snapshot;
- create a duplicate ResourceVersion for A → B → A;
- equate import supersession with privacy purge;
- broaden into embeddings, RAG, models, Authority, execution, broad corpus import, or unrelated deployment work.

## Next bounded implementation action

When implementation work resumes, first compare `2c48a0e...` against every amended SR2-G gate. Then change only the minimum runtime/schema/test/pilot pieces needed to conform and rerun synthetic-first qualification before the tiny real-document pilot.

This documentation amendment itself authorizes no runtime fix.

## Stop boundary

**SR-2 remains paused at the audit-alignment boundary. The controlling contract is corrected first; implementation remains intentionally unchanged until the next explicit continuation.**