# Knowledge Core

This component contains the frozen Knowledge Core Kernel plus accepted PostgreSQL lexical retrieval, governed repository import, bounded persistence/recovery qualification, and the completed SR-1 deterministic section-retrieval design.

## Current state

**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**RF-2 lexical retrieval:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**RI-2 governed repository import:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**RI-3 application-process persistence:** accepted  
**RI-4 intended-host persistence/recovery:** accepted  
**SR-1 section-retrieval design:** `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — complete, design only  
**Status:** **Exact whole ResourceVersions remain canonical. SR-1 defines deterministic derived section retrieval and SR2-G1 through SR2-G22, but no section segmenter, migration, schema, or segment index has been implemented. No broad or production corpus is imported.**

Controlling state is `docs/architecture/knowledge-core/CURRENT_STATE.md`. The SR-1 contract is `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`. RI-4 intended-host evidence is `docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md`.

## Accepted foundation

Kernel V1 remains frozen. RF-2 provides PostgreSQL whole-`ResourceVersion` lexical retrieval with explicit lifecycle/authority metadata, deterministic ranking, current-generation-only serving, exact provenance, and serving-time restriction/deletion fences.

RI-2 provides stable governed repository document identity:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Manifest V2 is an explicit fail-closed allowlist. The host-configured Git reader accepts only exact listed regular blobs and is qualified for SHA-1 Git repositories. RI-2 covers exact replay, edits, renames, explicit retirements, stale source/state rejection, publication fencing, and exact provenance.

RI-3 proved persistence across application-process reconstruction with the same PostgreSQL database and persistent artifact directory. RI-4 extended that bounded evidence through PostgreSQL restart on CI and the intended Windows host while retaining the persistent Docker volume/artifact directory, current/historical retrieval behavior, exact replay, artifact integrity, and provenance continuity.

## SR-1 deterministic section-retrieval design

SR-1 changes no runtime code. Its core boundary is:

```text
exact immutable ResourceVersion artifact
        ↓
deterministic Python segmentation profile
        ↓
rebuildable exact source-aligned segment rows
        ↓
PostgreSQL lexical projection
        ↓
deterministic section retrieval with exact parent provenance
```

The whole `ResourceVersion`/artifact remains canonical evidence. Derived segments are disposable/rebuildable and must reproduce from the exact parent plus an explicit deterministic profile.

The V1 design uses strict UTF-8 text, deterministic ATX-heading/fenced-code Markdown scanning, root/plain-text handling, exact source byte/line ranges, exact source-slice SHA-256 digests, deterministic large-block continuation, and deterministic segment keys. Exact ranges must cover the parent without gaps/overlap and reconstruct its original bytes.

Document lifecycle remains explicit governed input. Headings, paths, filenames, dates, recency, and lexical score do not infer currentness. An optional exact source-controlled Markdown `kc:retrieval-lifecycle` directive may only preserve or reduce lifecycle within a heading subtree; it cannot promote currentness. Authority/source ranking metadata remains inherited from the parent in V1.

PostgreSQL remains the baseline lexical retrieval engine. No language model, tokenizer, embedding service, vector database, or RAG layer is required for canonical storage, segmentation, lifecycle provenance, or baseline retrieval.

`SECTION_RETRIEVAL_SR1.md` contains the full contract and falsifiable `SR2-G1` through `SR2-G22` implementation gates.

## Current boundary

SR-1 is **design only**. Knowledge Core does not yet claim implemented section retrieval.

The next separately authorized phase is SR-2. If authorized, it may implement only the minimum derived segment table/migration, deterministic segmenter, generation/retrieval/API changes, and synthetic/tiny-real tests required by `SR2-G1` through `SR2-G22`.

The first SR-2 serving transition must preserve the accepted RF-2 whole-document generation until a complete segment generation is published. Failed/partial segment builds must remain non-serving.

Still out of scope:

- broad ACL/Vera/RiskCardOCR/research corpus import;
- automatic discovery/classification/document-key assignment;
- PDF/DOCX/HTML/image/OCR extraction;
- embeddings/vector search, semantic reranking, or RAG/context assembly;
- model-required segmentation/retrieval;
- cross-version semantic section identity;
- Authority or autonomous execution;
- production deployment/security/backup expansion;
- machine-reboot persistence qualification.

## Development

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
alembic upgrade head
```

Set `KNOWLEDGE_CORE_DATABASE_URL` before applying PostgreSQL migrations.

## Next boundary

**Do not begin SR-2 from this README alone.** Read `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` and `CURRENT_STATE.md`, verify branch/HEAD, and proceed only after separate SR-2 authorization. Stop after the accepted SR-2 gates; embeddings, RAG, broad import, Authority, and execution remain separate future work.
