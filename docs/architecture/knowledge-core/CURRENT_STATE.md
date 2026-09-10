# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **SR-2 G1–G22 independently green and checkpointed; intended-host SR-2 restart/recovery qualification is next**

**Clean reset runtime checkpoint:** `267fc28bd862ddd4ca22e61792d073853a1e51a8` — Actions `34443719080` success  
**SR-2 Slice 1:** `c0a4ad89347ff62bc2259b5c20b742eb6fc6c336` — Actions `34444560064` success  
**SR-2 Slice 2:** `b9248ac6c0471743d218bb6df9720d92deb320c5` — Actions `34445248423` success  
**SR-2 Slice 3:** `70dde361cd62f507f54b5e42e3ef12cea27ce11f` — Actions `34446983351` success  
**SR-2 Slice 4:** `33c83e99728de9cab9a4eede8030fa733a4a5beb` — Actions `34448019988` success  
**SR-2 Slice 5:** `ee285a5301bd81c9bd011799c7150ce3d081e11a` — Actions `34450118281` success  
**SR-2 Slice 6:** `1534dba10757612485821bf566c6fdccffde06c2` — Actions `34452778382` success  
**Slice 6 state checkpoint:** `d540f206bb2c7a94eeb14f642b3a87d7ff81486e`  
**Slice 7 pause handoff introduced:** `8fafb1603649a2af64f2122c9b66e7fbae9f4ada`  
**Slice 7 G1–G21 qualified runtime/test checkpoint:** `7570425231c0f1804c800ad4c6809f6261d82416` — Actions `34457756458` success  
**SR2-G22 qualified runtime/test/workflow checkpoint:** `c75a6be2e832bdc29fda0e4a6eab7de28da90668` — Actions `34462565404` success

This file is the controlling restart entry point for Knowledge Core. Git history is the archive; active implementation guidance belongs here and in the controlling contracts.

## Accepted foundation

The following remain accepted and are not being rebuilt:

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`.
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`.
- RF-2 whole-`ResourceVersion` PostgreSQL lexical retrieval: `479a918762e919851e19fee3b36cc1d95e78f3e8`.
- Governed repository import RI-2: `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad`.
- RI-3 persistence qualification: `9a167e67200c6bee2b7f4ed7b1dc91224d553390`.
- RI-4 intended-host persistence/recovery qualification and evidence for the RF-2 path.
- Audit-amended SR-1 contract: `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`.
- Architecture correction KC-D025 in `docs/architecture/knowledge-core/DECISIONS.md`.
- G1–G21 qualification map: `docs/architecture/knowledge-core/SR2_G1_G21_COVERAGE_MATRIX.md`.
- G22 real-document qualification: `docs/architecture/knowledge-core/SR2_G22_QUALIFICATION.md`.
- Exact G22 corpus manifest: `docs/architecture/knowledge-core/SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json`.

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

`SR2-G1` through `SR2-G22` in the amended SR-1 contract are now independently qualified in CI. Intended-host qualification of the SR-2 segment-serving path remains outstanding.

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

### Slice 7 — G1–G21 qualification closure

Qualified runtime/test/workflow checkpoint `7570425231c0f1804c800ad4c6809f6261d82416`.

Slice 7 published the explicit cross-boundary acceptance closure without changing production architecture or implementation code:

- `tests/test_sr2_acceptance_closure.py` adds the missing G1–G21 qualification fixtures identified by the completed audit;
- `SR2_G1_G21_COVERAGE_MATRIX.md` maps every amended gate G1–G21 to committed proof;
- `sr2_real_pilot` is registered as the dedicated G22 marker;
- both G1–G21 CI selectors explicitly include `not sr2_real_pilot`, mechanically excluding G22;
- G16 exercises reachable ranking discriminators and repeated stable ordering while separately locking the complete configured total order through final `segment_key`, without fabricating impossible duplicate canonical segment identities;
- G1/G7 rebuild qualification proves complete derived regeneration is reproducible while canonical versions, artifact bytes, and governed observations remain unchanged;
- G8 covers path-only re-observation plus repeated identical slices at distinct coordinates;
- G12 covers the required restrictive lifecycle cases through publication and verifies current-to-superseded re-projection reuses structural keys;
- G13/G17/G18 distinguish historical retirement retention from privacy fencing, prove stale derived rows cannot consume a result limit, and prove repeated derivative cleanup is idempotent;
- G21 proves structural-profile versus projection-only replacement generations remain distinct and canonical evidence is not mutated.

GitHub Actions `34457756458` qualified that exact checkpoint:

