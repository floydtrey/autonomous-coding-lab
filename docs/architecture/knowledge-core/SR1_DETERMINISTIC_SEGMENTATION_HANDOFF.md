# Knowledge Core SR-1 Handoff — Historical Planning Context

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Original starting checkpoint:** `31ae88e8df65776e7932a432a1a38df3fb2c3af3`  
**Original purpose:** hand off RI-4-complete state into SR-1 deterministic document-segmentation design  
**Current status:** **historical planning handoff; superseded for active SR-1 semantics by audit-amended `SECTION_RETRIEVAL_SR1.md` and `KC-D025`**

## Mandatory supersession notice — 2026-09-10

This file records why SR-1 was started and its original scope. It is **not** the active lifecycle/parser/rebuild contract.

A later bounded audit corrected several assumptions developed during SR-1. Any continuation must read, in order:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`;
2. `docs/architecture/knowledge-core/DECISIONS.md`, especially `KC-D025`;
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`;
4. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`.

If text in this historical planning handoff conflicts with those documents, the later audit-amended contract controls.

In particular, do **not** infer from the original phrase “reproducible from canonical input plus a segmentation profile” that lifecycle/source-ranking projection is determined by canonical bytes alone. The corrected separation is:

```text
structural segmentation
    = exact ResourceVersion + structural segmentation profile

complete retrieval/lifecycle projection
    = structural segments
    + exact governed observation/classification snapshot
    + retrieval-projection profile
```

The corrected contract also establishes that:

- section declarations are preserved as source evidence;
- effective lifecycle is the most restrictive of document + applicable ancestor + own declarations;
- a less-restrictive declaration cannot promote effective state but does not fail merely because inherited state is more restrictive;
- ordinary prose/inline-code/quoted/fenced mentions of `kc:retrieval-lifecycle` are content;
- only standalone control-looking comments enter malformed/misplaced/duplicate control validation;
- an oversized indivisible ordinary UTF-8 line fails like an oversized indivisible fence, and a fitting final suffix is emitted whole;
- A → B → A reuses the original A `ResourceVersion` and structural segment identities under the same structural profile;
- privacy restriction/erasure and derivative reconciliation are distinct from repository historical supersession.

The pre-audit SR-2 candidate `2c48a0e73c560fad62028776f375c94162e138be` is not an accepted implementation checkpoint.

## Why SR-1 followed RI-4

RI-3 and RI-4 proved that accepted Knowledge Core import, generation, artifact, retrieval, and provenance state survives application reconstruction and PostgreSQL restart in the bounded qualified environments.

The next functional limitation was retrieval granularity. RF-2 retrieves whole exact `ResourceVersion` documents. Real-document work showed that whole-document lifecycle treatment is too coarse when one canonical document contains both current and historical material.

The intended solution remains deterministic derived segmentation—not manual source splitting and not model-required canonical processing.

## Original core direction preserved

The architecture still follows:

```text
exact governed Git source
        ↓
RI-2 exact source verification/import
        ↓
immutable whole ResourceVersion + exact artifact
        ↓
deterministic structural parser/segmenter
        ↓
governed lifecycle/source projection
        ↓
derived section/segment records with exact provenance
        ↓
PostgreSQL lexical index
        ↓
deterministic ranked retrieval
```

The whole document remains canonical evidence. Derived retrieval units are rebuildable/disposable indexing state. A model may later assist optional semantic retrieval/reranking/synthesis, but it must not be required for canonical source identity, structural segmentation, governed lifecycle provenance, or baseline lexical retrieval.

## SR-1 scope that remains valid

SR-1 had to define:

- retrievable structural units and heading context;
- preamble, ATX headings, fenced code, lists/tables, plain text, and large-block behavior;
- exact byte/line/source-digest provenance;
- deterministic structural segment identity;
- parent versus section lifecycle semantics;
- generation publication/rebuild behavior;
- PostgreSQL derived representation and deterministic ranking;
- API result provenance;
- serving-time parent restriction/deletion fences;
- controlled synthetic fixtures followed by a tiny exact real-document pilot;
- falsifiable SR-2 gates.

Those subjects are now governed by the amended `SECTION_RETRIEVAL_SR1.md` rather than this planning document.

## Preserved safety/integrity properties

- Kernel V1 remains frozen.
- `(source_repository_key, source_document_key) -> Resource` identity remains unchanged.
- Exact source bytes and immutable `ResourceVersion` remain canonical evidence.
- RI-2 exact Git verification, allowlists, omission safety, replay, and publication fencing remain authoritative.
- RF-2 serving-time privacy/restriction/deletion eligibility remains mandatory.
- Structural segment provenance resolves to one exact canonical `ResourceVersion` and exact source location.
- Complete retrieval-generation provenance also resolves to the exact governed observation/classification snapshot used for lifecycle/source projection.
- No partial derived generation may become current.
- No parser/projection failure authorizes model or heuristic fallback.

## Explicit non-goals preserved

SR-1/SR-2 still exclude:

- manual document splitting;
- broad ACL/Vera/RiskCardOCR/research corpus import;
- PDF/DOCX/HTML/OCR extraction;
- embeddings/vector search;
- RAG/context assembly;
- model-required storage/segmentation/lifecycle retrieval;
- autonomous classification;
- Authority or autonomous execution;
- unrelated production/deployment expansion.

## Historical startup prompt — do not use unchanged

The original startup prompt for designing SR-1 is obsolete because SR-1 is already complete and audit-amended. Do not start a new chat from the old prompt or treat this file as authority for G11/G12.

Use `CURRENT_STATE.md` and the amended SR-1 contract instead.

## Current stop boundary

**This file is historical planning context. It must not be used to restart the pre-audit lifecycle/parser rules. No runtime/test/migration fix is authorized by this documentation clarification itself.**