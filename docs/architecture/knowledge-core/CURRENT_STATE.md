# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **SR-2 Slices 1–2 accepted; physical lineage/storage decision next**  
**Clean reset runtime checkpoint:** `267fc28bd862ddd4ca22e61792d073853a1e51a8`  
**Clean reset qualification:** GitHub Actions `34443719080` — **success**  
**SR-2 Slice 1 checkpoint:** `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336`  
**SR-2 Slice 1 qualification:** GitHub Actions `34444560064` — **success**  
**SR-2 Slice 2 checkpoint:** `b9248ac6c0471743d218bb6df9720d92deb320c5`  
**SR-2 Slice 2 qualification:** GitHub Actions `34445248423` — **success**

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

The pre-audit SR-2 implementation commit `2c48a0e73c560fad62028776f375c94162e138be` is **ABANDONED — DO NOT USE FOR IMPLEMENTATION, TEST DESIGN, MIGRATION DESIGN, OR DECISION-MAKING**.

Its code, tests, migration, API extensions, importer adapter, and real-pilot manifest were removed from the active tree. Git history is only an archive for that rejected prototype. Do not restore or copy it.

## Active SR-1 rules

The controlling contract is `SECTION_RETRIEVAL_SR1.md` as amended on 2026-09-10. In particular:

- Structural segmentation depends only on exact canonical `ResourceVersion` bytes/media plus the exact structural profile.
- Governed lifecycle/source-ranking projection additionally depends on the exact governed observation/classification snapshot plus the retrieval-projection profile.
- Declared section lifecycle remains source-derived evidence.
- Effective lifecycle is the most restrictive of governed document lifecycle, applicable ancestor declarations, and the section's own declaration.
- Less-restrictive child declarations cannot promote effective lifecycle and are not rejected merely for being less restrictive.
- Prose, inline code, block quotes/quoted explanations, and fenced code mentioning `kc:retrieval-lifecycle` remain ordinary content.
- Standalone non-fenced attempted controls that are malformed, misplaced, or duplicated fail lifecycle projection.
- Indivisible oversized fenced regions or UTF-8 source lines fail structural segmentation when no legal boundary exists; a fitting final suffix is emitted whole.
- Exact `ResourceVersion` identity is content-addressed within a logical Resource; A -> B -> A reuses A and its structural keys under the same structural profile.
- Repository supersession/retirement-retain is historical retrieval classification, not privacy deletion.
- Privacy `RESTRICT`/`ERASE` fences serving access first; derivative cleanup is deterministic/idempotent reconciliation.

`SR2-G1` through `SR2-G22` remain the final acceptance requirements.

## SR-2 Slice 1 — deterministic structural segmentation

Accepted checkpoint: `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336`.

Files introduced:

- `components/knowledge-core/knowledge_core/application/segmentation.py`
- `components/knowledge-core/tests/test_sr2_structural_segmentation.py`

The structural stage is lifecycle-blind and implements strict UTF-8, exact byte/line preservation, ATX headings, fence awareness, preamble/section/document blocks, deterministic continuation splitting, exact reconstruction/slice SHA-256, deterministic segment keys, and empty-document handling.

Synthetic coverage exercises structural portions of SR2-G2, G3, G4, G5, G6, G7, G8, and G21.

Qualification `34444560064`:

- migrations through `0010_ri2`: passed;
- fast suite: **54 passed**, 1 guarded exact-corpus skip;
- PostgreSQL suite: **16 passed**, 2 guarded exact-corpus skips;
- RI-4 restart/replay: passed.

## SR-2 Slice 2 — governed lifecycle/control projection

Accepted runtime checkpoint: `b9248ac6c0471743d218bb6df9720d92deb320c5`.

Slice 2 changes relative to the Slice 1 state checkpoint `6da47661ab883328a5b825456cfe1b99aeb41b91` are exactly:

- modified `components/knowledge-core/knowledge_core/application/segmentation.py` to expose the same deterministic Markdown heading/fence scan for reuse by lifecycle projection;
- added `components/knowledge-core/knowledge_core/application/lifecycle_projection.py`;
- added `components/knowledge-core/tests/test_sr2_lifecycle_projection.py`.

No database schema, migration, API, retrieval service, storage model, or repository-import publication behavior changed.

The pure projection stage:

- accepts an explicit governed observation identity and the governed retrieval metadata required by SR-1;
- validates that the observation and structural parent refer to the same exact `ResourceVersion`;
- binds the retrieval projection profile to the exact structural profile digest;
- recognizes only exact eligible standalone lifecycle controls;
- treats prose, inline, quoted, fenced, and plain-text control-like strings as ordinary content;
- fails malformed, misplaced, duplicate, or preamble standalone attempted controls;
- preserves each section's own declared lifecycle and directive source coordinates;
- computes effective lifecycle as the most restrictive document + ancestor + own value;
- preserves less-restrictive child declarations while preventing them from promoting effective lifecycle;
- records the source(s) controlling the effective restriction without inventing arbitrary tie precedence;
- reprojects a later parent downgrade over unchanged structural segments without changing structural segment keys;
- performs no heading-name lifecycle inference.

Synthetic tests cover the lifecycle/control portions of SR2-G7, G11, and G12 and the structural/projection separation introduced by KC-D025.

Qualification `34445248423`:

- migrations through `0010_ri2`: passed;
- fast suite: **66 passed**, 1 guarded exact-corpus skip;
- PostgreSQL suite: **16 passed**, 2 guarded exact-corpus skips;
- RI-4 restart/replay: passed.

The guarded exact-corpus skips intentionally refuse to relabel later-edited documentation as earlier exact-source evidence; they are not SR-2 failures.

## Governed observation evidence already available

Accepted RI-2 stores immutable `RepositorySourceObservation.observation_id` plus manifest/document identity, source repository key, exact commit/path/blob, exact `resource_version_ref`, classification, document retrieval lifecycle, authority rank, and rationale.

SR-1 requires the exact governed snapshot set used by a serving generation to be recoverable. For repository import, the physical reference may use immutable observation ID, manifest digest + document key, or another exact stable reference. `resource_version_ref` alone is insufficient.

The existing generic `kc_derived.generation_source` records canonical `KnowledgeRef` sources and revisions; it cannot directly identify `kc_control.repository_source_observation.observation_id` because repository observations are control/governance records rather than canonical `KnowledgeRef` rows.

## Restart order

Read, in order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
5. accepted generation, RF-2, RI-2, and deletion interfaces needed for the bounded next slice

Do not search Git history for SR-2 implementation guidance unless explicitly investigating the rejected prototype.

## Next bounded task — physical lineage/storage decision before migration

Do not add migration `0011` until the physical lineage representation is chosen explicitly.

The next design must satisfy all of these simultaneously:

- keep generic `GenerationSource` semantics intact unless there is a compelling reason to broaden them;
- make the exact governed observation/classification snapshot set recoverable independently of segment search ranking;
- bind each derived parent/segment to its exact governed snapshot;
- use accepted `RepositorySourceObservation.observation_id` for repository-imported sources rather than inventing a parallel authoritative observation store;
- preserve a path for other governed text-source types without pretending an arbitrary UUID is durable evidence;
- remain derived/rebuildable and subordinate to canonical/governed evidence;
- survive deterministic derivative cleanup semantics without confusing historical supersession with privacy erasure.

After that representation is accepted, the next implementation slice may add the minimum derived schema/model/migration and PostgreSQL tests needed to prove lineage and storage invariants before retrieval cutover.

## Out of scope

Do not expand this phase into embeddings, vector search, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic classification/document-key assignment, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
