# Knowledge Core Current State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**PostgreSQL qualification:** `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`  
**RF-2 retrieval:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**First curated real-corpus pilot:** `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`  
**RI-1 design:** `f7f12c04163ecbe3b6143191008cf393726b8def`  
**RI-2 governed importer:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**RI-3 application-process persistence:** final validated checkpoint `9a167e67200c6bee2b7f4ed7b1dc91224d553390` — CI `34418080815`  
**RI-3 final evidence-only checkpoint:** `3d12f205d15c310bce0718c56c0866befccd90ec`  
**RI-4 host harness:** `934850d5830d4a5d89ec32b04630435a027e816f` — CI rehearsal `34418809968`  
**RI-4 intended-host evidence:** `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md` — **success**  
**SR-1 design:** `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — **complete, design only**  
**Next separately authorized phase:** `SR-2 — deterministic section-retrieval implementation and qualification`  
**Status:** **Kernel V1 remains frozen. RF-2, RI-2, RI-3, and RI-4 are accepted. SR-1 is complete as a design/acceptance contract only. Exact whole ResourceVersions remain canonical evidence; no section-segmentation code, schema, migration, or segment index has been implemented. No broad or production corpus has been imported.**

This is the controlling branch-specific state.

## Accepted foundation

Stable governed repository document identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

RF-2 remains the accepted implemented PostgreSQL lexical-retrieval baseline. It retrieves exact whole `ResourceVersion` documents with explicit lifecycle/authority metadata, deterministic ranking, current-generation-only serving, exact provenance, and serving-time restriction/deletion fences.

RI-2 remains the accepted governed repository-import implementation: exact SHA-1 Git source verification, explicit Manifest V2 allowlists, manifest chaining, omission safety, stable edit/rename identity, explicit retirement, stale source/state rejection, generation publication fencing, exact replay, and service-only repository access.

RI-3 proves that accepted import/generation/artifact state survives complete reconstruction of the Knowledge Core application in a separate Python process while the same PostgreSQL database and artifact directory remain intact.

RI-4 proves the bounded intended-host restart/recovery case: PostgreSQL restart with its persistent Docker volume retained, reconstruction of the application process, reuse of the persistent artifact directory, exact replay, current/historical retrieval, artifact integrity, and provenance continuity.

## RI-4 — local-host persistence/recovery qualification — accepted

The fixed RI-4 manifest pins exactly three Markdown files at source commit `3d12f205d15c310bce0718c56c0866befccd90ec`: current `CURRENT_STATE.md`, current `REPOSITORY_IMPORT_RI3.md`, and historical/superseded `REPOSITORY_IMPORT_RI2.md`.

The intended Windows host ran the accepted qualification successfully with Docker Desktop server `29.7.2`, PostgreSQL `18`, loopback port `55432`, and persistent state root:

`C:\Users\floyd\AppData\Local\KnowledgeCore\ri4-host-qualification-01`

The generated evidence reported:

```text
status: success
postgres_restart_verified: true
application_reconstruction_verified: true
exact_replay_verified: true
current_historical_retrieval_verified: true
artifact_integrity_verified: true
provenance_verified: true
backup_restore_performed: false
```

The same text generation `da8ab02c-8819-43d0-9d39-e3098398c8e1` remained current across restart/recovery/replay. The bounded RI-4 scope is accepted complete; machine-reboot persistence, backup/restore, and production deployment remain unqualified.

## SR-1 — deterministic section retrieval design — complete

SR-1 is recorded in:

`docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`

It defines the contract for deriving smaller lexical retrieval units from exact immutable textual `ResourceVersion` artifacts while preserving the entire whole document as canonical evidence.

Accepted SR-1 design decisions include:

- deterministic Python, not a model, performs segmentation;
- strict UTF-8 `text/markdown` and `text/plain` remain the bounded supported media;
- exact source bytes are partitioned in source order with no overlap or gaps, and the segment ranges must reconstruct the exact parent bytes/digest;
- Markdown V1 structure uses deterministic ATX-heading recognition plus fenced-code awareness; headings inside fences do not become structure;
- preamble, direct heading blocks, root documents, and deterministic large-block continuations are the retrieval-unit shapes;
- large-block continuation uses fixed byte thresholds and line/blank-line boundaries, with fenced code indivisible; an unbreakable oversized fenced region fails the candidate generation closed;
- every segment retains exact parent `resource_version_ref`, ordinal, byte range, line range, heading path, exact source-slice SHA-256, lifecycle provenance, and a deterministic profile-bound segment key;
- headings, filenames, paths, dates, and prose never infer lifecycle or authority;
- parent document lifecycle remains explicit governed input;
- an optional exact Markdown `kc:retrieval-lifecycle` directive may only preserve or reduce lifecycle currentness within a heading subtree; it can never promote a section above its document/ancestor lifecycle;
- authority rank and approved repository/source metadata remain inherited from the parent in V1; there is no segment-scope authority override;
- PostgreSQL lexical search remains the baseline, using weighted exact local segment text plus source-derived heading context;
- derived segment rows are rebuildable projection state and do not become canonical Resources/ResourceVersions or copied canonical documents;
- the accepted `DerivedKind.TEXT` generation fence remains the serving publication boundary, including the transition from legacy RF-2 whole-document retrieval;
- parent `resource_version_serving_eligible()` remains mandatory before a derived segment hit is emitted;
- no partial/failed segment generation may replace the prior current text generation;
- no model, tokenizer, embedding service, or vector database is required for canonical storage, segmentation, lifecycle provenance, or baseline retrieval.

SR-1 defines falsifiable `SR2-G1` through `SR2-G22`, covering canonical immutability, exact byte reconstruction, Markdown/fence semantics, large-block continuation, stable segment identity, provenance, lifecycle inheritance/directives, generation isolation, RF-2 cutover safety, deterministic ranking, serving fences, service-only behavior, no model dependency, profile rebuilds, and one tiny explicitly pinned real-document pilot after the synthetic gates pass.

## Current limitations / unclaimed capability

Knowledge Core still does not claim:

- implemented section/segment retrieval; SR-1 is a design only;
- section-segmentation migrations/tables/runtime or a current segment generation;
- machine reboot persistence or Docker Desktop restart across a host reboot;
- backup/restore or disaster recovery;
- production credentials, TLS, firewalling, service supervision, startup policy, or filesystem ACL qualification;
- broad/production corpus import or automatic discovery/classification/document-key assignment;
- SHA-256-format Git repository support;
- PDF/DOCX/HTML extraction/OCR, embeddings/vector search, semantic reranking, or RAG/context assembly;
- cross-version semantic section identity or automatic lifecycle inference;
- Authority integration or autonomous execution.

## Durable restart point

Before any separately authorized SR-2 implementation, read:

1. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
2. `docs/architecture/knowledge-core/CURRENT_STATE.md`
3. `docs/architecture/knowledge-core/SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md` for the original SR-1 scope and preserved boundaries
4. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`
5. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`
6. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
7. `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md`
8. `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md`
9. `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md`
10. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
11. `components/knowledge-core/README.md`

Verify branch/HEAD before writing.

## Next separately authorized phase — SR-2

SR-2 may be started only with separate authorization.

If authorized, implement only the smallest derived segment storage/index, deterministic segmenter, generation-builder/retrieval/API changes, and controlled tests required to satisfy `SR2-G1` through `SR2-G22` in `SECTION_RETRIEVAL_SR1.md`.

Synthetic gates must precede the tiny real-document pilot. The real pilot must use an explicit bounded manifest pinned to exact Git objects and the same deterministic machinery; do not manually split source documents or broaden the corpus.

SR-2 must preserve the exact whole `ResourceVersion` as canonical evidence and must prove the RF-2 whole-document generation continues serving until a complete segment generation is safely published.

Do not add embeddings, RAG, broad corpus import, model-required segmentation/retrieval, Authority, execution, or unrelated production/deployment work.

## Stop boundary

**SR-1 is complete as design only. Stop here. Do not begin SR-2 implementation without separate authorization.**
