# Knowledge Core

Knowledge Core is the bounded canonical/retrieval service under `components/knowledge-core`.

## Current status

**Branch:** `architecture/knowledge-core`  
**State:** **SR-2 Slices 1–6 accepted; Slice 7 G1–G21 audit complete; closure qualification pending**

Accepted foundation remains Kernel V1 + PostgreSQL qualification + RF-2 lexical retrieval + governed RI-2 import + RI-3/RI-4 persistence/recovery qualification.

Accepted SR-2 Slice 6 runtime checkpoint:

`1534dba10757612485821bf566c6fdccffde06c2`

Accepted Slice 6 qualification:

- GitHub Actions `34452778382`
- **71** fast tests passed, with 1 guarded exact-corpus skip
- **29** PostgreSQL tests passed, with 2 guarded exact-corpus skips
- RI-4 restart/replay rehearsal passed

The G1–G21 Slice 7 coverage audit has been completed. The current conclusion is that the remaining work is principally cross-boundary qualification closure rather than a broad SR-2 redesign. The Slice 7 closure package has been designed but is **not yet accepted or CI-qualified**, and G22 remains intentionally unexecuted.

No user-PC execution is required yet. The required acceptance order is:

```text
G1–G21 green in CI
    -> separate G22 tiny pinned real-document pilot
    -> G1–G22 green
    -> intended-host SR-2 restart/recovery qualification on the user's PC
```

The controlling section-retrieval design is the audit-amended:

`docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`

with architecture decision KC-D025 in:

`docs/architecture/knowledge-core/DECISIONS.md`

The first file to read before doing any new work is:

`docs/architecture/knowledge-core/CURRENT_STATE.md`

For the current pause/resume boundary, then read:

`docs/architecture/knowledge-core/SR2_SLICE7_PAUSE_HANDOFF.md`

## Abandoned SR-2 prototype

Commit `2c48a0e73c560fad62028776f375c94162e138be` is **ABANDONED — DO NOT USE FOR IMPLEMENTATION, TEST DESIGN, MIGRATION DESIGN, OR DECISION-MAKING**.

That prototype was built against section-retrieval rules that were later corrected. Its SR-2 runtime code, tests, migration, importer adapter, and pilot manifest are intentionally absent from the active tree. Git history is the archive; do not restore or copy those files unless explicitly investigating the rejected prototype.

Any older wording that says to repair, align, or continue `2c48a0e...` is obsolete execution guidance. The active SR-2 implementation was rebuilt from the amended contract.

## Mandatory restart order

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/SR2_SLICE7_PAUSE_HANDOFF.md`
3. `docs/architecture/knowledge-core/DECISIONS.md` — especially KC-D025
4. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
5. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
6. accepted generation / RF-2 / RI-2 / deletion / SR-2 Slice 1–6 implementation and tests needed by the bounded task

Obsolete handoff files are deliberately not retained in the active tree. Accepted RF/RI qualification documents remain only for still-active foundation behavior and concrete qualification evidence; they do not override the restart order above.

Unreferenced Git blob objects created while drafting future Slice 7 work are not accepted branch state and must not be used as restart evidence.

## Accepted identity/retrieval foundation

Stable governed repository identity remains:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Exact `ResourceVersion` identity is content-addressed within one logical Resource. Re-observing prior bytes reuses the existing exact version; A → B → A therefore returns to A's original exact `ResourceVersion` while the later observation/receipt/generation records the new governed event.

RF-2 remains the accepted whole-document PostgreSQL lexical baseline with explicit lifecycle/authority metadata, deterministic ranking, one-current-generation publication, exact parent provenance, and mandatory serving-time restriction/deletion fences.

## SR-2 architecture boundary

The essential split is:

```text
exact ResourceVersion bytes + structural profile
    -> deterministic structural segments

structural segments + exact governed observation/classification snapshot
+ retrieval-projection profile
    -> lifecycle/search projection
```

Declared section lifecycle stays source-derived. Effective lifecycle is the most restrictive of the governed document lifecycle, applicable ancestor declarations, and the section's own declaration.

No model, tokenizer, embedding service, vector service, or semantic inference decides segmentation or lifecycle in this phase.

## Slice 7 resume boundary

Resume from the completed G1–G21 audit rather than repeating it from scratch. The next bounded work is to publish and qualify the missing closure evidence, including the active coverage matrix and mechanical pytest/CI exclusion of a dedicated `sr2_real_pilot` marker.

G22 must not execute as part of the G1–G21 closure run. Only an independently green G1–G21 checkpoint may authorize the separate tiny pinned real-document pilot.

If qualification exposes a straightforward implementation or test defect, repair only that defect. If it exposes a genuine architecture ambiguity, return to the decision process instead of silently broadening the design.

## Development

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
alembic upgrade head
```

Set `KNOWLEDGE_CORE_DATABASE_URL` before PostgreSQL migrations.

## Out of scope

Do not expand SR-2 into embeddings/vector retrieval, RAG/context assembly, model-based lifecycle inference, broad corpus import, automatic discovery/classification, PDF/DOCX/HTML/OCR extraction, Authority, autonomous execution, or unrelated deployment/security work.
