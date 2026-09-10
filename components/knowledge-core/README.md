# Knowledge Core

Knowledge Core is the bounded canonical/retrieval service under `components/knowledge-core`.

## Current status

**Branch:** `architecture/knowledge-core`  
**State:** **clean SR-2 restart baseline**

Accepted foundation remains Kernel V1 + PostgreSQL qualification + RF-2 lexical retrieval + governed RI-2 import + RI-3/RI-4 persistence/recovery qualification.

The controlling section-retrieval design is the audit-amended:

`docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`

with architecture decision KC-D025 in:

`docs/architecture/knowledge-core/DECISIONS.md`

The first file to read before doing any new work is:

`docs/architecture/knowledge-core/CURRENT_STATE.md`

## Abandoned SR-2 prototype

Commit `2c48a0e73c560fad62028776f375c94162e138be` is **ABANDONED — DO NOT USE FOR IMPLEMENTATION, TEST DESIGN, MIGRATION DESIGN, OR DECISION-MAKING**.

That prototype was built against section-retrieval rules that were later corrected. Its SR-2 runtime code, tests, migration, importer adapter, and pilot manifest are intentionally absent from the active tree. Git history is the archive; do not restore or copy those files unless explicitly investigating the rejected prototype.

Any older wording that says to repair, align, or continue `2c48a0e...` is obsolete execution guidance. Build SR-2 fresh from the amended contract instead.

## Mandatory restart order

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
5. accepted RF-2 / RI-2 implementation and tests needed by the bounded task

Obsolete handoff files are deliberately not retained in the active tree. Accepted RF/RI qualification documents remain only for still-active foundation behavior and concrete qualification evidence; they do not override the restart order above.

## Accepted identity/retrieval foundation

Stable governed repository identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Exact `ResourceVersion` identity is content-addressed within one logical Resource. Re-observing prior bytes reuses the existing exact version; A → B → A therefore returns to A's original exact `ResourceVersion` while the later observation/receipt/generation records the new governed event.

RF-2 remains the accepted whole-document PostgreSQL lexical baseline with explicit lifecycle/authority metadata, deterministic ranking, one-current-generation publication, exact parent provenance, and mandatory serving-time restriction/deletion fences.

## New SR-2 boundary

SR-2 must be implemented fresh from amended SR2-G1 through SR2-G22. The essential split is:

```text
exact ResourceVersion bytes + structural profile
    -> deterministic structural segments

structural segments + exact governed observation/classification snapshot
+ retrieval-projection profile
    -> lifecycle/search projection
```

Declared section lifecycle stays source-derived. Effective lifecycle is the most restrictive of the governed document lifecycle, applicable ancestor declarations, and the section's own declaration.

No model, tokenizer, embedding service, or semantic inference decides segmentation or lifecycle in this phase.

## Development

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
alembic upgrade head
```

Set `KNOWLEDGE_CORE_DATABASE_URL` before PostgreSQL migrations.

## Out of scope

Do not expand SR-2 into embeddings/vector retrieval, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic discovery/classification, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
