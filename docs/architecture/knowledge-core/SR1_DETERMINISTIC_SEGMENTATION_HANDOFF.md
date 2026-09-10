# Knowledge Core SR-1 Handoff — Deterministic Document Segmentation and Retrieval Contract

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Starting checkpoint:** `31ae88e8df65776e7932a432a1a38df3fb2c3af3`  
**Prior phase:** RI-4 accepted complete  
**Selected next phase:** **SR-1 — deterministic document segmentation and retrieval contract**  
**Phase type:** **design only**  

## Why SR-1 is next

Persistence/recovery is no longer the immediate blocker. RI-3 and RI-4 proved that accepted Knowledge Core import, generation, artifact, retrieval, and provenance state survives application reconstruction and PostgreSQL restart on CI and the intended Windows host.

The next functional limitation is retrieval granularity. RF-2 indexes and retrieves exact whole `ResourceVersion` documents. The first curated real-corpus pilot showed that whole-document lifecycle treatment is too coarse when one document contains a mixture of current and historical/stale material.

Do **not** solve this by manually splitting documents. The intended system is deterministic machinery that preserves the exact canonical document and derives smaller retrieval units automatically.

## Core decision

The canonical path does **not** require an AI model.

Target architecture:

```text
exact Git document
        ↓
RI-2 exact source verification/import
        ↓
immutable whole ResourceVersion + exact artifact
        ↓
deterministic Python document parser/segmenter
        ↓
derived section/segment records with exact parent provenance
        ↓
PostgreSQL lexical index
        ↓
deterministic ranked retrieval
```

The original whole document remains canonical evidence. Derived retrieval units are rebuildable/disposable indexing state. If segmentation logic changes later, derived units may be regenerated from the immutable source without changing what the source document said.

A model may be considered later for optional semantic assistance such as uncertain classification, query expansion, reranking, or answer synthesis. It must **not** be required to preserve canonical document identity, source bytes, provenance, deterministic segmentation, or baseline lexical retrieval.

## SR-1 design objective

Define a falsifiable contract for how deterministic Python converts an exact immutable textual `ResourceVersion` into smaller safe retrieval units and how retrieval returns those units while preserving exact provenance back to the whole source document.

The design order is:

1. define retrieval behavior and result semantics;
2. define deterministic segmentation rules that satisfy that retrieval contract;
3. define the derived persistence/index representation required to implement those rules;
4. define failure/rebuild/versioning behavior;
5. define SR-2 implementation acceptance gates.

SR-1 must stop before implementing Python, migrations, schema changes, or retrieval code.

## Questions SR-1 must answer

At minimum, the design must resolve:

- What is the retrievable unit: Markdown heading section, subsection, preamble, or another deterministic structure?
- How are `#`, `##`, `###`, etc. represented, and how much parent heading context accompanies a child result?
- How are introductory text, code blocks, tables, lists, fenced blocks, and unusually large sections handled?
- What exact source coordinates are preserved: heading path, byte/character offsets, line ranges, source digest, parent `ResourceVersion`, and/or deterministic segment digest?
- How are segment identities handled when text changes, headings are renamed, sections move, or identical text appears in multiple places?
- Which properties are inherited from the parent document and which, if any, may be explicit at segment scope?
- How is current vs superseded/historical information represented safely when a single canonical document contains mixed-status material?
- What happens when deterministic rules cannot classify or safely segment content?
- How does deletion/restriction serving eligibility on the parent `ResourceVersion` fence all derived segments?
- How does generation publication prevent partially rebuilt segment indexes from serving?
- How are derived segments invalidated/rebuilt when a new parser/segmentation profile is introduced?
- How are search ranking and deterministic tie-breaking extended from RF-2 whole-document search to segment search?
- What does the API return so a client can recover the exact parent document and source location?
- How does the system avoid treating headings, filenames, paths, or generated metadata as unsupported truth?

## Required safety/integrity properties

