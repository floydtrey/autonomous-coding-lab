# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **SR-2 Slices 1–4 accepted; segment-generation persistence next**

**Clean reset runtime checkpoint:** `267fc28bd862ddd4ca22e61792d073853a1e51a8` — Actions `34443719080` success  
**SR-2 Slice 1:** `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336` — Actions `34444560064` success  
**SR-2 Slice 2:** `b9248ac6c0471743d218bb6df9720d92deb320c5` — Actions `34445248423` success  
**SR-2 Slice 3:** `70dde361cd62f507f54b5e42e3ef12cea27ce11f` — Actions `34446983351` success  
**SR-2 Slice 4:** `33c83e99728de9cab9a4eede8030fa733a4a5beb` — Actions `34448019988` success

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

Exact whole `ResourceVersion` artifacts remain canonical evidence. Repository source observations and governing import receipts/manifests remain governed source/classification evidence. SR-2 structures, lineage rows, and search projections remain derived and rebuildable.

## Rejected prototype boundary

Commit `2c48a0e73c560fad62028776f375c94162e138be` is **ABANDONED — DO NOT USE FOR IMPLEMENTATION, TEST DESIGN, MIGRATION DESIGN, OR DECISION-MAKING**.

Do not restore files or implementation patterns from that commit. The active SR-2 implementation was rebuilt from the amended contract.

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
- A serving SR-2 generation must make the exact governed snapshot set recoverable; `resource_version_ref` alone is insufficient.

`SR2-G1` through `SR2-G22` in the amended SR-1 contract remain the final acceptance requirements.

## SR-2 Slice 1 — deterministic structural segmentation

Accepted checkpoint: `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336`.

Implemented in:

- `components/knowledge-core/knowledge_core/application/segmentation.py`
- `components/knowledge-core/tests/test_sr2_structural_segmentation.py`

The stage is lifecycle-blind. It provides strict UTF-8 handling, exact LF/CRLF coordinates, ATX/fence-aware structure, deterministic preamble/section/document blocks, deterministic continuation splitting, gap-free reconstruction, slice SHA-256, deterministic segment keys, and empty-document handling.

Qualification: **54 fast passed**, **16 PostgreSQL passed**, RI-4 restart/replay passed.

## SR-2 Slice 2 — governed lifecycle/control projection

Accepted checkpoint: `b9248ac6c0471743d218bb6df9720d92deb320c5`.

Implemented in:

- shared structural Markdown scan in `application/segmentation.py`;
- `application/lifecycle_projection.py`;
- `tests/test_sr2_lifecycle_projection.py`.

The projection stage preserves source declarations and exact directive coordinates, computes monotone effective lifecycle, rejects only genuine standalone attempted-control errors, remains structurally identity-neutral, and carries an explicit governed observation identity.

Qualification: **66 fast passed**, **16 PostgreSQL passed**, RI-4 restart/replay passed.

## SR-2 Slice 3 — exact governed projection lineage storage

Accepted checkpoint: `70dde361cd62f507f54b5e42e3ef12cea27ce11f`.

Added:

- `application/projection_lineage.py`
- `storage/section_retrieval_models.py`
- migration `0011_sr2_projection_lineage.py`
- `tests/test_sr2_projection_lineage.py`
- registration of the new storage model in `storage/database.py`.

The derived table `kc_derived.text_generation_source` contains exactly:

- `generation_id`
- `resource_version_ref`
- `source_observation_id`
- `governing_manifest_digest`
- `projection_snapshot_digest`

Primary identity is `(generation_id, resource_version_ref)`. Foreign keys independently bind the exact derived generation, exact canonical `ResourceVersion`, immutable RI-2 `RepositorySourceObservation`, and governing `RepositoryImportReceipt`/manifest.

`projection_snapshot_digest` binds canonical JSON of the effective document-level projection inputs, including both the source observation's own manifest identity and the later governing manifest identity. The table does not copy the source observation or manifest payload.

Qualification: **70 fast passed**, **17 PostgreSQL passed**, RI-4 restart/replay passed.

