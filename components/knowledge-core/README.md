# Knowledge Core

This component contains the frozen Knowledge Core Kernel plus accepted PostgreSQL lexical retrieval, governed repository import, bounded persistence/recovery qualification, and the audit-amended SR-1 deterministic section-retrieval contract.

## Current state

**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**RF-2 lexical retrieval:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**RI-2 governed repository import:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**RI-3 persistence:** accepted  
**RI-4 intended-host persistence/recovery:** accepted  
**Original SR-1 design commit:** `1d1313844aa4d224bd42c0888970a11e959d9501`  
**Pre-audit SR-2 candidate:** `2c48a0e73c560fad62028776f375c94162e138be` — **not accepted**  
**SR-1 contract:** `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md` — **audit-amended 2026-09-10**  
**Current status:** **SR-2 is paused until the pre-audit implementation is aligned with the amended contract. No broad or production corpus is imported.**

Controlling state is `docs/architecture/knowledge-core/CURRENT_STATE.md`. The architecture decision that records the audit correction is `KC-D025` in `docs/architecture/knowledge-core/DECISIONS.md`.

## Mandatory restart order

Do not start SR-2 from this README alone. Read:

1. `docs/architecture/knowledge-core/CURRENT_STATE.md`
2. `docs/architecture/knowledge-core/DECISIONS.md` — `KC-D025`
3. `docs/architecture/knowledge-core/SECTION_RETRIEVAL_SR1.md`
4. `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
5. RI-1/RI-2 records as needed
6. accepted RF-2/RI-2 implementation interfaces relevant to the bounded change
7. `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`

`SR1_DETERMINISTIC_SEGMENTATION_HANDOFF.md` is historical planning context only. RF-1/RF-2 and RI-3/RI-4 records remain historical qualification evidence and do not override the later SR-1 amendment.

## Accepted foundation

Kernel V1 remains frozen. RF-2 provides whole-`ResourceVersion` PostgreSQL lexical retrieval with explicit lifecycle/authority metadata, deterministic ranking, current-generation-only serving, exact provenance, and mandatory serving-time restriction/deletion fences.

RI-2 provides stable governed repository identity:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Exact `ResourceVersion` identity is content-addressed within that Resource. Previously unseen bytes create a new exact version; re-observing bytes matching a prior version reuses that version. A → B → A therefore reuses A's original `ResourceVersion` while a new source observation/receipt/generation records the later observation.

Manifest V2 remains an explicit fail-closed allowlist. Repository access is host-configured and ordinary clients receive no repository or storage credentials.

## Audit-amended SR-1 section retrieval

### Structural segmentation

Structural segmentation is determined by:

```text
exact immutable ResourceVersion artifact/media
+ structural segmentation profile
```

It determines segment boundaries, ordinals, structural kinds, heading paths, byte/line coordinates, source-slice SHA-256 values, and structural segment keys.

Lifecycle/classification changes alone do not alter those structural identities.

### Governed retrieval projection

Complete lifecycle/source retrieval projection additionally depends on:

```text
exact governed observation/classification snapshot
+ retrieval-projection rules/profile
```

A serving generation must preserve exact governed observation lineage. `ResourceVersion + segmentation profile` alone is not sufficient to reproduce lifecycle, classification, authority, or source-observation metadata.

### Declared and effective lifecycle

Lifecycle restrictiveness is:

```text
current < unknown < superseded
```

A source section declaration is preserved exactly. Effective lifecycle is the most restrictive of the governed document lifecycle, all applicable ancestor declarations, and the section's own declaration.

A child declaring `current` cannot undo an ancestor/document `unknown` or `superseded` state, but the declaration is not rejected merely for being less restrictive. A later parent downgrade therefore reprojects lifecycle without forcing unchanged canonical bytes to fail structural segmentation.

### Lifecycle-control parsing

Valid lifecycle declarations remain exact standalone HTML-comment controls in the required post-heading position.

Ordinary prose, inline code, block quotes/quoted explanations, and fenced code containing `kc:retrieval-lifecycle` are ordinary source content.

A standalone non-fenced control-looking comment beginning with the reserved prefix is treated as attempted control. Malformed, misplaced, or duplicate attempted controls fail lifecycle projection explicitly.

### Large-block edge cases

- fitting final suffix is emitted whole and terminates;
- no split occurs inside a UTF-8 source line or fenced block;
- an indivisible ordinary line or fenced region larger than hard max fails closed.

### Privacy versus historical supersession

Repository supersession/retirement-retain is historical retrieval lifecycle, not privacy deletion.

Privacy `RESTRICT`/`ERASE` fences parent/children immediately. Derivative cleanup is deterministic/idempotent reconciliation and may occur eagerly. If a parent exact version is actually physically purged/erased, no segment derivative may remain. Serving-time parent eligibility stays mandatory defense in depth.

## SR-2 acceptance state

The pre-audit candidate `2c48a0e73c560fad62028776f375c94162e138be` implemented the earlier SR-1 rules and is not accepted under the amendment.

Its first workflow, GitHub Actions `34439043763`, passed migrations and the fast suite, then produced 19 PostgreSQL passes plus one G22 real-pilot query failure. RI-4 rehearsal was skipped after that failure. No fix to that query or to the audited runtime rules has been applied yet.

Before SR-2 can be accepted, implementation must be compared against amended `SR2-G1` through `SR2-G22` in `SECTION_RETRIEVAL_SR1.md` and requalified synthetic-first.

## Current boundary

This documentation amendment changes contract/state only. It does **not** authorize or perform runtime/test/migration/API/pilot-manifest fixes.

Still out of scope:

- broad ACL/Vera/RiskCardOCR/research corpus import;
- automatic discovery/classification/document-key assignment;
- PDF/DOCX/HTML/image/OCR extraction;
- embeddings/vector search, semantic reranking, or RAG/context assembly;
- model-required structural segmentation/lifecycle retrieval;
- cross-version semantic section identity;
- Authority or autonomous execution;
- unrelated production deployment/security/backup expansion;
- machine-reboot persistence qualification.

## Development

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
alembic upgrade head
```

Set `KNOWLEDGE_CORE_DATABASE_URL` before PostgreSQL migrations.

## Next boundary

**When implementation resumes, first align `2c48a0e...` to the audit-amended contract. Do not begin embeddings, RAG, broad import, Authority, execution, or unrelated expansion.**