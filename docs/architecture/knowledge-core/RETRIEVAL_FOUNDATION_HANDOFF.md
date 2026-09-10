# Knowledge Core — Retrieval / Import Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RI-4 is accepted complete. SR-1 deterministic document segmentation and section-retrieval design is complete. SR-2 implementation is not started and requires separate authorization.**

## Accepted checkpoints

- Frozen Kernel V1: `9e904f49480055615bb0cf32360dbdc8400e117c`
- PostgreSQL qualification: `2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`
- RF-2 retrieval: `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`
- First curated real-corpus pilot: `40849bd4de261089a030e09677568c3b4cf1a862` — CI `34373589343`
- RI-1 design: `f7f12c04163ecbe3b6143191008cf393726b8def`
- RI-2 governed importer: `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`
- RI-3 final validated code/config/docs checkpoint: `9a167e67200c6bee2b7f4ed7b1dc91224d553390` — CI `34418080815`
- RI-3 final evidence checkpoint: `3d12f205d15c310bce0718c56c0866befccd90ec`
- RI-4 harness checkpoint: `934850d5830d4a5d89ec32b04630435a027e816f` — CI rehearsal `34418809968`
- RI-4 intended-host evidence: `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md` — success
- SR-1 design: `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — complete, design only

## Accepted foundation

Kernel V1 remains frozen. RF-2 and RI-2 semantics remain accepted.

Stable repository document identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

RI-2 still requires exact manifest-listed SHA-1 Git source objects, explicit lifecycle/authority/classification, manifest chaining, omission safety, exact replay, stale-state rejection, and publication fencing. Repository access remains host-injected and ordinary retrieval clients receive no storage/repository credentials.

RF-2 remains the implemented whole-`ResourceVersion` PostgreSQL lexical baseline with exact parent provenance, deterministic rank, current-generation-only serving, and mandatory serving-time privacy/restriction/deletion fencing.

RI-3 and RI-4 remain the accepted bounded persistence/recovery evidence. RI-4 successfully reproduced PostgreSQL restart, application reconstruction, exact replay, current/historical retrieval separation, artifact integrity, and provenance continuity on the intended Windows host.

## SR-1 completion

The controlling SR-1 design is:

`docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`

SR-1 preserves the exact whole `ResourceVersion` and immutable artifact as canonical evidence and defines smaller retrieval units only as deterministic, disposable derived projection state.

### Core deterministic contract

The initial profile is `kc-section-segmentation-v1` and is identified by a canonical configuration digest. The same exact parent `ResourceVersion` plus the same profile must reproduce the same ordered segment boundaries, coordinates, source-slice digests, lifecycle projection, heading paths, and deterministic segment keys.

For strict UTF-8 Markdown, the V1 parser recognizes only bounded ATX headings outside fenced code. It partitions exact source bytes into preamble/direct-heading blocks and deterministic continuations. Plain text uses a root block plus the same deterministic continuation rules. Source ranges are exact, ordered, non-overlapping, and gap-free; concatenating them must reconstruct the exact canonical artifact.

Large blocks use fixed byte thresholds and deterministic blank-line/line-boundary splitting. Fenced code is indivisible. If an oversized fenced region cannot be partitioned legally, the candidate generation fails closed instead of silently splitting, omitting content, or invoking a model fallback.

### Lifecycle/currentness contract

Document lifecycle remains explicit governed input from the accepted import/retrieval source. Heading text, filenames, paths, dates, lexical scores, and recency never create lifecycle or authority.

Markdown may contain an exact reserved `kc:retrieval-lifecycle` directive immediately after a heading. It may only preserve or reduce currentness (`current < unknown < superseded`) for that heading subtree. It can never promote a segment above its parent document or ancestor section lifecycle. Malformed/misplaced reserved directives and promotion attempts fail segmentation.

Unlabeled sections inherit parent lifecycle. Therefore mixed-status intent that is not explicit is **not guessed**. A governed source can add exact section directives in a new canonical version, or the parent can be classified conservatively through the existing import process. No model is required.

Authority rank and approved repository/source annotations remain inherited from the parent in V1; SR-1 defines no segment-scope authority override.

### Derived identity/provenance

Every segment must retain:

- exact parent `resource_version_ref`;
- deterministic source ordinal and structural kind;
- exact byte and line range;
- exact source-slice SHA-256;
- derived heading path;
- parent and effective lifecycle plus lifecycle-origin coordinates;
- inherited retrieval/source metadata;
- deterministic segment key bound to parent version, profile, coordinates, ordinal, and source-slice digest;
- serving generation/profile identity.

A segment key is a derived locator only. It is not a cross-version semantic section identity and never replaces canonical parent provenance.

### Baseline retrieval

PostgreSQL remains the baseline lexical engine. Segment search uses exact local segment text plus source-derived heading-path context in a deterministic weighted `tsvector`. It does not require copied canonical segment bodies in PostgreSQL.

Ranking extends RF-2 deterministically: lexical score, effective lifecycle, inherited authority, parent canonical revision, parent exact version ref, segment ordinal, and final segment-key tie-break.

Multiple hits from one parent are allowed. Grouping/diversification/RAG context assembly are deferred.

Before any segment hit is emitted, the application must recheck serving eligibility of the exact parent `ResourceVersion`. Response limiting remains after that check.

### Generation/cutover safety

Segment retrieval remains under the accepted `DerivedKind.TEXT` one-current-generation fence. `generation_source` continues to identify exact parent versions; segment rows form derived child lineage.

A candidate segment generation cannot settle current until every supported selected parent verifies, decodes, segments, satisfies exact-coverage invariants, and indexes completely. Failure leaves the previous current text generation serving.

The first SR-2 cutover must specifically prove that accepted RF-2 whole-document retrieval remains usable until a complete segment generation is published, that a failed candidate causes no serving gap, and that old whole-document rows and new segment rows are never mixed in one result set.

## Falsifiable SR-2 boundary

`SECTION_RETRIEVAL_SR1.md` defines `SR2-G1` through `SR2-G22`. The gates cover:

- no canonical mutation;
- byte-for-byte partition/reconstruction;
- ATX/fence/preamble semantics;
- deterministic large-block splitting and oversized-fence failure;
- stable segment identities and edit/rename/duplicate behavior;
- exact parent/source provenance;
- inherited metadata and no authority escalation;
- explicit lifecycle directives without heuristic lifecycle inference or promotion;
- mixed current/historical retrieval;
- one-current-generation isolation and RF-2 no-gap cutover;
- deterministic repeated ranking;
- parent serving fences over stale segment rows;
- bounded service-only API behavior and hidden storage internals;
- no language-model/tokenizer/embedding/vector dependency;
- profile-change rebuild behavior;
- one tiny exact-Git-object real-document pilot only after synthetic gates pass.

SR-2 may implement only what those gates require and only after separate authorization.

## Critical boundary

Knowledge Core still does not claim:

- implemented section/segment retrieval;
- section schema/migration/runtime/index generation;
- automatic lifecycle/currentness inference;
- broad or production corpus import;
- automatic discovery/classification/document-key assignment;
- SHA-256-format Git repositories;
- PDF/DOCX/HTML/image/OCR extraction;
- embeddings/vector retrieval, semantic reranking, or RAG/context assembly;
- machine-reboot persistence, Docker Desktop host-reboot recovery, backup/restore, or production deployment/security qualification;
- Authority or autonomous execution.

SR-1 authorizes none of those capabilities.

## Startup instructions for a separately authorized SR-2 continuation

1. Work from `architecture/knowledge-core` and verify branch/HEAD before writing.
2. Read `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` first.
3. Read current controlling state and the accepted RF-2/RI-2 generation/import interfaces before implementation.
4. Preserve exact whole `ResourceVersion`/artifact evidence and existing repository document identity.
5. Implement only the minimum required for `SR2-G1` through `SR2-G22`.
6. Run synthetic gates before the tiny real-document pilot.
7. Do not manually split source documents or broaden the approved corpus.
8. Stop after SR-2 gates/evidence if SR-2 is separately authorized; do not continue into embeddings, RAG, Authority, or execution.

## Stop boundary

**SR-1 is complete as a design and falsifiable acceptance contract. Stop here. Do not begin SR-2 implementation without separate authorization.**
