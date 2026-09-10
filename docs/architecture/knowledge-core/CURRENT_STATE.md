# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **SR-2 Slices 1–5 accepted; atomic serving cutover next**

**Clean reset runtime checkpoint:** `267fc28bd862ddd4ca22e61792d073853a1e51a8` — Actions `34443719080` success  
**SR-2 Slice 1:** `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336` — Actions `34444560064` success  
**SR-2 Slice 2:** `b9248ac6c0471743d218bb6df9720d92deb320c5` — Actions `34445248423` success  
**SR-2 Slice 3:** `70dde361cd62f507f54b5e42e3ef12cea27ce11f` — Actions `34446983351` success  
**SR-2 Slice 4:** `33c83e99728de9cab9a4eede8030fa733a4a5beb` — Actions `34448019988` success  
**SR-2 Slice 5:** `ee285a5301bd81c9bd011799c7150ce3d081e11a` — Actions `34450118281` success

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

## Research-alignment checkpoint — Slices 1–4

Before Slice 5, Slices 1–4 were re-audited against the completed Knowledge Architecture Evidence Campaign, especially:

- `docs/research/knowledge-architecture/CONCEPTUAL_ARCHITECTURE_SYNTHESIS.md`;
- `docs/research/knowledge-architecture/invariants.md`;
- `docs/research/knowledge-architecture/gaps/formal-provenance-evidence-lineage.md`;
- `docs/research/knowledge-architecture/gaps/resource-artifact-identity-lineage.md`.

No Slice 1–4 redesign was required. The implementation remains aligned with the research requirements that canonical source evidence and derived projections remain distinct; exact immutable source versions are bound to consequential derivations; logical source identity, exact observed version, derived-record identity, and presentation identity remain separate; provenance is explicit lineage rather than inferred metadata; current/historical lifecycle is explicit; replacement projections are built and validated before cutover; and derived indexes remain generation/profile-bound and rebuildable.

The audit identified one Slice-5 persistence guardrail: an opaque aggregate generation `config_digest` alone is insufficient for direct recovery of non-default structural/projection profile identity. Slice 5 therefore persists an explicit generation-level SR-2 profile record while leaving the accepted Slice-3 five-field governed-source lineage unchanged.

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

`application/segmentation.py` provides lifecycle-blind strict UTF-8 segmentation, exact byte/line coordinates, ATX/fence-aware structure, deterministic continuation splitting, gap-free reconstruction, exact slice SHA-256, deterministic structural segment keys, and empty-document behavior.

### Slice 2 — governed lifecycle/control projection

Checkpoint `b9248ac6c0471743d218bb6df9720d92deb320c5`.

`application/lifecycle_projection.py` preserves source declarations and coordinates, computes monotone effective lifecycle, rejects genuine standalone attempted-control errors, remains structurally identity-neutral, and binds an explicit governed observation identity plus retrieval-projection profile.

### Slice 3 — exact governed projection lineage storage

Checkpoint `70dde361cd62f507f54b5e42e3ef12cea27ce11f`.

`kc_derived.text_generation_source` remains exactly the accepted five-field lineage table:

- `generation_id`
- `resource_version_ref`
- `source_observation_id`
- `governing_manifest_digest`
- `projection_snapshot_digest`

It binds the derived generation, exact canonical version, immutable RI-2 observation, governing manifest/receipt, and deterministic effective projection snapshot without copying the observation/manifest payload.

### Slice 4 — governed source selection

Checkpoint `33c83e99728de9cab9a4eede8030fa733a4a5beb`.

`application/governed_source_selection.py` reconstructs exact current, prior-version, and retirement-retain source snapshots through the explicit RI-2 manifest chain, not timestamps or UUID ordering. It verifies every manifest/observation relationship, preserves immutable source observations, computes effective governed projection snapshots, proves A -> B -> A exact-version/structural-key reuse, and fails closed on unreconstructable evidence.

### Slice 5 — validated segment-generation persistence

Checkpoint `ee285a5301bd81c9bd011799c7150ce3d081e11a`.

Added:

- `application/section_generation.py`;
- migration `0012_sr2_segment_projection.py`;
- `tests/test_sr2_segment_generation.py`;
- SR-2 segment/profile models in `storage/section_retrieval_models.py`.

Slice 5 adds two derived persistence structures without changing RF-2 serving:

1. `kc_derived.text_generation_profile` — one row per SR-2 candidate generation carrying the exact structural-profile ID/digest, retrieval-projection profile ID/digest, and aggregate generation-config digest.
2. `kc_derived.resource_segment_text_search` — segment coordinates, structural identity/digest, heading path, declared/effective lifecycle provenance, inherited governed source/ranking annotations, and weighted PostgreSQL `tsvector`, with no copied canonical segment body.

Each segment row has a composite foreign key to its exact `(generation_id, resource_version_ref)` `text_generation_source` lineage row. The candidate generation also uses generic `GenerationSource` for exact canonical `ResourceVersion`/revision lineage.

`SectionGenerationKnowledgeKernel.build_segment_generation_candidate()`:

- consumes the Slice-4 resolver;
- verifies exact ResourceVersion bytes, byte size, SHA-256 and governed Git-blob identity before segmentation;
- applies the accepted structural and lifecycle profiles;
- creates a new `DerivedKind.TEXT` generation with explicit SR-2 model/version/config identity;
- stores profile identity, exact governed source lineage, and segment lexical projections;
- removes recognized lifecycle declaration text from local lexical weight A and adds heading-path context at weight B;
- recomputes and validates the complete candidate from authoritative inputs;
- marks any post-start invalid candidate stale;
- deliberately leaves a successful candidate in `BUILDING` state and does not settle/cut it over.

No legacy whole-document `ResourceTextSearch` compatibility rows are copied into an SR-2 candidate. RF-2 remains the sole current/serving text generation throughout Slice 5.

Qualification `34450118281`:

- migrations through `0012_sr2_segments`: passed;
- fast suite: **71 passed**, 1 guarded exact-corpus skip;
- PostgreSQL suite: **25 passed**, 2 guarded exact-corpus skips;
- RI-4 intended-host restart/replay: passed.

The guarded exact-corpus skips refuse to relabel later-edited documentation as earlier pinned evidence; they are not SR-2 failures.

## Restart order

Read, in order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
5. accepted generation, RF-2, RI-2, deletion, and SR-2 Slice 1–5 interfaces needed for the bounded next slice

Do not search Git history for SR-2 implementation guidance unless explicitly investigating the rejected prototype.

## Next bounded task — SR-2 Slice 6: atomic cutover and serving integration

Do not treat the existence of a validated `BUILDING` SR-2 candidate as serving authorization.

Before SR-2 segment rows may serve, Slice 6 must:

- preserve RF-2 serving until a complete SR-2 candidate is revalidated immediately before publication;
- make repository-import receipt settlement and SR-2 generation promotion an atomic publication boundary so a crash cannot leave a `current` SR-2 generation governed by an `applying` receipt or a `settled` receipt pointing to a non-current/incomplete generation;
- preserve the generic generation out-of-order/late-finisher fence;
- extend privacy derivative reconciliation so restricted exact/logical parent resources remove or suppress their SR-2 segment derivatives before segment serving is enabled;
- retain mandatory serving-time parent `ResourceVersion` eligibility checks as defense in depth;
- make `search_text` dispatch by the current text-generation implementation identity: legacy RF-2 generations use whole-document rows; accepted SR-2 generations use only segment rows; never mix both in one response;
- implement deterministic SR-1 segment ranking and current/unknown/superseded filtering with `limit` applied after parent eligibility;
- expose the required segment and generation/profile provenance through the bounded retrieval response without exposing body copies, DB credentials, artifact paths, or internal control data;
- prove RF-2 -> SR-2 cutover has no serving gap and a failed/late candidate cannot replace a newer current generation.

Do not run the G22 real-document pilot until the synthetic/PostgreSQL G1–G21 acceptance work is complete and green.

## Out of scope

Do not expand SR-2 into embeddings, vector search, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic classification/document-key assignment, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
