# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **clean SR-2 restart baseline**  
**Clean reset runtime checkpoint:** `267fc28bd862ddd4ca22e61792d073853a1e51a8`  
**Qualification:** GitHub Actions `34443719080` — **success**

This file is the controlling restart entry point for Knowledge Core.

## Active accepted foundation

The following remain accepted and are not being rebuilt:

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`.
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`.
- RF-2 whole-`ResourceVersion` PostgreSQL lexical retrieval: `479a918762e919851e19fee3b36cc1d95e78f3e8`.
- Governed repository import RI-2: `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`.
- RI-3 persistence qualification: `9a167e67200c6bee2b7f4ed7b1dc91224d553390`.
- RI-4 intended-host persistence/recovery qualification and evidence.
- Audit-amended SR-1 contract: `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`.
- Architecture correction KC-D025 in `docs/architecture/knowledge-core/DECISIONS.md`.

Exact whole `ResourceVersion` artifacts remain canonical evidence. Repository source observations remain governed source/classification evidence. Derived retrieval state remains rebuildable and subordinate to those inputs.

The clean reset runtime checkpoint has no active SR-2 runtime/schema/test implementation. Compared with original accepted SR-1 commit `1d1313844aa4d224bd42c0888970a11e959d9501`, its runtime, API, storage models, and migration head are restored to the accepted pre-SR-2 baseline. The only test change is a maintenance correction that pins an RI-2 exact-Git-object fixture to its accepted RI-1 source commit instead of moving `HEAD`.

Qualification `34443719080` completed with:

- migrations through `0010_ri2`: passed;
- fast semantic suite: 48 passed, 1 guarded exact-corpus skip;
- PostgreSQL suite: 16 passed, 2 guarded exact-corpus skips;
- RI-4 local-host restart/replay qualification: passed.

The guarded corpus skips intentionally refuse to relabel later-edited documentation as earlier exact-source evidence; they are not SR-2 failures.

## SR-2 reset

The pre-audit SR-2 implementation commit:

`2c48a0e73c560fad62028776f375c94162e138be`

is **ABANDONED — DO NOT USE FOR IMPLEMENTATION, TEST DESIGN, MIGRATION DESIGN, OR DECISION-MAKING**.

It was built against SR-1 rules that were later corrected. Its code, tests, migration, API extensions, importer adapter, and real-pilot manifest have been removed from the active working tree. Git history is the only archive for that prototype.

Do not restore files from that commit, copy implementation patterns from it, or treat its tests as acceptance evidence. If a future investigation deliberately examines that commit, it is evidence of a rejected prototype only.

Any older wording that says the pre-audit candidate should be "aligned", "repaired", or "continued" is superseded by this clean-reset decision. KC-D025's architecture semantics remain accepted; the abandoned prototype does not.

## Active SR-1 rules for the new SR-2 build

The controlling contract is `SECTION_RETRIEVAL_SR1.md` as amended on 2026-09-10. Material rules include:

- Structural segmentation depends only on the exact canonical `ResourceVersion` artifact/media plus an exact structural segmentation profile.
- Governed lifecycle/source-ranking projection additionally depends on the exact governed observation/classification snapshot plus a retrieval-projection profile.
- Declared section lifecycle remains source-derived evidence.
- Effective lifecycle is the most restrictive of governed document lifecycle, applicable ancestor declarations, and the section's own declaration.
- A less-restrictive child declaration cannot promote effective lifecycle and is not rejected merely for being less restrictive.
- Ordinary prose, inline code, block quotes/quoted explanations, and fenced code that mention `kc:retrieval-lifecycle` remain ordinary content.
- A standalone non-fenced control-looking lifecycle comment that is malformed, misplaced, or duplicated fails lifecycle projection explicitly.
- An indivisible oversized fenced region or UTF-8 source line fails structural segmentation when no legal boundary exists; a final suffix within `hard_max_bytes` is emitted whole.
- Exact `ResourceVersion` identity is content-addressed within a logical Resource. A → B → A reuses the original A exact version and its structural segment identities under the same structural profile.
- Repository supersession/retirement-retain is historical retrieval classification, not privacy deletion.
- Privacy `RESTRICT`/`ERASE` fences serving access first; derivative cleanup is deterministic/idempotent reconciliation.

`SR2-G1` through `SR2-G22` in the amended SR-1 contract are the acceptance requirements for the new implementation.

## Restart order

A future SR-2 implementation chat must read, in this order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
5. accepted RF-2 and RI-2 runtime interfaces/tests needed for the bounded implementation
6. RI-1/RI-2 contract records only when exact repository-import behavior is relevant

Do not search Git history for SR-2 implementation guidance unless explicitly investigating the rejected prototype.

## Documentation hygiene

Obsolete handoff documents are not retained in the active tree merely for context. Git history is the archive.

Accepted RF/RI qualification documents remain only because they describe still-accepted foundation behavior or concrete qualification evidence. They do not override `CURRENT_STATE.md`, KC-D025, or the amended SR-1 contract on section retrieval.

## Next bounded task

Build SR-2 **from the amended contract**, using the accepted RF-2/RI-2 foundation as dependencies. Start with a fresh deterministic structural segmentation/projection design and synthetic acceptance tests. Do not copy the abandoned SR-2 implementation.

Before adding a migration or widening the runtime, define the smallest implementation slice needed to satisfy the amended gates and preserve accepted foundation invariants.

## Out of scope

Do not expand this phase into embeddings, vector search, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic classification/document-key assignment, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