SR-1 must preserve these accepted invariants unless concrete evidence demonstrates a defect:

- Kernel V1 remains frozen.
- `(source_repository_key, source_document_key) -> Resource` identity remains unchanged.
- Exact source bytes and immutable `ResourceVersion` remain canonical.
- RI-2 exact Git verification, manifest allowlist, omission safety, replay, and publication fencing remain authoritative.
- RF-2 serving-time restriction/deletion fences remain mandatory.
- Derived segmentation/index state must be reproducible from canonical input plus an explicit deterministic segmentation profile/version.
- No parser failure may silently invent, omit, or reclassify canonical source content as truth.
- No partially generated derived index may become the current serving generation.
- Provenance from every retrieval result must resolve to one exact canonical `ResourceVersion` and exact source location.

## Explicit non-goals for SR-1

Do **not** implement or design beyond what is necessary for this contract:

- no manual document splitting or hand-maintained section copies;
- no broad ACL/Vera/RiskCardOCR/research corpus import;
- no PDF/DOCX/HTML/OCR extraction pipeline;
- no embeddings or vector database;
- no RAG/context assembly;
- no model-required storage, segmentation, or retrieval;
- no autonomous classification agent;
- no Authority or autonomous execution;
- no backup/restore, production deployment, TLS, credentials, service supervision, or host-reboot qualification;
- no production code, migrations, or schema changes during SR-1.

## Evidence to review before designing

Read these first:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`
3. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md`
4. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
5. `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md`
6. `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md`
7. `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md`
8. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
9. `components/knowledge-core/README.md`

Then inspect only the existing RF-2/import code and tests needed to ensure the proposed contract fits accepted interfaces and invariants. Do not refactor or implement during SR-1.

## Expected SR-1 deliverable

Create a durable design record, tentatively:

`docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`

It should contain:

- retrieval-unit semantics;
- deterministic Markdown segmentation rules;
- canonical-vs-derived data boundary;
- provenance/identity/location rules;
- lifecycle/authority inheritance or segment-scope policy;
- parser-profile/generation/rebuild semantics;
- PostgreSQL derived-storage/index design at the contract level;
- API/result contract;
- explicit failure behavior;
- a small synthetic fixture plan plus a tiny real-document pilot plan;
- falsifiable SR-2 implementation acceptance gates;
- explicit deferred work.

Update `CURRENT_STATE.md` and `RETRIEVAL_FOUNDATION_HANDOFF.md` only after the SR-1 design is complete and reviewed. Stop before SR-2 implementation.

## Suggested first real pilot shape

Use only a tiny bounded set of existing Knowledge Core Markdown documents chosen to exercise:

- clean current-only structure;
- clean historical/superseded structure;
- mixed-status information in one document;
- nested headings;
- code blocks/tables/lists;
- a large section that stresses segmentation policy.

The pilot must be derived automatically by the same deterministic rules; no hand-splitting of the source documents.

## New-chat startup prompt

Use this in a fresh chat:

> Continue Knowledge Core work in `floydtrey/autonomous-coding-lab` on branch `architecture/knowledge-core`. Read `docs/architecture/knowledge-core/SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md` first, then verify the branch/HEAD and read every prerequisite it names before proposing changes. RI-4 is accepted complete. Perform only SR-1: design a deterministic document-segmentation and section-retrieval contract. Preserve exact whole ResourceVersions as canonical evidence; derived retrieval units must be created by deterministic Python and remain rebuildable from the canonical source. Do not require a model for canonical storage, segmentation, or baseline retrieval. Do not implement code, migrations, schema changes, embeddings, RAG, broad corpus import, Authority, or execution. Produce the durable SR-1 design and falsifiable SR-2 acceptance gates, update the controlling docs, commit the design-only changes, and stop.

## Stop boundary

**SR-1 is design only. Do not implement the segmenter or change the database/runtime until the SR-1 contract and SR-2 acceptance gates have been reviewed.**
