# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **SR-2 Slices 1–6 accepted; G1–G21 acceptance closure next**

**Clean reset runtime checkpoint:** `267fc28bd862ddd4ca22e61792d073853a1e51a8` — Actions `34443719080` success  
**SR-2 Slice 1:** `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336` — Actions `34444560064` success  
**SR-2 Slice 2:** `b9248ac6c0471743d218bb6df9720d92deb320c5` — Actions `34445248423` success  
**SR-2 Slice 3:** `70dde361cd62f507f54b5e42e3ef12cea27ce11f` — Actions `34446983351` success  
**SR-2 Slice 4:** `33c83e99728de9cab9a4eede8030fa733a4a5beb` — Actions `34448019988` success  
**SR-2 Slice 5:** `ee285a5301bd81c9bd011799c7150ce3d081e11a` — Actions `34450118281` success  
**SR-2 Slice 6:** `1534dba10757612485821bf566c6fdccffde06c2` — Actions `34452778382` success

This file is the controlling restart entry point for Knowledge Core. Git history is the archive; active implementation guidance belongs here and in the controlling contracts.

## Accepted foundation

The following remain accepted and are not being rebuilt:

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`.
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`.
- RF-2 whole-`ResourceVersion` PostgreSQL lexical retrieval: `479a918762e919851e19fee3b36cc1d95e78f3e8`.
- Governed repository import RI-2: `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`.
- RI-3 persistence qualification: `9a167e67200c6bee2b7f4ed7b1dc91224d553390`.
- RI-4 intended-host persistence/recovery qualification and evidence.
- Audit-amended SR-1 contract: `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`.
- Architecture correction KC-D025 in `docs/architecture/knowledge-core/DECISIONS.md`.

Exact whole `ResourceVersion` artifacts remain canonical evidence. Repository source observations and governing import receipts/manifests remain governed source/classification evidence. SR-2 structures, lineage, profiles, and search projections remain derived and rebuildable.

## Rejected prototype boundary

Commit `2c48a0e73c560fad62028776f375c94162e138be` is **ABANDONED — DO NOT USE FOR IMPLEMENTATION, TEST DESIGN, MIGRATION DESIGN, OR DECISION-MAKING**.

Do not restore files or implementation patterns from that commit. The active SR-2 implementation was rebuilt from the amended contract.

## Research-alignment checkpoint

Before Slice 5, Slices 1–4 were re-audited against the completed Knowledge Architecture Evidence Campaign, especially:

- `docs/research/knowledge-architecture/CONCEPTUAL_ARCHITECTURE_SYNTHESIS.md`;
- `docs/research/knowledge-architecture/invariants.md`;
- `docs/research/knowledge-architecture/gaps/formal-provenance-evidence-lineage.md`;
- `docs/research/knowledge-architecture/gaps/resource-artifact-identity-lineage.md`.

No redesign was required. The implementation remains aligned with the research requirements that canonical source evidence and derived projections remain distinct; exact immutable source versions are bound to consequential derivations; logical source identity, exact observed version, derived-record identity, and presentation identity remain separate; provenance is explicit lineage rather than inferred metadata; current/historical lifecycle is explicit; replacement projections are built and validated before cutover; and derived indexes remain generation/profile-bound and rebuildable.

Slice 5 added explicit generation-level structural/projection profile identity rather than relying only on an opaque aggregate config digest. Slice 6 preserves staged replacement semantics: an SR-2 candidate is built and revalidated while non-serving, then the generation and its governing RI-2 receipt cross the publication boundary atomically.

## Active SR-1 / KC-D025 rules

- Structural segmentation depends only on exact canonical `ResourceVersion` bytes/media plus the exact structural profile.
- Governed lifecycle/source-ranking projection additionally depends on the exact governed observation/classification snapshot plus the retrieval-projection profile.
- Declared section lifecycle remains source-derived evidence.
- Effective lifecycle is the most restrictive of governed document lifecycle, applicable ancestor declarations, and the section's own declaration.
- Less-restrictive declarations never promote effective lifecycle and are not structural errors.
- Ordinary prose, inline code, block quotes, and fenced examples mentioning `kc:retrieval-lifecycle` remain content; malformed/misplaced/duplicate standalone attempted controls fail lifecycle projection.
- A -> B -> A reuses A's exact content-addressed `ResourceVersion` and structural segment identities under the same structural profile.
- Repository supersession/retirement-retain is historical retrieval classification, not privacy deletion.
- Privacy `RESTRICT`/`ERASE` fences serving access first; derivative cleanup is deterministic/idempotent reconciliation.
- A serving SR-2 generation must make the exact governed snapshot set and behavior-bearing profile identity recoverable; `resource_version_ref` alone is insufficient.

`SR2-G1` through `SR2-G22` in the amended SR-1 contract remain the final acceptance requirements.

## Accepted SR-2 slices

### Slice 1 — deterministic structural segmentation

Checkpoint `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336`.

Lifecycle-blind strict UTF-8 segmentation, exact byte/line coordinates, ATX/fence-aware structure, deterministic continuation splitting, gap-free reconstruction, exact slice SHA-256, deterministic structural keys, and empty-document behavior.