## SR-2 Slice 4 — governed source selection from RI-2 evidence

Accepted checkpoint: `33c83e99728de9cab9a4eede8030fa733a4a5beb`.

Added:

- `components/knowledge-core/knowledge_core/application/governed_source_selection.py`
- `components/knowledge-core/tests/test_sr2_governed_source_selection.py`

The resolver consumes persisted RI-2 receipts/manifests and immutable `RepositorySourceObservation` rows. It does not modify accepted RI-2/RF-2 publication behavior.

The resolver:

- reconstructs provenance through the explicit `previous_manifest_digest` chain rather than settlement timestamps or UUID ordering;
- accepts only an `applying` or `settled` governing receipt and requires every predecessor to be settled;
- recomputes and verifies each persisted manifest digest before trusting its payload;
- verifies source-repository and predecessor-chain continuity;
- verifies each observation against the exact active manifest entry that created it;
- emits explicit roles `current`, `prior_version`, and `retirement_retain`;
- keeps the source observation's original `manifest_digest` distinct from the later `governing_manifest_digest`;
- preserves the immutable source observation while projecting prior/retained versions as effective document lifecycle `superseded`;
- constructs the exact `GovernedRetrievalObservation` required by lifecycle projection;
- computes the deterministic Slice-3 `projection_snapshot_digest` for every selected version;
- deduplicates by exact `ResourceVersion` identity and fails closed on contradictory selection;
- fails closed if the governing receipt, manifest chain, observation, or source-manifest relationship cannot be reconstructed exactly.

Qualification `34448019988`:

- migrations through `0011_sr2_lineage`: passed;
- fast suite: **70 passed**, 1 guarded exact-corpus skip;
- PostgreSQL suite: **20 passed**, 2 guarded exact-corpus skips;
- RI-4 local-host restart/replay qualification: passed.

Slice-4 acceptance specifically proved:

- a new current version plus its prior version and a separate retirement-retain document resolve to three exact governed projection sources;
- repeated reconstruction of the same governing manifest produces the same projection snapshot digests;
- A -> B -> A reuses A's original canonical `ResourceVersion` and structural segment keys;
- the returning A observation and later governing manifest produce a new projection snapshot digest rather than rewriting the original observation;
- unknown or tampered governing evidence fails closed.

The guarded exact-corpus skips refuse to relabel later-edited documentation as earlier pinned evidence; they are not SR-2 failures.

## Restart order

Read, in order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
5. accepted generation, RF-2, RI-2, deletion, and SR-2 Slice 1–4 interfaces needed for the bounded next slice

Do not search Git history for SR-2 implementation guidance unless explicitly investigating the rejected prototype.

## Next bounded task — SR-2 Slice 5: segment-generation persistence

Build the first SR-2 derived generation from the already-proven structural, lifecycle, lineage, and governed-source layers. Do not cut serving retrieval over yet.

Slice 5 should:

- consume `resolve_governed_projection_sources()` rather than reconstructing repository provenance again;
- load and verify each exact canonical `ResourceVersion` artifact before segmentation;
- run structural segmentation and governed lifecycle projection using the already-qualified profiles;
- create one derived text generation under a new SR-2 model/version identity;
- persist one `text_generation_source` lineage row per selected `ResourceVersion` using the exact Slice-4 source observation, governing manifest, and projection snapshot digest;
- add the minimum segment-derived storage needed to preserve segment coordinates, heading path, structural key/digest, declared/effective lifecycle provenance, inherited authority/source metadata, and PostgreSQL lexical search projection without copying canonical body text;
- verify the entire candidate generation before settlement and fail/stale the candidate on any mismatch;
- preserve RF-2 as the serving retrieval path throughout this slice.

Do not yet modify the public retrieval API or switch search serving to segment rows. Cutover and serving behavior belong to a later bounded slice after generation persistence is independently qualified.

## Out of scope

Do not expand SR-2 into embeddings, vector search, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic classification/document-key assignment, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