- migrations through `0012_sr2_segments`: passed;
- fast G1–G21 suite: **75 passed**, 1 guarded older RF-2 exact-corpus skip, 38 deselected;
- PostgreSQL G1–G21 suite: **36 passed**, 2 guarded older RF-2 exact-corpus skips, 76 deselected;
- RI-4 restart/replay rehearsal: **passed** with application reconstruction, artifact integrity, current/historical retrieval, exact replay, PostgreSQL restart, and provenance verification all true.

No G1–G21 failure exposed a production defect or an architecture ambiguity, so no production repair or design change was made during Slice 7 closure.

The guarded `test_real_corpus_pilot.py` skips remain the older RF-2 immutable pilot refusing to relabel changed documentation as its historical evidence. They are not SR2-G22.

### SR2-G22 — tiny pinned real-document pilot

Qualified runtime/test/workflow checkpoint `c75a6be2e832bdc29fda0e4a6eab7de28da90668`.

G22 pins exactly three real Knowledge Core Markdown documents from source commit `bb42835442c03478da2b61c3f79b1c41c26e4e92` in `SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json` and exercises the accepted SR-2 import/segmentation/projection/publication/retrieval machinery under the dedicated `sr2_real_pilot` marker.

The pilot proves exact governed observation lineage; exact structural reconstruction from the pinned Git objects; harmless literal discussion of `kc:retrieval-lifecycle`; no lifecycle inference from historical/temporal prose; parent-superseded historical behavior; import of only the three allowlisted files; exact source provenance; and repeated stable retrieval identities.

Actions `34462565404` passed:

- migrations through `0012_sr2_segments`;
- fast G1–G21 selector: **75 passed**, 1 guarded RF-2 skip, 39 deselected;
- PostgreSQL G1–G21 selector: **36 passed**, 2 guarded RF-2 skips, 77 deselected;
- separate G22 selector: **1 passed**, 114 deselected;
- RI-4 restart/replay rehearsal: **success**, with application reconstruction, artifact integrity, current/historical retrieval, exact replay, PostgreSQL restart, and provenance verification all true.

The initial candidate `f263f72899e35afe48ec41c04092d2ee3e7a3375` failed only because a four-term pilot query incorrectly required terms spanning multiple segments to match within one segment. The test-only correction at `c75a6be2e832bdc29fda0e4a6eab7de28da90668` used a segment-local query. No production code, schema, migration, architecture rule, or KC-D025 decision changed, and no architecture ambiguity was exposed.

The durable G22 evidence is `docs/architecture/knowledge-core/SR2_G22_QUALIFICATION.md`.

## Restart order

Read, in order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/SR2_G1_G21_COVERAGE_MATRIX.md`
5. `docs/architecture/knowledge-core/SR2_G22_QUALIFICATION.md`
6. `docs/architecture/knowledge-core/SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json`
7. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
8. accepted RI-4 persistence/recovery interfaces and SR-2 Slice 1–7 interfaces needed for the bounded host qualification

`SR2_SLICE7_PAUSE_HANDOFF.md` is retained as historical restart evidence for the pre-closure pause; it is not active task authority.

Do not search Git history or orphaned draft objects for SR-2 implementation guidance unless explicitly investigating the rejected prototype.

## Next bounded task — intended-host SR-2 restart/recovery qualification

G1–G22 are now green and checkpointed. The next task is to qualify the accepted SR-2 **segment-serving** path on the intended Windows/PostgreSQL host.

Do not relabel the existing RI-4 intended-host run as SR-2 evidence. RI-4 successfully qualified persistence/recovery for its bounded RF-2 whole-`ResourceVersion` retrieval path; its own accepted documentation explicitly does not claim chunking/section retrieval.

A bounded SR-2 host qualification should reuse the accepted persistence/recovery discipline where applicable, while exercising the SR-2 section-aware import/generation/publication/serving path and exact G22-style provenance. Do not broaden it into machine-reboot persistence, backup/restore, production deployment, broad corpus import, embeddings/RAG, or autonomous execution.

If host qualification exposes a genuine architecture ambiguity, stop and return to the decision process rather than silently choosing a new design.

## Intended-host boundary

**User-PC testing is now required for the next qualification.**

G22 has independently passed and is checkpointed. The prior RI-4 Windows command is useful as persistence/recovery precedent, but it is not sufficient by itself because it serves RF-2 whole-document rows. Before asking the user to execute a command, construct or identify a bounded SR-2 host qualification entrypoint that actually exercises segment serving.

The next sequence is:

`G1–G22 green/checkpointed -> bounded SR-2 host qualification entrypoint -> intended Windows/PostgreSQL execution -> durable host evidence`

## Out of scope

Do not expand SR-2 into embeddings, vector search, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic classification/document-key assignment, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
