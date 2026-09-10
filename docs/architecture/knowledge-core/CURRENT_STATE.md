# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **SR-2 Slice 1 accepted; lifecycle projection next**  
**Clean reset runtime checkpoint:** `267fc28bd862ddd4ca22e61792d073853a1e51a8`  
**Clean reset qualification:** GitHub Actions `34443719080` — **success**  
**SR-2 Slice 1 checkpoint:** `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336`  
**SR-2 Slice 1 qualification:** GitHub Actions `34444560064` — **success**

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

## Abandoned prototype boundary

The pre-audit SR-2 implementation commit:

`2c48a0e73c560fad62028776f375c94162e138be`

is **ABANDONED — DO NOT USE FOR IMPLEMENTATION, TEST DESIGN, MIGRATION DESIGN, OR DECISION-MAKING**.

Its code, tests, migration, API extensions, importer adapter, and real-pilot manifest were removed from the active working tree. Git history is the only archive for that rejected prototype. Do not restore or copy it.

## Active SR-1 rules

The controlling contract is `SECTION_RETRIEVAL_SR1.md` as amended on 2026-09-10. Material rules include:

- Structural segmentation depends only on exact canonical `ResourceVersion` bytes/media plus an exact structural profile.
- Governed lifecycle/source-ranking projection additionally depends on the exact governed observation/classification snapshot plus a retrieval-projection profile.
- Declared section lifecycle remains source-derived evidence.
- Effective lifecycle is the most restrictive of governed document lifecycle, applicable ancestor declarations, and the section's own declaration.
- A less-restrictive child declaration cannot promote effective lifecycle and is not rejected merely for being less restrictive.
- Ordinary prose, inline code, block quotes/quoted explanations, and fenced code mentioning `kc:retrieval-lifecycle` remain ordinary content.
- A standalone non-fenced control-looking lifecycle comment that is malformed, misplaced, or duplicated fails lifecycle projection explicitly.
- An indivisible oversized fenced region or UTF-8 source line fails structural segmentation when no legal boundary exists; a final suffix within `hard_max_bytes` is emitted whole.
- Exact `ResourceVersion` identity is content-addressed within a logical Resource; A -> B -> A reuses the original A exact version and structural keys under the same structural profile.
- Repository supersession/retirement-retain is historical retrieval classification, not privacy deletion.
- Privacy `RESTRICT`/`ERASE` fences serving access first; derivative cleanup is deterministic/idempotent reconciliation.

`SR2-G1` through `SR2-G22` remain the final acceptance requirements.

## SR-2 Slice 1 — deterministic structural segmentation

Checkpoint `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336` adds only:

- `components/knowledge-core/knowledge_core/application/segmentation.py`
- `components/knowledge-core/tests/test_sr2_structural_segmentation.py`

No existing runtime, API, storage model, migration, retrieval service, or repository-import file was changed.

The new structural stage is intentionally lifecycle-blind. It consumes only exact bytes, media type, parent `resource_version_ref`, and the structural segmentation profile. It implements:

- strict UTF-8 validation for supported `text/markdown` and `text/plain`;
- exact LF/CRLF byte preservation and line coordinates;
- deterministic ATX heading structure with heading paths;
- deterministic fenced-code awareness;
- preamble/section/document base blocks;
- fixed soft/hard byte continuation rules;
- no split inside a source line or fenced region;
- deterministic failure when no legal boundary exists;
- exact gap-free source reconstruction and per-slice SHA-256;
- deterministic structural segment keys bound to parent exact version, coordinates, slice digest, ordinal, and structural profile digest;
- deterministic empty-document handling.

Synthetic tests cover the structural portions of SR2-G2, G3, G4, G5, G6, G7, G8, and G21. They also prove that literal lifecycle-control discussion does not affect structural segmentation.

Qualification `34444560064` completed with:

- migrations through `0010_ri2`: passed;
- fast semantic suite: **54 passed**, 1 guarded exact-corpus skip;
- PostgreSQL suite: **16 passed**, 2 guarded exact-corpus skips;
- RI-4 local-host restart/replay qualification: passed.

The guarded corpus skips intentionally refuse to relabel later-edited documentation as earlier exact-source evidence and are not SR-2 failures.

## Governed observation input already available

Accepted RI-2 already stores immutable `RepositorySourceObservation.observation_id` plus manifest/document identity, exact source commit/path/blob, exact `resource_version_ref`, classification, retrieval lifecycle, authority rank, and rationale. The next SR-2 slice should consume that accepted evidence rather than inventing a parallel observation store.

Do not modify RF-2 `TextIndexSource`, PostgreSQL schema, or repository-import publication merely to start lifecycle parsing. First prove lifecycle/control semantics as a pure projection layer.

## Restart order

Read, in this order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
5. accepted RF-2/RI-2 interfaces needed for the bounded slice

Do not search Git history for SR-2 implementation guidance unless explicitly investigating the rejected prototype.

## Next bounded task

**SR-2 Slice 2: pure governed lifecycle/control projection plus synthetic tests.**

Build a separate projection stage over the already-proven structural segmentation. It should:

- recognize only exact eligible standalone lifecycle declarations;
- treat prose/inline/quoted/fenced mentions as ordinary content;
- fail malformed/misplaced/duplicate standalone attempted controls;
- preserve own declarations and exact directive coordinates;
- compute effective lifecycle as the most restrictive document + ancestor + own state;
- prove parent downgrade and ancestor restriction without changing structural keys;
- carry an explicit governed observation identity in the projection input/output.

Do **not** add a migration, segment search table, API changes, repository-import publication changes, or retrieval cutover in Slice 2. Those belong to later slices after pure projection behavior is accepted.

## Out of scope

Do not expand this phase into embeddings, vector search, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic classification/document-key assignment, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