### Slice 2 — governed lifecycle/control projection

Checkpoint `b9248ac6c0471743d218bb6df9720d92deb320c5`.

Preserves source declarations and coordinates, computes monotone effective lifecycle, rejects genuine standalone attempted-control errors, remains structurally identity-neutral, and binds an explicit governed observation identity plus retrieval-projection profile.

### Slice 3 — exact governed projection lineage storage

Checkpoint `70dde361cd62f507f54b5e42e3ef12cea27ce11f`.

`kc_derived.text_generation_source` binds each derived parent to its exact canonical version, immutable RI-2 observation, governing manifest/receipt, and deterministic effective projection snapshot without copying canonical/governed evidence.

### Slice 4 — governed source selection

Checkpoint `33c83e99728de9cab9a4eede8030fa733a4a5beb`.

Reconstructs current, prior-version, and retirement-retain source snapshots through the explicit RI-2 manifest chain; verifies exact evidence relationships; preserves immutable observations; and proves A -> B -> A version/structural-key reuse with new projection snapshot identity.

### Slice 5 — validated segment-generation persistence

Checkpoint `ee285a5301bd81c9bd011799c7150ce3d081e11a`.

Adds explicit `text_generation_profile` identity plus `resource_segment_text_search` derived segment rows with structural coordinates/identity, declared/effective lifecycle provenance, inherited governed source metadata, and weighted PostgreSQL lexical vectors. Successful candidates remain `BUILDING` and non-serving until publication.

### Slice 6 — atomic publication and serving integration

Checkpoint `1534dba10757612485821bf566c6fdccffde06c2`.

Slice 6 adds:

- atomic publication of a revalidated SR-2 candidate and its exact `applying` RI-2 governing receipt in one PostgreSQL transaction;
- preservation of the generic late-finisher generation fence, including failure/staling if a competing publication settles the receipt first;
- serving dispatch by current text-generation implementation identity: RF-2 current generations read only whole-document rows, SR-2 current generations read only segment rows;
- deterministic segment ranking by lexical score, effective lifecycle, authority rank, parent revision, parent version ref, segment ordinal, and segment key;
- `include_superseded=false` filtering on effective lifecycle with result limit applied only after serving-time parent eligibility;
- segment/generation/profile/governed-source provenance in the bounded retrieval domain/API response without copied bodies or artifact/internal credentials;
- privacy derivative cleanup for exact/logical parent targets plus mandatory serving-time parent eligibility as defense in depth;
- a section-aware repository-import kernel that composes accepted RI-2 canonical/observation writes with SR-2 candidate build and atomic publication without altering the accepted RI-2 kernel used by RI-4 qualification.

Qualification `34452778382`:

- migrations through `0012_sr2_segments`: passed;
- fast suite: **71 passed**, 1 guarded exact-corpus skip;
- PostgreSQL suite: **29 passed**, 2 guarded exact-corpus skips;
- RI-4 intended-host restart/replay qualification: passed.

The guarded exact-corpus skips refuse to relabel later-edited documentation as earlier pinned evidence; they are not SR-2 failures.

## Restart order

Read, in order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
5. accepted generation, RF-2, RI-2, deletion, and SR-2 Slice 1–6 interfaces needed for the bounded next slice

Do not search Git history for SR-2 implementation guidance unless explicitly investigating the rejected prototype.

## Next bounded task — SR-2 Slice 7: G1–G21 acceptance closure

Audit the fresh Slices 1–6 tests against every amended SR2-G1 through SR2-G21 requirement. Do not infer a gate is covered merely because adjacent behavior passed.

Slice 7 should:

- create an explicit G1–G21 coverage matrix mapping each contractual assertion to one or more concrete synthetic/PostgreSQL tests;
- add only missing qualification fixtures/assertions required by the amended contract;
- prove structural profile changes and projection-only changes remain distinct and never mutate canonical evidence or mix serving generations;
- prove repository supersession/retirement-retain remains distinct from privacy restriction/erasure reconciliation;
- prove complete generation/profile/governed-snapshot provenance through the service boundary without exposing internal storage/artifact controls;
- mechanically separate G22 from G1–G21 in pytest/CI so the real-document pilot cannot execute until every synthetic/PostgreSQL acceptance gate has passed;
- leave G22 itself unexecuted until the G1–G21 closure commit is independently green.

Do not broaden the implementation unless an uncovered G1–G21 requirement exposes an actual defect.

## Intended-host boundary

No new user-PC execution is required through Slice 7. CI is the acceptance environment for deterministic synthetic/PostgreSQL G1–G21 closure.

After G1–G21 are independently green, G22 may run against the tiny pinned real-document pilot. Intended-host SR-2 restart/recovery qualification on the user's PC should occur only after the complete G1–G22 SR-2 acceptance suite is green and before SR-2 is declared operationally accepted for that host.

## Out of scope

Do not expand SR-2 into embeddings, vector search, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic classification/document-key assignment, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
